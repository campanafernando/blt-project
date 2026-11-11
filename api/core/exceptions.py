from django.core.exceptions import NON_FIELD_ERRORS
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler


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
    return drf_exception_handler(exc, context)
