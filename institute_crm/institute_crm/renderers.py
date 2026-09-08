"""
Uniform API response shaping.

Every successful response is wrapped as ``{success, message, data}``, and every failure
as ``{success, message, errors, status_code}``. The frontend axios interceptor in
``frontend/src/services/api.js`` relies on this contract, so changes here are
breaking changes for the client.
"""
import logging

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import renderers, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

from institute_crm.exceptions import DomainError

logger = logging.getLogger("institute_crm.api")


def _domain_error_response(exc: DomainError) -> Response:
    """Render a service-layer domain failure.

    These are *expected* outcomes (a lead already admitted, a batch already full), so
    they are logged at INFO rather than ERROR and never include a traceback.
    """
    errors = exc.field_errors or {"detail": exc.message}
    logger.info("Domain error (%s): %s", exc.code, exc.message)
    return Response(
        {
            "success": False,
            "message": exc.message,
            "errors": errors,
            "code": exc.code,
            "status_code": exc.status_code,
        },
        status=exc.status_code,
    )


def custom_exception_handler(exc, context):
    """DRF exception handler covering domain errors, DRF errors and unhandled crashes."""
    # 1. Service-layer domain errors carry their own status code and message.
    if isinstance(exc, DomainError):
        return _domain_error_response(exc)

    # 2. Translate common Django-level exceptions that DRF does not map by default.
    if isinstance(exc, ObjectDoesNotExist) and not isinstance(exc, Http404):
        # e.g. a bare `Model.objects.get()` inside a service.
        logger.info("Record not found: %s", exc)
        return Response(
            {
                "success": False,
                "message": "The requested record was not found.",
                "errors": {"detail": str(exc)},
                "code": "not_found",
                "status_code": status.HTTP_404_NOT_FOUND,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, DjangoPermissionDenied):
        return Response(
            {
                "success": False,
                "message": "You do not have permission to perform this action.",
                "errors": {"detail": str(exc) or "Permission denied."},
                "code": "permission_denied",
                "status_code": status.HTTP_403_FORBIDDEN,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # 3. Standard DRF handling (validation, auth, throttling, 404, ...).
    response = exception_handler(exc, context)

    if response is not None:
        payload = {
            "success": False,
            "message": "Validation or execution error occurred.",
            "errors": response.data,
            "status_code": response.status_code,
        }
        if isinstance(response.data, dict) and "detail" in response.data:
            payload["message"] = str(response.data["detail"])
        elif isinstance(response.data, dict) and response.data:
            # Surface the first field error so the UI has something specific to show
            # instead of a generic banner.
            first_field, first_error = next(iter(response.data.items()))
            if isinstance(first_error, (list, tuple)) and first_error:
                payload["message"] = f"{first_field}: {first_error[0]}"
        response.data = payload
        return response

    # 4. Genuinely unexpected: log with a traceback and never leak internals.
    view = context.get("view") if context else None
    request = context.get("request") if context else None
    logger.error(
        "Unhandled exception in %s (%s %s)",
        type(view).__name__ if view else "unknown view",
        getattr(request, "method", "?"),
        getattr(request, "path", "?"),
        exc_info=True,
    )
    return Response(
        {
            "success": False,
            "message": "Internal Server Error",
            "errors": {"detail": "An unexpected error occurred. The issue has been logged."},
            "code": "internal_error",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


class StandardResponseRenderer(renderers.JSONRenderer):
    """Wrap successful payloads in the standard envelope.

    Responses that already carry a ``success`` key (errors from the handler above, or a
    view that shapes its own envelope) pass through untouched.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        status_code = response.status_code if response is not None else 200

        if isinstance(data, dict) and "success" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # 204 No Content must have an empty body.
        if status_code == status.HTTP_204_NO_CONTENT:
            return b""

        wrapped = {
            "success": status_code < 400,
            "message": "Request processed successfully" if status_code < 400 else "Error",
            "data": data,
        }
        return super().render(wrapped, accepted_media_type, renderer_context)
