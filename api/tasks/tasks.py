from celery import shared_task

from . import services


@shared_task
def notify_assignment(task_id: int) -> str | None:
    return f"notified:{task_id}" if services.assignment_notify_send(task_id=task_id) else None


@shared_task
def send_due_soon_digest() -> int:
    return services.due_soon_digest_send()
