from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions, status
from rest_framework.views import exception_handler as drf_exception_handler


class SpecAlreadyPublishedError(Exception):
    """A spec can become a Gitea issue only once."""

    def __init__(self, message: str = "Spec already published."):
        super().__init__(message)


def exception_handler(exc, context):
    """DRF's handler, plus Django exceptions raised by services in the DRF error format."""
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "error_dict"):
            detail = {
                ("non_field_errors" if field == NON_FIELD_ERRORS else field): messages
                for field, messages in exc.message_dict.items()
            }
        else:
            detail = {"detail": " ".join(exc.messages)}
        exc = exceptions.ValidationError(detail)
    elif isinstance(exc, DjangoPermissionDenied):
        # DRF's default conversion drops the message.
        exc = exceptions.PermissionDenied(str(exc) or None)
    elif isinstance(exc, SpecAlreadyPublishedError):
        exc = exceptions.APIException(str(exc))
        exc.status_code = status.HTTP_409_CONFLICT
    return drf_exception_handler(exc, context)
