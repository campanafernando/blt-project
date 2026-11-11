from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Task(BaseModel):
    class Status(models.TextChoices):
        TODO = "todo", "To do"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO, db_index=True
    )
    due_date = models.DateField(null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="assigned_tasks",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_tasks"
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(fields=("status", "due_date"), name="task_status_due_idx"),
            models.Index(fields=("assigned_to", "status"), name="task_assignee_idx"),
        )
        constraints = (
            models.CheckConstraint(
                condition=(
                    models.Q(status="done", completed_at__isnull=False)
                    | (~models.Q(status="done") & models.Q(completed_at__isnull=True))
                ),
                name="task_completed_at_iff_done",
            ),
        )

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        # Derived on purpose: no nightly job can leave this flag stale.
        if not self.due_date or self.status == self.Status.DONE:
            return False
        return self.due_date < timezone.localdate()
