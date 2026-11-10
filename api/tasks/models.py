from django.conf import settings
from django.db import models
from django.utils import timezone


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "A fazer"
        IN_PROGRESS = "in_progress", "Em andamento"
        DONE = "done", "Concluída"

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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = (
            models.Index(fields=("status", "due_date"), name="task_status_due_idx"),
            models.Index(fields=("assigned_to", "status"), name="task_assignee_idx"),
        )

    def __str__(self) -> str:
        return self.title

    @property
    def is_overdue(self) -> bool:
        # Derived on purpose: no nightly job can leave this flag stale.
        if not self.due_date or self.status == self.Status.DONE:
            return False
        return self.due_date < timezone.localdate()
