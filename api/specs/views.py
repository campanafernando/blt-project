from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from core.pagination import StandardPagination

from . import selectors, services
from .serializers import (
    SpecConfigSerializer,
    SpecCreateSerializer,
    SpecSerializer,
)


class SpecConfigApi(APIView):
    @extend_schema(operation_id="spec_config", responses=SpecConfigSerializer, tags=["Specs"])
    def get(self, request):
        data = {
            "ai_enabled": settings.AI_ENABLED,
            "publish_enabled": bool(settings.GITHUB_TOKEN),
            "model": settings.OPENCODE_MODEL,
            "prompt_version": settings.SPEC_PROMPT_VERSION,
            "max_input_chars": settings.SPEC_MAX_INPUT_CHARS,
        }
        return Response(SpecConfigSerializer(data).data)


class SpecListCreateApi(APIView):
    throttle_scope = "spec"

    @extend_schema(operation_id="list_specs", responses=SpecSerializer(many=True), tags=["Specs"])
    def get(self, request):
        paginator = StandardPagination()
        page = paginator.paginate_queryset(selectors.specs_for(request.user), request, view=self)
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
        spec = services.generate_spec(
            user=request.user, issue_url=serializer.validated_data["issue_url"]
        )
        return Response(SpecSerializer(spec).data, status=status.HTTP_201_CREATED)


class SpecDetailApi(APIView):
    @extend_schema(operation_id="get_spec", responses=SpecSerializer, tags=["Specs"])
    def get(self, request, spec_id: int):
        spec = selectors.get_spec(request.user, spec_id)
        if spec is None:
            raise NotFound("Spec não encontrada.")
        return Response(SpecSerializer(spec).data)


class SpecPublishApi(APIView):
    @extend_schema(
        operation_id="publish_spec", request=None, responses=SpecSerializer, tags=["Specs"]
    )
    def post(self, request, spec_id: int):
        spec = selectors.get_spec(request.user, spec_id)
        if spec is None:
            raise NotFound("Spec não encontrada.")
        return Response(SpecSerializer(services.publish_spec(spec=spec)).data)
