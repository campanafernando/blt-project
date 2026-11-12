from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination
from tasks.serializers import TaskInputSerializer, TaskSerializer

from . import gitea, selectors, services
from .models import Spec
from .serializers import (
    SpecConfigSerializer,
    SpecCreateSerializer,
    SpecSerializer,
)


def _spec_get_or_404(request, spec_id: int) -> Spec:
    spec = selectors.spec_get(fetched_by=request.user, spec_id=spec_id)
    if spec is None:
        raise NotFound("Spec not found.")
    return spec


class SpecConfigApi(APIView):
    @extend_schema(operation_id="spec_config", responses=SpecConfigSerializer, tags=["Specs"])
    def get(self, request):
        data = {
            "ai_enabled": settings.AI_ENABLED,
            "publish_enabled": gitea.can_publish(),
        }
        return Response(SpecConfigSerializer(data).data)


class SpecListCreateApi(APIView):
    def get_throttles(self):
        # Only generation is expensive; listing must not burn the quota.
        self.throttle_scope = "spec" if self.request.method == "POST" else None
        return super().get_throttles()

    @extend_schema(operation_id="list_specs", responses=SpecSerializer(many=True), tags=["Specs"])
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(
            selectors.spec_list(fetched_by=request.user), request, view=self
        )
        return paginator.get_paginated_response(SpecSerializer(page, many=True).data)

    @extend_schema(
        operation_id="create_spec",
        request=SpecCreateSerializer,
        responses={201: SpecSerializer},
        tags=["Specs"],
    )
    def post(self, request):
        serializer = SpecCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        spec = services.spec_generate(user=request.user, **serializer.validated_data)
        return Response(SpecSerializer(spec).data, status=status.HTTP_201_CREATED)


class SpecDetailApi(APIView):
    @extend_schema(operation_id="get_spec", responses=SpecSerializer, tags=["Specs"])
    def get(self, request, spec_id: int):
        spec = _spec_get_or_404(request, spec_id)
        return Response(SpecSerializer(spec).data)


class SpecPublishApi(APIView):
    throttle_scope = "spec_publish"

    @extend_schema(
        operation_id="publish_spec", request=None, responses=SpecSerializer, tags=["Specs"]
    )
    def post(self, request, spec_id: int):
        spec = _spec_get_or_404(request, spec_id)
        return Response(SpecSerializer(services.spec_publish(spec=spec)).data)


class SpecTasksCreateApi(APIView):
    class InputSerializer(serializers.Serializer):
        # Same item shape as POST /tasks/, so the rules cannot drift apart.
        tasks = TaskInputSerializer(many=True, allow_empty=False, max_length=10)

        class Meta:
            ref_name = "SpecTasksCreate"

    class OutputSerializer(serializers.Serializer):
        tasks = TaskSerializer(many=True)

        class Meta:
            ref_name = "SpecTasksCreated"

    @extend_schema(
        operation_id="create_spec_tasks",
        request=InputSerializer,
        responses={201: OutputSerializer},
        tags=["Specs"],
    )
    def post(self, request, spec_id: int):
        spec = _spec_get_or_404(request, spec_id)
        serializer = self.InputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tasks = services.spec_tasks_create(
            spec=spec, actor=request.user, tasks=serializer.validated_data["tasks"]
        )
        return Response(
            self.OutputSerializer({"tasks": tasks}).data, status=status.HTTP_201_CREATED
        )
