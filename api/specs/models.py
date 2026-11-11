from django.conf import settings
from django.db import models


class Spec(models.Model):
    class Size(models.TextChoices):
        SMALL = "S", "S"
        MEDIUM = "M", "M"
        LARGE = "L", "L"

    issue_url = models.URLField()
    repo = models.CharField(max_length=200)
    issue_number = models.PositiveIntegerField()
    issue_title = models.CharField(max_length=300)
    summary = models.TextField()
    acceptance_criteria = models.JSONField(default=list)
    implementation_steps = models.JSONField(default=list)
    risks = models.JSONField(default=list)
    out_of_scope = models.JSONField(default=list)
    size = models.CharField(max_length=1, choices=Size.choices)
    body_markdown = models.TextField()
    model = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=20)
    latency_ms = models.PositiveIntegerField()
    input_chars = models.PositiveIntegerField()
    truncated = models.BooleanField(default=False)
    published_issue_url = models.URLField(blank=True)
    published_issue_number = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="specs"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = (models.Index(fields=("created_by", "-created_at")),)

    def __str__(self) -> str:
        return f"Spec #{self.pk} · {self.issue_title}"

    @property
    def published(self) -> bool:
        # The URL alone is not enough: publish_spec parks a claim marker in it while publishing.
        return self.published_issue_number is not None
