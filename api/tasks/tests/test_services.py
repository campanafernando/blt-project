from datetime import timedelta
from unittest import mock

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from tasks import notifications, services
from tasks.models import Task


@pytest.mark.django_db
def test_services_are_keyword_only(user, task):
    with pytest.raises(TypeError):
        services.task_create(user, "Positional")
    with pytest.raises(TypeError):
        services.task_complete(task)
    with pytest.raises(TypeError):
        services.task_delete(task, user)


@pytest.mark.django_db
def test_create_trims_title_and_sets_creator(user):
    task = services.task_create(actor=user, title="  Review PR  ")
    assert task.title == "Review PR"
    assert task.created_by == user
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_create_done_sets_completed_at(user):
    task = services.task_create(actor=user, title="Already done", status=Task.Status.DONE)
    assert task.completed_at is not None


@pytest.mark.django_db
def test_create_rejects_blank_title(user):
    with pytest.raises(ValidationError) as error:
        services.task_create(actor=user, title="   ")
    assert "title" in error.value.message_dict
    assert not Task.objects.exists()


@pytest.mark.django_db
def test_create_rejects_invalid_status(user):
    with pytest.raises(ValidationError) as error:
        services.task_create(actor=user, title="Bad status", status="archived")
    assert "status" in error.value.message_dict


@pytest.mark.django_db
def test_create_rejects_inactive_assignee(user, other_user):
    other_user.is_active = False
    other_user.save()
    with pytest.raises(ValidationError) as error:
        services.task_create(actor=user, title="Inactive", assigned_to=other_user)
    assert "assigned_to" in error.value.message_dict
    assert not Task.objects.exists()


@pytest.mark.django_db
def test_create_with_past_due_date_is_allowed(user):
    past = timezone.localdate() - timedelta(days=3)
    task = services.task_create(actor=user, title="Backdated", due_date=past)
    assert task.is_overdue is True


@pytest.mark.django_db
def test_complete_is_idempotent(user):
    task = services.task_create(actor=user, title="Complete me")
    services.task_complete(task=task)
    first = task.completed_at
    services.task_complete(task=task)
    task.refresh_from_db()
    assert task.completed_at == first
    assert task.status == Task.Status.DONE


@pytest.mark.django_db
def test_reopen_clears_completed_at(user):
    task = services.task_create(actor=user, title="Reopen me", status=Task.Status.DONE)
    services.task_reopen(task=task)
    task.refresh_from_db()
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_reopen_is_idempotent(user, task):
    services.task_reopen(task=task)
    task.refresh_from_db()
    assert task.status == Task.Status.TODO
    assert task.completed_at is None


@pytest.mark.django_db
def test_update_to_done_sets_and_clears_completed_at(user, task):
    services.task_update(task=task, data={"status": Task.Status.DONE})
    assert task.completed_at is not None
    services.task_update(task=task, data={"status": Task.Status.IN_PROGRESS})
    assert task.completed_at is None


@pytest.mark.django_db
def test_update_keeps_completed_at_when_still_done(user, task):
    services.task_update(task=task, data={"status": Task.Status.DONE})
    first = task.completed_at
    services.task_update(task=task, data={"status": Task.Status.DONE, "title": "Renamed"})
    assert task.completed_at == first


@pytest.mark.django_db
def test_update_trims_title_and_rejects_blank(user, task):
    services.task_update(task=task, data={"title": "  Trimmed  "})
    task.refresh_from_db()
    assert task.title == "Trimmed"
    with pytest.raises(ValidationError) as error:
        services.task_update(task=task, data={"title": "  "})
    assert "title" in error.value.message_dict


@pytest.mark.django_db
def test_update_rejects_invalid_status(user, task):
    with pytest.raises(ValidationError) as error:
        services.task_update(task=task, data={"status": "archived"})
    assert "status" in error.value.message_dict


@pytest.mark.django_db
def test_update_rejects_fields_outside_the_whitelist(user, task, other_user):
    with pytest.raises(ValueError, match="created_by"):
        services.task_update(task=task, data={"created_by": other_user})
    task.refresh_from_db()
    assert task.created_by == user


@pytest.mark.django_db
def test_assign_inactive_user_is_rejected(user, other_user, task):
    other_user.is_active = False
    other_user.save()
    with pytest.raises(ValidationError) as error:
        services.task_assign(task=task, user=other_user)
    assert "assigned_to" in error.value.message_dict


@pytest.mark.django_db
def test_assignment_sends_email_after_commit(
    user, other_user, task, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.task_assign(task=task, user=other_user)
    assert len(mail.outbox) == 1
    assert "New task assigned" in mail.outbox[0].subject
    assert mail.outbox[0].to == ["maria@blt.local"]


@pytest.mark.django_db
def test_assignment_notifies_only_once_when_saved_again(
    user, other_user, task, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        services.task_assign(task=task, user=other_user)
    with django_capture_on_commit_callbacks(execute=True):
        services.task_update(task=task, data={"title": "New title"})
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_creator_can_delete(user, task):
    services.task_delete(task=task, actor=user)
    assert not Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
def test_assignee_cannot_delete(user, other_user):
    task = Task.objects.create(title="Not mine", created_by=other_user, assigned_to=user)
    with pytest.raises(PermissionDenied, match="Only the task creator can delete it."):
        services.task_delete(task=task, actor=user)
    assert Task.objects.filter(pk=task.pk).exists()


@pytest.mark.django_db
def test_assignment_notify_send_skips_missing_and_unassigned(task):
    assert notifications.assignment_notify_send(task_id=task.pk) is False
    assert notifications.assignment_notify_send(task_id=0) is False
    assert mail.outbox == []


@pytest.mark.django_db
def test_digest_continues_after_a_failed_send(user, other_user, caplog):
    tomorrow = timezone.localdate() + timedelta(days=1)
    for title in ("First", "Second"):
        Task.objects.create(title=title, due_date=tomorrow, created_by=user, assigned_to=other_user)
    with mock.patch("tasks.notifications.send_mail", side_effect=[OSError("smtp down"), 1]) as send:
        assert notifications.due_soon_digest_send() == 1
    assert send.call_count == 2
    assert all(call.kwargs["fail_silently"] is False for call in send.call_args_list)
    assert "Could not send the due-soon e-mail" in caplog.text
