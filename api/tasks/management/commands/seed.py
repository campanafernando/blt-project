from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Task

User = get_user_model()

USERNAME = "fernando"
PASSWORD = "blt2026"

TASKS = (
    ("Review the customer contract", "Read the amendment and flag risks.", "in_progress", 2),
    ("Close the monthly report", "Consolidate October numbers.", "todo", 5),
    ("Ship the checkout fix", "Hotfix validated in staging.", "done", -1),
    ("Plan sprint 24", "Refinement with the team on Thursday.", "todo", 9),
    ("Update the API documentation", "Schema and error examples.", "in_progress", -2),
    ("Review the authentication PR", "Focus on token expiration.", "todo", 1),
    ("Prepare the customer presentation", "Ten-minute script.", "todo", 3),
    ("Fix the date filter", "Timezone in the due date filter.", "done", -4),
    ("Move the email job to Celery", "Remove the manual thread.", "in_progress", 6),
    ("Write permission tests", "Cover creator, assignee and stranger.", "todo", None),
)


class Command(BaseCommand):
    help = "Create the first user and sample tasks (idempotent)."

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            username=USERNAME,
            defaults={
                "email": "fernando@blt.local",
                "first_name": "Fernando",
                "last_name": "Campana",
            },
        )
        user.set_password(PASSWORD)
        user.save()

        today = timezone.localdate()
        created = 0
        for index, (title, description, status, due_offset) in enumerate(TASKS):
            due_date = today + timedelta(days=due_offset) if due_offset is not None else None
            _, was_created = Task.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "due_date": due_date,
                    # The last task stays unassigned so the board shows both cases.
                    "assigned_to": user if index < len(TASKS) - 1 else None,
                    "created_by": user,
                    "completed_at": timezone.now() if status == Task.Status.DONE else None,
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(f"Seed ready: {created} task(s) created. Login: {USERNAME}")
        )
