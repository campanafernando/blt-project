from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from tasks import selectors
from tasks.serializers import UserBriefSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "is_active")
        read_only_fields = fields


class LoginView(TokenObtainPairView):
    throttle_scope = "login"


class MeApi(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(operation_id="me", responses=UserSerializer, tags=["Auth"])
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserListApi(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="list_users", responses=UserBriefSerializer(many=True), tags=["Auth"]
    )
    def get(self, request):
        return Response(UserBriefSerializer(selectors.assignee_list(), many=True).data)
