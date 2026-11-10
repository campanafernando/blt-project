import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from specs import gitea

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


class Command(BaseCommand):
    help = "Create the demo repository and issues in Gitea (idempotent)."

    def handle(self, *args, **options):
        if not gitea.can_publish():
            raise CommandError("Set GITEA_TOKEN or GITEA_USER/GITEA_PASSWORD before seeding.")

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

        created = 0
        for title, body in ISSUES:
            if title in existing:
                continue
            issue = gitea.create_issue(repo, title, body)
            created += 1
            self.stdout.write(f"created {issue['url']}")

        base = settings.GITEA_URL
        self.stdout.write(
            self.style.SUCCESS(f"Gitea ready at {base}/{repo}/issues — {created} issue(s) created.")
        )
