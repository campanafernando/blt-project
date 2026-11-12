from celery import shared_task

from . import notifications


@shared_task
def notify_assignment(task_id: int) -> str | None:
    return f"notified:{task_id}" if notifications.assignment_notify_send(task_id=task_id) else None


@shared_task
def send_due_soon_digest() -> int:
    return notifications.due_soon_digest_send()
