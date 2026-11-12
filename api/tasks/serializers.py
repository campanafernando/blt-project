from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Task

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    """Directory entry: no contact or status data for other users."""

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")
        read_only_fields = fields


def assignee_field() -> serializers.PrimaryKeyRelatedField:
    return serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )


class TaskInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    assigned_to = assignee_field()

    class Meta:
        ref_name = "TaskCreate"


class TaskSerializer(serializers.ModelSerializer):
    assigned_to = UserBriefSerializer(read_only=True)
    created_by = UserBriefSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Task
        fields = (
            "id",
            "title",
            "description",
            "status",
            "status_display",
            "due_date",
            "assigned_to",
            "created_by",
            "completed_at",
            "is_overdue",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class TaskSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    todo = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    done = serializers.IntegerField()
    overdue = serializers.IntegerField()
