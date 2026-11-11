from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from tasks.models import Task
from tasks.seed_data import PASSWORD, TASKS, USERS

User = get_user_model()


class Command(BaseCommand):
    help = "Create the sample users and tasks (idempotent)."

    def handle(self, *args, **options):
        users = {}
        for username, (first_name, last_name) in USERS.items():
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@blt.local",
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )
            user.set_password(PASSWORD)
            user.save()
            users[username] = user

        today = timezone.localdate()
        created = 0
        for title, description, status, due_offset, creator, assignee in TASKS:
            due_date = today + timedelta(days=due_offset) if due_offset is not None else None
            _, was_created = Task.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "status": status,
                    "due_date": due_date,
                    "assigned_to": users[assignee] if assignee else None,
                    "created_by": users[creator],
                    "completed_at": timezone.now() if status == Task.Status.DONE else None,
                },
            )
            created += int(was_created)

        names = ", ".join(USERS)
        self.stdout.write(
            self.style.SUCCESS(f"Seed ready: {created} task(s) created. Users: {names}")
        )
