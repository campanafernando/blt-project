from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, MeApi, UserListApi

app_name = "accounts"

urlpatterns = [
    path("token/", LoginView.as_view(), name="token"),
    path("refresh/", TokenRefreshView.as_view(), name="refresh"),
    path("me/", MeApi.as_view(), name="me"),
    path("users/", UserListApi.as_view(), name="users"),
]
