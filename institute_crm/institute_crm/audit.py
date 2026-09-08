"""
Fine-grained audit logging for the service layer.

``accounts.middleware.AuditLogMiddleware`` already records one coarse row per mutating
HTTP request ("someone POSTed to /api/v1/crm/leads/"). That is useful for traffic
forensics but useless for answering "who changed this student's batch, and from what?".

Service methods use :func:`record_audit` to write the semantic entry: which model, which
record, which fields changed, and who did it. Both layers coexist deliberately - the
middleware cannot know intent, and the service cannot know the request.

Design rules
------------
* **Never let auditing break the operation it describes.** Every failure here is logged
  and swallowed. A broken audit sink must not roll back a fee payment.
* **Never store credentials or raw secrets.** Values matching :data:`REDACTED_FIELDS` are
  replaced with ``"***"`` before persistence.
* Call it *inside* the same ``transaction.atomic`` block as the change, so the audit row
  and the change are committed together.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Mapping

from django.db import models

logger = logging.getLogger("institute_crm.audit")

CREATE = "CREATE"
UPDATE = "UPDATE"
DELETE = "DELETE"
LOGIN = "LOGIN"
LOGIN_FAILED = "LOGIN_FAILED"
LOGOUT = "LOGOUT"
PASSWORD_CHANGE = "PASSWORD_CHANGE"
PASSWORD_RESET = "PASSWORD_RESET"
CONVERT = "CONVERT"
PUBLISH = "PUBLISH"
REVOKE = "REVOKE"
PAYMENT = "PAYMENT"
REFUND = "REFUND"

#: Field names whose values must never be written to the audit trail.
REDACTED_FIELDS = frozenset(
    {
        "password",
        "new_password",
        "old_password",
        "confirm_password",
        "temporary_password",
        "temp_password",
        "token",
        "access",
        "refresh",
        "access_token",
        "refresh_token",
        "secret",
        "api_key",
        "otp",
        "cognito_tokens",
    }
)

_REDACTION = "***"


def scrub(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``data`` with sensitive values replaced."""
    if not data:
        return {}
    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in REDACTED_FIELDS:
            cleaned[key] = _REDACTION
        elif isinstance(value, Mapping):
            cleaned[key] = scrub(value)
        else:
            cleaned[key] = _serialise(value)
    return cleaned


def _serialise(value: Any) -> Any:
    """Coerce a value into something ``JSONField`` will accept."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, models.Model):
        return str(value.pk)
    if isinstance(value, (list, tuple, set)):
        return [_serialise(item) for item in value]
    return str(value)


def diff_fields(
    instance: models.Model,
    updates: Mapping[str, Any],
    *,
    fields: Iterable[str] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build a ``{field: {"from": old, "to": new}}`` map for changed fields only.

    Call this *before* applying ``updates`` to ``instance``. Unchanged fields are
    omitted so the audit trail stays readable.
    """
    considered = set(fields) if fields is not None else set(updates.keys())
    changes: dict[str, dict[str, Any]] = {}
    for field in considered:
        if field not in updates:
            continue
        new_value = updates[field]
        old_value = getattr(instance, field, None)
        if old_value == new_value:
            continue
        if field.lower() in REDACTED_FIELDS:
            changes[field] = {"from": _REDACTION, "to": _REDACTION}
        else:
            changes[field] = {"from": _serialise(old_value), "to": _serialise(new_value)}
    return changes


def record_audit(
    *,
    actor: Any | None,
    action: str,
    instance: models.Model | None = None,
    model_name: str | None = None,
    target_id: Any | None = None,
    changes: Mapping[str, Any] | None = None,
    ip_address: str | None = None,
) -> Any | None:
    """Write one :class:`accounts.models.AuditLog` row. Never raises.

    Either pass ``instance`` (model name and pk are derived) or both ``model_name`` and
    ``target_id`` for non-model events such as a failed login.

    Returns the created row, or ``None`` if the write was skipped or failed.
    """
    # Imported lazily: this module is imported by services that Django loads during app
    # registry population, before the model layer is ready.
    from accounts.models import AuditLog

    try:
        if instance is not None:
            model_name = model_name or type(instance).__name__
            target_id = target_id if target_id is not None else instance.pk

        actor_obj = actor if getattr(actor, "pk", None) else None

        return AuditLog.objects.create(
            actor=actor_obj,
            action=action[:50],
            model_name=(model_name or "UNKNOWN")[:100],
            target_id=str(target_id or "")[:128],
            changes=scrub(changes),
            ip_address=ip_address,
        )
    except Exception:
        # An audit failure must never propagate into the business operation.
        logger.warning(
            "Failed to write audit entry (action=%s model=%s target=%s)",
            action,
            model_name,
            target_id,
            exc_info=True,
        )
        return None


def client_ip(request: Any) -> str | None:
    """Best-effort client IP, honouring a single proxy hop.

    Only trust ``X-Forwarded-For`` when the deployment actually sits behind a proxy that
    sets it; nginx.conf in this repo does.
    """
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")
