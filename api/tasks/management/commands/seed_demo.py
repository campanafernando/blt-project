from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Task

User = get_user_model()

DEMO_PASSWORD = "demo12345"

TASKS = (
    (
        "Review the customer contract",
        "Read the amendment and flag risks.",
        "in_progress",
        2,
        "demo",
    ),
    ("Close the monthly report", "Consolidate October numbers.", "todo", 5, "demo"),
    ("Ship the checkout fix", "Hotfix validated in staging.", "done", -1, "demo"),
    ("Plan sprint 24", "Refinement with the team on Thursday.", "todo", 9, "maria"),
    ("Update the API documentation", "Schema and error examples.", "in_progress", -2, "maria"),
    ("Review the authentication PR", "Focus on token expiration.", "todo", 1, "demo"),
    ("Prepare the customer demo", "Ten-minute script.", "todo", 3, "maria"),
    ("Fix the date filter", "Timezone in the due date filter.", "done", -4, "demo"),
    ("Move the email job to Celery", "Remove the manual thread.", "in_progress", 6, "demo"),
    ("Write permission tests", "Cover creator, assignee and stranger.", "todo", None, "maria"),
)


class Command(BaseCommand):
    help = "Create demo users and tasks (idempotent)."

    def handle(self, *args, **options):
        demo, _ = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@blt.local", "first_name": "Demo", "last_name": "User"},
        )
        demo.set_password(DEMO_PASSWORD)
        demo.save()

        maria, _ = User.objects.get_or_create(
            username="maria",
            defaults={"email": "maria@blt.local", "first_name": "Maria", "last_name": "Souza"},
        )
        maria.set_password(DEMO_PASSWORD)
        maria.save()

        users = {"demo": demo, "maria": maria}
        today = timezone.localdate()
        created = 0
        for title, description, status, due_offset, assignee in TASKS:
            due_date = today + timedelta(days=due_offset) if due_offset is not None else None
            _, was_created = Task.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "due_date": due_date,
                    "assigned_to": users[assignee],
                    "created_by": demo,
                    "completed_at": timezone.now() if status == Task.Status.DONE else None,
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed ready: {created} task(s) created. "
                f"Login: demo / {DEMO_PASSWORD} (also maria / {DEMO_PASSWORD})"
            )
        )
