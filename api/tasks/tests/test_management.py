from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from tasks import services
from tasks.models import Task
from tasks.tasks import notify_assignment, send_due_soon_digest


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_demo")
    call_command("seed_demo")
    assert Task.objects.count() == 10
    assert Task.objects.filter(created_by__username="demo").exists()
    assert Task.objects.filter(assigned_to__username="maria").exists()


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
    assert send_due_soon_digest() == services.due_soon_digest_send() == 0
    assert len(mail.outbox) == 1
