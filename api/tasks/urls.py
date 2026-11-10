from django.urls import path

from .views import (
    TaskAssignApi,
    TaskCompleteApi,
    TaskDetailApi,
    TaskListApi,
    TaskReopenApi,
    TaskSummaryApi,
)

app_name = "tasks"

urlpatterns = [
    path("tasks/", TaskListApi.as_view(), name="list"),
    path("tasks/summary/", TaskSummaryApi.as_view(), name="summary"),
    path("tasks/<int:task_id>/", TaskDetailApi.as_view(), name="detail"),
    path("tasks/<int:task_id>/complete/", TaskCompleteApi.as_view(), name="complete"),
    path("tasks/<int:task_id>/reopen/", TaskReopenApi.as_view(), name="reopen"),
    path("tasks/<int:task_id>/assign/", TaskAssignApi.as_view(), name="assign"),
]
