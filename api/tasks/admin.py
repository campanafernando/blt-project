from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "due_date", "assigned_to", "created_by", "is_overdue")
    list_filter = ("status", "due_date")
    search_fields = ("title", "description")
    autocomplete_fields = ("assigned_to", "created_by")
    date_hierarchy = "created_at"
