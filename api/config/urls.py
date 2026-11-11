from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Browsers ask for /favicon.ico on any page, including Swagger and the admin.
    path(
        "favicon.ico",
        RedirectView.as_view(url="/static/hypermedia/favicon.ico", permanent=True),
    ),
    path("admin/", admin.site.urls),
    path("api/v1/", include("tasks.urls")),
    path("api/v1/", include("specs.urls")),
    path("api/v1/auth/", include("accounts.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("app/", include("hypermedia.urls")),
    path(
        "app/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="login",
    ),
    path("app/logout/", auth_views.LogoutView.as_view(), name="logout"),
]
