from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from .filters import TaskFilter
from .models import Task


def _tasks_for(user: AbstractBaseUser) -> QuerySet[Task]:
    """Every task the user may see: created by them or assigned to them."""
    return Task.objects.filter(Q(created_by=user) | Q(assigned_to=user)).select_related(
        "assigned_to", "created_by"
    )


def task_list(*, fetched_by: AbstractBaseUser, filters: Mapping | None = None) -> QuerySet[Task]:
    return TaskFilter(filters or {}, queryset=_tasks_for(fetched_by)).qs


def task_get(*, fetched_by: AbstractBaseUser, task_id: int) -> Task | None:
    return _tasks_for(fetched_by).filter(pk=task_id).first()


def task_summary(*, fetched_by: AbstractBaseUser) -> dict[str, int]:
    queryset = _tasks_for(fetched_by)
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


def assignee_list() -> QuerySet:
    return get_user_model().objects.filter(is_active=True).order_by("username")
