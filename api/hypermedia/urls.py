from django.urls import path

from . import views

app_name = "hypermedia"

urlpatterns = [
    path("", views.board, name="board"),
    path("rows/", views.rows, name="rows"),
    path("tasks/", views.create, name="create"),
    path("tasks/<int:task_id>/complete/", views.complete, name="complete"),
    path("tasks/<int:task_id>/reopen/", views.reopen, name="reopen"),
    path("tasks/<int:task_id>/delete/", views.delete, name="delete"),
]
