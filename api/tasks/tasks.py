from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from .models import Task


@shared_task
def notify_assignment(task_id: int) -> str | None:
    task = Task.objects.select_related("assigned_to", "created_by").filter(pk=task_id).first()
    if task is None or task.assigned_to_id is None:
        return None
    send_mail(
        subject=f"Nova tarefa atribuída: {task.title}",
        message=(
            f"{task.created_by.username} atribuiu a tarefa '{task.title}' a você."
            f"\nVencimento: {task.due_date or 'sem data'}"
        ),
        from_email=None,
        recipient_list=[task.assigned_to.email or f"{task.assigned_to.username}@blt.local"],
        fail_silently=False,
    )
    return f"notified:{task_id}"


@shared_task
def send_due_soon_digest() -> int:
    due = timezone.localdate() + timezone.timedelta(days=1)
    tasks = Task.objects.filter(due_date=due).exclude(status=Task.Status.DONE)
    sent = 0
    for task in tasks.select_related("assigned_to"):
        if task.assigned_to_id is None:
            continue
        send_mail(
            subject="Tarefa vence amanhã",
            message=f"A tarefa '{task.title}' vence em {due}.",
            from_email=None,
            recipient_list=[task.assigned_to.email or f"{task.assigned_to.username}@blt.local"],
            fail_silently=True,
        )
        sent += 1
    return sent
