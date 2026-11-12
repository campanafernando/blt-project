import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from specs import gitea
from tasks.seed_data import GITEA_USERS, TASKS

ISSUES = (
    (
        "Add file attachments to tasks",
        "Users need to attach files (PDF, PNG, JPG) to a task and see them in the task detail.\n\n"
        "Context\n"
        "- Files are small (limit 10 MB each, max 5 per task).\n"
        "- Storage should use the existing S3-compatible profile (MinIO locally).\n"
        "- Only the task creator and the assignee may upload or remove attachments.\n\n"
        "Done when\n"
        "- Upload and delete work from the API and the React client.\n"
        "- A task detail lists attachments with name, size and uploaded by.\n"
        "- Removing an attachment deletes the object from storage.\n"
        "- Tests cover permission, size limit and missing file.",
    ),
    (
        "Filter the task list by assignee",
        "The board can filter by status and due date, but not by the person responsible. "
        "Managers need to see one person's workload.\n\n"
        "Context\n"
        "- API already stores assigned_to; add an assignee filter.\n"
        "- Add an 'only mine' shortcut in the UI.\n"
        "- Keep pagination and the existing filters working together.\n\n"
        "Done when\n"
        "- GET /api/v1/tasks/?assigned_to=<id> returns only that user's tasks.\n"
        "- The React filter bar has an assignee select and a 'mine' toggle.\n"
        "- Tests cover combined filters and an unknown user id.",
    ),
    (
        "Weekly digest email for tasks due next week",
        "Send each assignee a single email every Monday with the tasks due in the next "
        "seven days.\n\n"
        "Context\n"
        "- Celery beat already runs a daily digest for tomorrow; this one is weekly.\n"
        "- One email per person, grouped by due date, skipping completed tasks.\n"
        "- Respect the user's timezone (America/Sao_Paulo for now).\n"
        "- Empty digest means no email.\n\n"
        "Done when\n"
        "- The beat schedule has a weekly entry.\n"
        "- The task builds one message per assignee and skips empty ones.\n"
        "- Tests cover grouping, skipping done tasks and an assignee with no tasks.",
    ),
    (
        "Audit log for task changes",
        "We need to know who changed status, assignee or due date on a task, and when.\n\n"
        "Context\n"
        "- Store an immutable row per change with actor, field, old value, new value and "
        "timestamp.\n"
        "- Show the history in the task detail (read-only).\n"
        "- Do not log description or title changes in this iteration.\n\n"
        "Done when\n"
        "- Every status/assignee/due date change creates one audit row.\n"
        "- The API exposes GET /api/v1/tasks/{id}/history/.\n"
        "- Rows cannot be edited or deleted through the API.\n"
        "- Tests cover each tracked field and an untracked one.",
    ),
)


# Left without a task on purpose, so there is a fresh issue to generate a spec from.
# Keep it last: its number then stays stable after a fresh seed.
SPEC_PRACTICE_ISSUE = (
    "Export the task list to CSV",
    "People want to take their tasks into a spreadsheet for the weekly review.\n\n"
    "Context\n"
    "- The board already filters by status, due date, assignee and search.\n"
    "- The export should respect the same filters and only include tasks the user can see.\n"
    "- Columns: title, status, due date, assignee, created by, completed at.\n"
    "- Large lists must not block the request: the file can be prepared in the background.\n\n"
    "Done when\n"
    "- A signed-in user downloads a CSV of the filtered list from the board.\n"
    "- Dates are ISO formatted and text is escaped so spreadsheets do not run formulas.\n"
    "- Tests cover visibility, filters, an empty result and formula-looking titles.",
)


def synced_issues() -> list[tuple[str, str, list[str]]]:
    """One issue per task assigned to a Gitea user, same title and assignee."""
    return [
        (title, f"{description}\n\nTracked in BLT as a task assigned to {assignee}.", [assignee])
        for title, description, _status, _due, _creator, assignee in TASKS
        if assignee in GITEA_USERS
    ]


class Command(BaseCommand):
    help = "Create the project repository, its users and issues in Gitea (idempotent)."

    def handle(self, *args, **options):
        if not gitea.can_publish():
            raise CommandError("No Gitea token and no blt_password secret: run `make env` first.")

        gitea.unblock_account()

        repo = settings.GITEA_REPO
        for attempt in range(30):
            try:
                gitea.ensure_repo(repo)
                break
            except gitea.TrackerUnavailable:
                if attempt == 29:
                    raise
                time.sleep(2)
        existing = {issue["title"] for issue in gitea.list_issues(repo, limit=50, state="all")}

        assignable = []
        for username in GITEA_USERS:
            try:
                gitea.ensure_collaborator(repo, username)
                assignable.append(username)
            except gitea.IssueNotFound:
                self.stdout.write(
                    f"Gitea user '{username}' does not exist: its issues stay unassigned"
                )

        wanted = [(title, body, []) for title, body in ISSUES]
        wanted += [
            (title, body, [name for name in names if name in assignable])
            for title, body, names in synced_issues()
        ]
        wanted.append((*SPEC_PRACTICE_ISSUE, []))

        created = 0
        for title, body, assignees in wanted:
            if title in existing:
                continue
            issue = gitea.create_issue(repo, title, body, assignees=assignees)
            created += 1
            self.stdout.write(f"created {issue['url']}")

        base = settings.GITEA_URL
        self.stdout.write(
            self.style.SUCCESS(f"Gitea ready at {base}/{repo}/issues — {created} issue(s) created.")
        )
