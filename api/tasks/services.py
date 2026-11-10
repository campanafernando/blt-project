from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Task
from .tasks import notify_assignment


def _validate_assignee(user) -> None:
    if user is not None and not user.is_active:
        raise ValidationError({"assigned_to": "Inactive users cannot be assigned tasks."})


def _notify(task: Task) -> None:
    if task.assigned_to_id:
        # Only after commit: no e-mail for a task that was rolled back.
        transaction.on_commit(lambda: notify_assignment.delay(task.pk))


def create_task(
    *,
    actor,
    title: str,
    description: str = "",
    due_date=None,
    assigned_to=None,
    status: str = Task.Status.TODO,
) -> Task:
    _validate_assignee(assigned_to)
    task = Task.objects.create(
        title=title.strip(),
        description=description,
        due_date=due_date,
        assigned_to=assigned_to,
        status=status,
        created_by=actor,
        completed_at=timezone.now() if status == Task.Status.DONE else None,
    )
    _notify(task)
    return task


def update_task(task: Task, **changes) -> Task:
    if "assigned_to" in changes:
        _validate_assignee(changes["assigned_to"])

    new_status = changes.get("status", task.status)
    if new_status == Task.Status.DONE and task.status != Task.Status.DONE:
        task.completed_at = timezone.now()
    elif new_status != Task.Status.DONE:
        task.completed_at = None

    for field, value in changes.items():
        setattr(task, field, value)
    task.save()
    if "assigned_to" in changes:
        _notify(task)
    return task


def complete_task(task: Task) -> Task:
    if task.status == Task.Status.DONE:
        return task
    task.status = Task.Status.DONE
    task.completed_at = timezone.now()
    task.save(update_fields=("status", "completed_at", "updated_at"))
    return task


def reopen_task(task: Task) -> Task:
    if task.status != Task.Status.DONE:
        return task
    task.status = Task.Status.TODO
    task.completed_at = None
    task.save(update_fields=("status", "completed_at", "updated_at"))
    return task


def assign_task(task: Task, user) -> Task:
    _validate_assignee(user)
    task.assigned_to = user
    task.save(update_fields=("assigned_to", "updated_at"))
    _notify(task)
    return task
