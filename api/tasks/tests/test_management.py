from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from conftest import TEST_PASSWORD
from tasks import notifications
from tasks.models import Task
from tasks.seed_data import TASKS, USERS
from tasks.tasks import notify_assignment, send_due_soon_digest


@pytest.mark.django_db
def test_seed_is_idempotent(api, settings):
    settings.SEED_PASSWORD = TEST_PASSWORD
    call_command("seed")
    call_command("seed")
    assert Task.objects.count() == len(TASKS)
    assert Task.objects.filter(assigned_to__isnull=True).count() == 1
    for username in USERS:
        login = api.post(
            "/api/v1/auth/token/", {"username": username, "password": TEST_PASSWORD}, format="json"
        )
        assert login.status_code == 200
    assert Task.objects.filter(assigned_to__username="lane", created_by__username="fernando")
    # A teammate sees what is assigned to them and what they created.
    ballast = api.post(
        "/api/v1/auth/token/", {"username": "ballast", "password": TEST_PASSWORD}, format="json"
    ).data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {ballast}")
    titles = {task["title"] for task in api.get("/api/v1/tasks/?page_size=100").data["results"]}
    assert "Design the onboarding checklist" in titles
    assert "Set up the staging database backup" not in titles


@pytest.mark.django_db
def test_digest_sends_one_email_per_due_task(user):
    tomorrow = timezone.localdate() + timedelta(days=1)
    Task.objects.create(title="Due tomorrow", due_date=tomorrow, created_by=user, assigned_to=user)
    Task.objects.create(
        title="Done",
        due_date=tomorrow,
        created_by=user,
        assigned_to=user,
        status=Task.Status.DONE,
        completed_at=timezone.now(),
    )
    Task.objects.create(title="Unassigned", due_date=tomorrow, created_by=user)
    assert send_due_soon_digest() == 1
    assert len(mail.outbox) == 1
    assert "due tomorrow" in mail.outbox[0].subject.lower()


@pytest.mark.django_db
def test_celery_tasks_delegate_to_services(user, other_user):
    task = Task.objects.create(title="Notify", created_by=user, assigned_to=other_user)
    assert notify_assignment(task.pk) == f"notified:{task.pk}"
    assert notify_assignment(0) is None
    assert send_due_soon_digest() == notifications.due_soon_digest_send() == 0
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_seed_refuses_to_run_without_the_password_secret(settings):
    from django.core.management.base import CommandError

    settings.SEED_PASSWORD = ""
    with pytest.raises(CommandError):
        call_command("seed")
