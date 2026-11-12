from datetime import date

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Task
from .tasks import notify_assignment

TASK_UPDATE_FIELDS = ("title", "description", "status", "due_date", "assigned_to")


def _assignee_validate(user: AbstractBaseUser | None) -> None:
    if user is not None and not user.is_active:
        raise ValidationError({"assigned_to": "Inactive users cannot be assigned tasks."})


def _notify(task: Task) -> None:
    if task.assigned_to_id:
        # Only after commit: no e-mail for a task that was rolled back.
        transaction.on_commit(lambda: notify_assignment.delay(task.pk))


def _completed_at_sync(task: Task, *, was_done: bool) -> None:
    """Keep `completed_at` set if and only if the task is done."""
    if task.status != Task.Status.DONE:
        task.completed_at = None
    elif not was_done or task.completed_at is None:
        task.completed_at = timezone.now()


@transaction.atomic
def task_create(
    *,
    actor: AbstractBaseUser,
    title: str,
    description: str = "",
    due_date: date | None = None,
    assigned_to: AbstractBaseUser | None = None,
    status: str = Task.Status.TODO,
) -> Task:
    _assignee_validate(assigned_to)
    task = Task(
        title=title.strip(),
        description=description,
        due_date=due_date,
        assigned_to=assigned_to,
        status=status,
        created_by=actor,
    )
    _completed_at_sync(task, was_done=False)
    task.full_clean()
    task.save()
    _notify(task)
    return task


@transaction.atomic
def task_update(*, task: Task, data: dict) -> Task:
    unknown = set(data) - set(TASK_UPDATE_FIELDS)
    if unknown:
        raise ValueError(f"Fields cannot be updated: {', '.join(sorted(unknown))}")
    if "assigned_to" in data:
        _assignee_validate(data["assigned_to"])

    was_done = task.status == Task.Status.DONE
    for field, value in data.items():
        setattr(task, field, value.strip() if field == "title" else value)
    _completed_at_sync(task, was_done=was_done)
    task.full_clean()
    task.save()
    if "assigned_to" in data:
        _notify(task)
    return task


@transaction.atomic
def task_complete(*, task: Task) -> Task:
    if task.status == Task.Status.DONE:
        return task
    task.status = Task.Status.DONE
    _completed_at_sync(task, was_done=False)
    task.full_clean()
    task.save(update_fields=("status", "completed_at", "updated_at"))
    return task


@transaction.atomic
def task_reopen(*, task: Task) -> Task:
    if task.status != Task.Status.DONE:
        return task
    task.status = Task.Status.TODO
    _completed_at_sync(task, was_done=True)
    task.full_clean()
    task.save(update_fields=("status", "completed_at", "updated_at"))
    return task


@transaction.atomic
def task_assign(*, task: Task, user: AbstractBaseUser) -> Task:
    _assignee_validate(user)
    task.assigned_to = user
    task.full_clean()
    task.save(update_fields=("assigned_to", "updated_at"))
    _notify(task)
    return task


@transaction.atomic
def task_delete(*, task: Task, actor: AbstractBaseUser) -> None:
    if task.created_by_id != actor.id:
        raise PermissionDenied("Only the task creator can delete it.")
    task.delete()
