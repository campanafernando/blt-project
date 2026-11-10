from django.urls import path

from .views import SpecConfigApi, SpecDetailApi, SpecListCreateApi, SpecPublishApi

app_name = "specs"

urlpatterns = [
    path("specs/", SpecListCreateApi.as_view(), name="list"),
    path("specs/config/", SpecConfigApi.as_view(), name="config"),
    path("specs/<int:spec_id>/", SpecDetailApi.as_view(), name="detail"),
    path("specs/<int:spec_id>/publish/", SpecPublishApi.as_view(), name="publish"),
]
