from datetime import timedelta

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from tasks import services
from tasks.models import Task


@pytest.mark.django_db
def test_create_trims_title_and_sets_creator(user):
    task = services.create_task(actor=user, title="  Revisar PR  ")
    assert task.title == "Revisar PR"
    assert task.created_by == user
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_create_done_sets_completed_at(user):
    task = services.create_task(actor=user, title="Já feita", status=Task.Status.DONE)
    assert task.completed_at is not None


@pytest.mark.django_db
def test_complete_is_idempotent(user):
    task = services.create_task(actor=user, title="Concluir")
    services.complete_task(task)
    first = task.completed_at
    services.complete_task(task)
    task.refresh_from_db()
    assert task.completed_at == first
    assert task.status == Task.Status.DONE


@pytest.mark.django_db
def test_reopen_clears_completed_at(user):
    task = services.create_task(actor=user, title="Reabrir", status=Task.Status.DONE)
    services.reopen_task(task)
    task.refresh_from_db()
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_reopen_is_idempotent(user, task):
    services.reopen_task(task)
    task.refresh_from_db()
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_update_to_done_sets_and_clears_completed_at(user, task):
    services.update_task(task, status=Task.Status.DONE)
    assert task.completed_at is not None
    services.update_task(task, status=Task.Status.IN_PROGRESS)
    assert task.completed_at is None


@pytest.mark.django_db
def test_assign_inactive_user_is_rejected(user, other_user, task):
    other_user.is_active = False
    other_user.save()
    with pytest.raises(ValidationError):
        services.assign_task(task, other_user)


@pytest.mark.django_db
def test_assignment_sends_email_after_commit(
    user, other_user, task, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.assign_task(task, other_user)
    assert len(mail.outbox) == 1
    assert "Nova tarefa atribuída" in mail.outbox[0].subject
    assert mail.outbox[0].to == ["maria@blt.local"]


@pytest.mark.django_db
def test_assignment_notifies_only_once_when_saved_again(
    user, other_user, task, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.assign_task(task, other_user)
    with django_capture_on_commit_callbacks(execute=True):
        services.update_task(task, title="Novo título")
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_create_with_past_due_date_is_allowed(user):
    past = timezone.localdate() - timedelta(days=3)
    task = services.create_task(actor=user, title="Retroativa", due_date=past)
    assert task.is_overdue is True
