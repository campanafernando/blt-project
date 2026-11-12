import logging

from django.contrib.auth.models import AbstractBaseUser
from django.core.mail import send_mail
from django.utils import timezone

from .models import Task

logger = logging.getLogger(__name__)


def _recipient(user: AbstractBaseUser) -> str:
    return user.email or f"{user.username}@blt.local"


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
