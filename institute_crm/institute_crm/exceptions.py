"""
Domain exceptions shared by every service module.

Why these exist
---------------
Services must be callable from anywhere - a DRF view, a management command, a future
Celery task, a RAG source adapter - so they cannot raise DRF exceptions without dragging
HTTP concerns into the domain layer. They also should not raise bare ``ValueError``,
because that is indistinguishable from a genuine programming bug and gets reported to
clients as a 500.

Instead services raise a :class:`DomainError` subclass. ``institute_crm.renderers
.custom_exception_handler`` translates each one into the right status code and the
project's standard ``{success, message, errors, status_code}`` envelope.

Usage::

    from institute_crm.exceptions import ConflictError, NotFoundError

    lead = Lead.objects.filter(pk=lead_id).first()
    if lead is None:
        raise NotFoundError("Lead not found.", code="lead_not_found")
    if lead.stage == Lead.STAGE_ADMITTED:
        raise ConflictError(f"Lead '{lead.name}' is already admitted.")

Attach ``field_errors`` when the problem maps onto specific input fields so the frontend
can highlight them::

    raise ValidationFailed(
        "Could not update your profile.",
        field_errors={"phone": ["Enter a 10-digit mobile number."]},
    )
"""
from __future__ import annotations

from typing import Any, Mapping


class DomainError(Exception):
    """Base class for expected, business-rule failures.

    ``status_code`` is advisory - the exception handler owns the HTTP mapping - but
    keeping it here means a single subclass definition covers both concerns.
    """

    status_code: int = 400
    default_message: str = "The request could not be completed."
    default_code: str = "domain_error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        field_errors: Mapping[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.field_errors: dict[str, Any] = dict(field_errors or {})
        super().__init__(self.message)

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "detail": self.message}
        if self.field_errors:
            payload["fields"] = self.field_errors
        return payload

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"{type(self).__name__}({self.message!r}, code={self.code!r})"


class ValidationFailed(DomainError):
    """Input is well-formed but violates a business rule."""

    status_code = 400
    default_message = "The submitted data is not valid."
    default_code = "validation_failed"


class NotFoundError(DomainError):
    """A referenced record does not exist, or is not visible to the caller.

    Deliberately also used for records the caller may not see, so that probing an ID
    cannot be used to confirm its existence.
    """

    status_code = 404
    default_message = "The requested record was not found."
    default_code = "not_found"


class PermissionDeniedError(DomainError):
    """The caller is authenticated but not allowed to perform this action."""

    status_code = 403
    default_message = "You do not have permission to perform this action."
    default_code = "permission_denied"


class AuthenticationFailed(DomainError):
    """Credentials were supplied but are not valid."""

    status_code = 401
    default_message = "Invalid credentials."
    default_code = "authentication_failed"


class ConflictError(DomainError):
    """The action contradicts the current state of the record.

    Examples: converting an already-admitted lead, double-marking attendance,
    enrolling into a full batch, publishing results twice.
    """

    status_code = 409
    default_message = "This action conflicts with the current state of the record."
    default_code = "conflict"


class ExternalServiceError(DomainError):
    """A third-party dependency (AWS, payment gateway, LLM provider) failed.

    Raise this only when the failure is *fatal* to the operation. Optional integrations
    - Cognito provisioning, SES notifications - should be logged and swallowed so a
    downstream outage cannot block an admission or a payment record.
    """

    status_code = 502
    default_message = "An upstream service is currently unavailable."
    default_code = "external_service_error"


class ConfigurationError(DomainError):
    """A required setting or piece of reference data is missing.

    Distinct from ``ImproperlyConfigured`` (which is a startup concern) - this covers
    runtime gaps such as "no fee structure defined for this course".
    """

    status_code = 500
    default_message = "The system is not configured to complete this action."
    default_code = "configuration_error"
