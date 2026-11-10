from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination

from . import selectors, services
from .filters import TaskFilter
from .serializers import (
    TaskAssignSerializer,
    TaskCreateSerializer,
    TaskSerializer,
    TaskSummarySerializer,
    TaskUpdateSerializer,
)

TASK_FILTER_PARAMETERS = [
    OpenApiParameter(
        "status",
        OpenApiTypes.STR,
        enum=["todo", "in_progress", "done"],
        description="Filtra por status.",
    ),
    OpenApiParameter("due_date_after", OpenApiTypes.DATE, description="Due on or after."),
    OpenApiParameter("due_date_before", OpenApiTypes.DATE, description="Due on or before."),
    OpenApiParameter("assigned_to", OpenApiTypes.INT, description="Assignee user id."),
    OpenApiParameter("overdue", OpenApiTypes.BOOL, description="Somente atrasadas."),
    OpenApiParameter("search", OpenApiTypes.STR, description="Title or description."),
    OpenApiParameter("page", OpenApiTypes.INT, description="Page (10 per page)."),
    OpenApiParameter("page_size", OpenApiTypes.INT, description="Up to 100 per page."),
]


class TaskListApi(APIView):
    @extend_schema(
        operation_id="list_tasks",
        parameters=TASK_FILTER_PARAMETERS,
        responses=TaskSerializer(many=True),
        tags=["Tasks"],
    )
    def get(self, request):
        filtered = TaskFilter(request.query_params, queryset=selectors.tasks_for(request.user))
        paginator = StandardPagination()
        page = paginator.paginate_queryset(filtered.qs, request, view=self)
        return paginator.get_paginated_response(TaskSerializer(page, many=True).data)

    @extend_schema(
        operation_id="create_task",
        request=TaskCreateSerializer,
        responses={201: TaskSerializer},
        tags=["Tasks"],
    )
    def post(self, request):
        serializer = TaskCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskSummaryApi(APIView):
    @extend_schema(operation_id="task_summary", responses=TaskSummarySerializer, tags=["Tasks"])
    def get(self, request):
        return Response(TaskSummarySerializer(selectors.summary_for(request.user)).data)


class TaskDetailApi(APIView):
    def get_task(self, request, task_id: int):
        task = selectors.get_task(request.user, task_id)
        if task is None:
            raise NotFound("Task not found.")
        return task

    @extend_schema(operation_id="get_task", responses=TaskSerializer, tags=["Tasks"])
    def get(self, request, task_id: int):
        return Response(TaskSerializer(self.get_task(request, task_id)).data)

    @extend_schema(
        operation_id="update_task",
        request=TaskUpdateSerializer,
        responses=TaskSerializer,
        tags=["Tasks"],
    )
    def patch(self, request, task_id: int):
        task = self.get_task(request, task_id)
        serializer = TaskUpdateSerializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(TaskSerializer(task).data)

    @extend_schema(operation_id="delete_task", responses={204: None}, tags=["Tasks"])
    def delete(self, request, task_id: int):
        task = self.get_task(request, task_id)
        if task.created_by_id != request.user.id:
            raise PermissionDenied("Only the task creator can delete it.")
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCompleteApi(APIView):
    @extend_schema(
        operation_id="complete_task", request=None, responses=TaskSerializer, tags=["Tasks"]
    )
    def post(self, request, task_id: int):
        task = selectors.get_task(request.user, task_id)
        if task is None:
            raise NotFound("Task not found.")
        return Response(TaskSerializer(services.complete_task(task)).data)


class TaskReopenApi(APIView):
    @extend_schema(
        operation_id="reopen_task", request=None, responses=TaskSerializer, tags=["Tasks"]
    )
    def post(self, request, task_id: int):
        task = selectors.get_task(request.user, task_id)
        if task is None:
            raise NotFound("Task not found.")
        return Response(TaskSerializer(services.reopen_task(task)).data)


class TaskAssignApi(APIView):
    @extend_schema(
        operation_id="assign_task",
        request=TaskAssignSerializer,
        responses=TaskSerializer,
        tags=["Tasks"],
    )
    def post(self, request, task_id: int):
        task = selectors.get_task(request.user, task_id)
        if task is None:
            raise NotFound("Task not found.")
        serializer = TaskAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = services.assign_task(task, serializer.validated_data["user"])
        return Response(TaskSerializer(task).data)
