from django.contrib import admin

from .models import Spec


@admin.register(Spec)
class SpecAdmin(admin.ModelAdmin):
    list_display = ("id", "issue_title", "size", "published", "created_by", "created_at")
    list_filter = ("size", "truncated")
    search_fields = ("issue_title", "summary", "repo")
    readonly_fields = ("body_markdown", "latency_ms", "input_chars", "prompt_version")
