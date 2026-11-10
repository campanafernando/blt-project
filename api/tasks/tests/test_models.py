from datetime import timedelta

import pytest
from django.utils import timezone

from tasks.models import Task


@pytest.mark.django_db
def test_str_returns_title(user):
    task = Task.objects.create(title="Revisar contrato", created_by=user)
    assert str(task) == "Revisar contrato"


@pytest.mark.django_db
def test_overdue_requires_due_date(user):
    task = Task.objects.create(title="Sem prazo", created_by=user)
    assert task.is_overdue is False


@pytest.mark.django_db
def test_past_due_date_is_overdue(user):
    task = Task.objects.create(
        title="Atrasada",
        due_date=timezone.localdate() - timedelta(days=1),
        created_by=user,
    )
    assert task.is_overdue is True


@pytest.mark.django_db
def test_done_task_is_never_overdue(user):
    task = Task.objects.create(
        title="Feita",
        due_date=timezone.localdate() - timedelta(days=10),
        status=Task.Status.DONE,
        created_by=user,
    )
    assert task.is_overdue is False


@pytest.mark.django_db
def test_future_due_date_is_not_overdue(user):
    task = Task.objects.create(
        title="Futura",
        due_date=timezone.localdate() + timedelta(days=1),
        created_by=user,
    )
    assert task.is_overdue is False
