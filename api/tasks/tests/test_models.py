from datetime import UTC, datetime, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from tasks.models import Task

COMPLETED_AT = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


@pytest.mark.django_db
def test_str_returns_title(user):
    task = Task.objects.create(title="Review contract", created_by=user)
    assert str(task) == "Review contract"


@pytest.mark.django_db
def test_overdue_requires_due_date(user):
    task = Task.objects.create(title="No deadline", created_by=user)
    assert task.is_overdue is False


@pytest.mark.django_db
def test_past_due_date_is_overdue(user):
    task = Task.objects.create(
        title="Overdue",
        due_date=timezone.localdate() - timedelta(days=1),
        created_by=user,
    )
    assert task.is_overdue is True


@pytest.mark.django_db
def test_done_task_is_never_overdue(user):
    task = Task.objects.create(
        title="Finished",
        due_date=timezone.localdate() - timedelta(days=10),
        status=Task.Status.DONE,
        completed_at=COMPLETED_AT,
        created_by=user,
    )
    assert task.is_overdue is False


@pytest.mark.django_db
def test_future_due_date_is_not_overdue(user):
    task = Task.objects.create(
        title="Future",
        due_date=timezone.localdate() + timedelta(days=1),
        created_by=user,
    )
    assert task.is_overdue is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("status", "completed_at"),
    [
        (Task.Status.DONE, None),
        (Task.Status.TODO, COMPLETED_AT),
        (Task.Status.IN_PROGRESS, COMPLETED_AT),
    ],
)
def test_database_rejects_completed_at_out_of_sync_with_status(user, status, completed_at):
    with pytest.raises(IntegrityError), transaction.atomic():
        Task.objects.create(
            title="Inconsistent", status=status, completed_at=completed_at, created_by=user
        )


@pytest.mark.django_db
def test_database_accepts_consistent_completed_at(user):
    Task.objects.create(title="Open", created_by=user)
    Task.objects.create(
        title="Closed", status=Task.Status.DONE, completed_at=COMPLETED_AT, created_by=user
    )
    assert Task.objects.count() == 2
