from django.contrib.auth import get_user_model
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination

from . import selectors, services
from .models import Task
from .serializers import (
    TaskInputSerializer,
    TaskSerializer,
    TaskSummarySerializer,
    assignee_field,
)

User = get_user_model()

TASK_FILTER_PARAMETERS = [
    OpenApiParameter(
        "status",
        OpenApiTypes.STR,
        enum=["todo", "in_progress", "done"],
        description="Filter by status.",
    ),
    OpenApiParameter("due_date_after", OpenApiTypes.DATE, description="Due on or after."),
    OpenApiParameter("due_date_before", OpenApiTypes.DATE, description="Due on or before."),
    OpenApiParameter("assigned_to", OpenApiTypes.INT, description="Assignee user id."),
    OpenApiParameter("overdue", OpenApiTypes.BOOL, description="Overdue tasks only."),
    OpenApiParameter("search", OpenApiTypes.STR, description="Title or description."),
    OpenApiParameter("page", OpenApiTypes.INT, description="Page (10 per page)."),
    OpenApiParameter("page_size", OpenApiTypes.INT, description="Up to 100 per page."),
]


def _task_get_or_404(request, task_id: int) -> Task:
    task = selectors.task_get(fetched_by=request.user, task_id=task_id)
    if task is None:
        raise NotFound("Task not found.")
    return task


# One class per URL keeps the public paths, operation ids and schema exactly as published.
# `ref_name` keeps the OpenAPI component names stable now that inputs are nested classes.


class TaskListApi(APIView):
    InputSerializer = TaskInputSerializer

    @extend_schema(
        operation_id="list_tasks",
        parameters=TASK_FILTER_PARAMETERS,
        responses=TaskSerializer(many=True),
        tags=["Tasks"],
    )
    def get(self, request):
        tasks = selectors.task_list(fetched_by=request.user, filters=request.query_params)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(tasks, request, view=self)
        return paginator.get_paginated_response(TaskSerializer(page, many=True).data)

    @extend_schema(
        operation_id="create_task",
        request=InputSerializer,
        responses={201: TaskSerializer},
        tags=["Tasks"],
    )
    def post(self, request):
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = services.task_create(actor=request.user, **serializer.validated_data)
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskSummaryApi(APIView):
    @extend_schema(operation_id="task_summary", responses=TaskSummarySerializer, tags=["Tasks"])
    def get(self, request):
        summary = selectors.task_summary(fetched_by=request.user)
        return Response(TaskSummarySerializer(summary).data)


class TaskDetailApi(APIView):
    class InputSerializer(serializers.Serializer):
        title = serializers.CharField(max_length=200)
        description = serializers.CharField(required=False, allow_blank=True)
        status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
        due_date = serializers.DateField(required=False, allow_null=True)
        assigned_to = assignee_field()

        class Meta:
            ref_name = "TaskUpdate"

    @extend_schema(operation_id="get_task", responses=TaskSerializer, tags=["Tasks"])
    def get(self, request, task_id: int):
        return Response(TaskSerializer(_task_get_or_404(request, task_id)).data)

    @extend_schema(
        operation_id="update_task",
        request=InputSerializer,
        responses=TaskSerializer,
        tags=["Tasks"],
    )
    def patch(self, request, task_id: int):
        task = _task_get_or_404(request, task_id)
        serializer = self.InputSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = services.task_update(task=task, data=serializer.validated_data)
        return Response(TaskSerializer(task).data)

    @extend_schema(operation_id="delete_task", responses={204: None}, tags=["Tasks"])
    def delete(self, request, task_id: int):
        services.task_delete(task=_task_get_or_404(request, task_id), actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCompleteApi(APIView):
    @extend_schema(
        operation_id="complete_task", request=None, responses=TaskSerializer, tags=["Tasks"]
    )
    def post(self, request, task_id: int):
        task = services.task_complete(task=_task_get_or_404(request, task_id))
        return Response(TaskSerializer(task).data)


class TaskReopenApi(APIView):
    @extend_schema(
        operation_id="reopen_task", request=None, responses=TaskSerializer, tags=["Tasks"]
    )
    def post(self, request, task_id: int):
        task = services.task_reopen(task=_task_get_or_404(request, task_id))
        return Response(TaskSerializer(task).data)


class TaskAssignApi(APIView):
    class InputSerializer(serializers.Serializer):
        user = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True))

        class Meta:
            ref_name = "TaskAssign"

    @extend_schema(
        operation_id="assign_task",
        request=InputSerializer,
        responses=TaskSerializer,
        tags=["Tasks"],
    )
    def post(self, request, task_id: int):
        task = _task_get_or_404(request, task_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = services.task_assign(task=task, user=serializer.validated_data["user"])
        return Response(TaskSerializer(task).data)
