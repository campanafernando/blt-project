from django.db.models import Count, Q
from django.utils import timezone

from .models import Task


def tasks_for(user):
    """Every task the user may see: created by them or assigned to them."""
    return Task.objects.filter(Q(created_by=user) | Q(assigned_to=user)).select_related(
        "assigned_to", "created_by"
    )


def get_task(user, task_id: int) -> Task | None:
    return tasks_for(user).filter(pk=task_id).first()


def summary_for(user) -> dict:
    queryset = tasks_for(user)
    counts = {
        row["status"]: row["total"] for row in queryset.values("status").annotate(total=Count("id"))
    }
    overdue = (
        queryset.filter(due_date__lt=timezone.localdate()).exclude(status=Task.Status.DONE).count()
    )
    return {
        "total": sum(counts.values()),
        "todo": counts.get(Task.Status.TODO, 0),
        "in_progress": counts.get(Task.Status.IN_PROGRESS, 0),
        "done": counts.get(Task.Status.DONE, 0),
        "overdue": overdue,
    }
