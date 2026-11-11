import logging
from datetime import date

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)

TASK_UPDATE_FIELDS = ("title", "description", "status", "due_date", "assigned_to")


def _assignee_validate(user: AbstractBaseUser | None) -> None:
    if user is not None and not user.is_active:
        raise ValidationError({"assigned_to": "Inactive users cannot be assigned tasks."})


def _notify(task: Task) -> None:
    if task.assigned_to_id:
        # Only after commit: no e-mail for a task that was rolled back.
        from .tasks import notify_assignment  # tasks.py imports this module at load time

        transaction.on_commit(lambda: notify_assignment.delay(task.pk))


def _recipient(user: AbstractBaseUser) -> str:
    return user.email or f"{user.username}@blt.local"


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


def assignment_notify_send(*, task_id: int) -> bool:
    """E-mail the assignee of a task. Returns False when there is nobody to notify."""
    task = Task.objects.select_related("assigned_to", "created_by").filter(pk=task_id).first()
    if task is None or task.assigned_to is None:
        return False
    send_mail(
        subject=f"New task assigned: {task.title}",
        message=(
            f"{task.created_by.username} assigned '{task.title}' to you."
            f"\nDue date: {task.due_date or 'none'}"
        ),
        from_email=None,
        recipient_list=[_recipient(task.assigned_to)],
        fail_silently=False,
    )
    return True


def due_soon_digest_send() -> int:
    """E-mail the assignees of tasks due tomorrow. One failure does not stop the rest."""
    due = timezone.localdate() + timezone.timedelta(days=1)
    tasks = (
        Task.objects.filter(due_date=due, assigned_to__isnull=False)
        .exclude(status=Task.Status.DONE)
        .select_related("assigned_to")
    )
    sent = 0
    for task in tasks:
        try:
            send_mail(
                subject="Task due tomorrow",
                message=f"'{task.title}' is due on {due}.",
                from_email=None,
                recipient_list=[_recipient(task.assigned_to)],
                fail_silently=False,
            )
        except Exception:
            logger.exception("Could not send the due-soon e-mail for task %s", task.pk)
            continue
        sent += 1
    return sent
