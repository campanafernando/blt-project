from datetime import timedelta

import pytest
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from tasks.models import Task
from tasks.tasks import send_due_soon_digest


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
    Task.objects.create(title="Vence amanhã", due_date=tomorrow, created_by=user, assigned_to=user)
    Task.objects.create(
        title="Concluída",
        due_date=tomorrow,
        created_by=user,
        assigned_to=user,
        status=Task.Status.DONE,
    )
    Task.objects.create(title="Sem responsável", due_date=tomorrow, created_by=user)
    assert send_due_soon_digest() == 1
    assert len(mail.outbox) == 1
    assert "vence amanhã" in mail.outbox[0].subject.lower()
