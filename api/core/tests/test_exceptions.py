import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from rest_framework.exceptions import APIException, NotFound
from rest_framework.views import APIView

from core.exceptions import SpecAlreadyPublishedError, exception_handler

CONTEXT = {"view": APIView(), "request": None}


def test_field_errors_become_field_to_list_map():
    response = exception_handler(ValidationError({"title": "Too short."}), CONTEXT)
    assert response.status_code == 400
    assert response.data == {"title": ["Too short."]}


def test_non_field_errors_use_the_drf_key():
    exc = ValidationError({"__all__": ["Inconsistent."], "status": ["Invalid."]})
    response = exception_handler(exc, CONTEXT)
    assert response.status_code == 400
    assert response.data == {"non_field_errors": ["Inconsistent."], "status": ["Invalid."]}


def test_plain_validation_error_becomes_detail():
    response = exception_handler(ValidationError("Something is wrong."), CONTEXT)
    assert response.status_code == 400
    assert response.data == {"detail": "Something is wrong."}


def test_permission_denied_keeps_its_message():
    response = exception_handler(PermissionDenied("Only the creator."), CONTEXT)
    assert response.status_code == 403
    assert response.data == {"detail": "Only the creator."}


def test_permission_denied_without_message_uses_the_default():
    response = exception_handler(PermissionDenied(), CONTEXT)
    assert response.status_code == 403
    assert "detail" in response.data


def test_drf_exceptions_are_untouched():
    response = exception_handler(NotFound("Task not found."), CONTEXT)
    assert response.status_code == 404
    assert response.data == {"detail": "Task not found."}


def test_other_exceptions_are_not_handled():
    assert exception_handler(RuntimeError("boom"), CONTEXT) is None


@pytest.mark.django_db
def test_service_errors_reach_the_client_in_drf_format(auth, user, other_user):
    from tasks.models import Task

    task = Task.objects.create(title="Not mine", created_by=other_user, assigned_to=user)
    response = auth.delete(f"/api/v1/tasks/{task.id}/")
    assert response.status_code == 403
    assert response.data == {"detail": "Only the task creator can delete it."}


def test_spec_already_published_maps_to_409():
    response = exception_handler(SpecAlreadyPublishedError(), CONTEXT)
    assert response.status_code == 409
    assert response.data == {"detail": "Spec already published."}


def test_spec_already_published_is_not_a_drf_exception():
    assert not isinstance(SpecAlreadyPublishedError(), APIException)
