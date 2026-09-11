"""
Authentication and credential lifecycle.

Covers login (Django auth + JWT issuance with custom claims, optional Cognito sync),
self-service password change, and the forgot/reset password flow.

Security posture
----------------
* Login accepts a username *or* an email address, but never reveals which of the two
  failed - both produce the same ``AuthenticationFailed``.
* The forgot-password endpoint always reports success, so it cannot be used to enumerate
  registered accounts.
* Soft-deleted and deactivated users cannot authenticate even with correct credentials.
* AWS Cognito is treated as an *optional mirror*: an outage there logs a warning and the
  local login still succeeds. Cognito tokens are never written to the audit trail.
"""
from __future__ import annotations

import logging
import secrets
import threading
from typing import Any

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from institute_crm import audit
from institute_crm.exceptions import (
    AuthenticationFailed,
    NotFoundError,
    ValidationFailed,
)

logger = logging.getLogger("institute_crm.accounts")

#: Placeholder OTP retained for the existing demo flow. Real delivery (SES/SNS) is a
#: follow-up; see `AuthService.request_password_reset`.
DEMO_OTP = "123456"


class AuthService:
    # ------------------------------------------------------------------ login

    @staticmethod
    def _record_audit_async(**kwargs: Any) -> None:
        """Fire-and-forget audit write so auth responses never wait on the INSERT.

        Runs :func:`institute_crm.audit.record_audit` on a daemon thread with its
        own DB connection. Audit already swallows its own errors; this only adds
        that a slow audit sink cannot add 200-500ms to login latency.
        """

        def _write() -> None:
            from django.db import connection

            try:
                # Drop any inherited (and unusable across threads) connection
                # so this thread opens a fresh one.
                connection.close()
                audit.record_audit(**kwargs)
            except Exception:  # pragma: no cover - record_audit never raises
                logger.warning("Async audit write failed", exc_info=True)
            finally:
                try:
                    connection.close()
                except Exception:
                    pass

        thread = threading.Thread(target=_write, daemon=True, name="audit-login")
        try:
            # Inside an explicit transaction (e.g. tests wrapping each case in
            # an atomic block) defer the spawn until commit, so the background
            # connection can actually see the actor row. Outside a transaction
            # (normal production login) this fires immediately.
            transaction.on_commit(thread.start)
        except Exception:  # pragma: no cover - defensive fallback
            thread.start()

    @staticmethod
    def login(*, username: str, password: str, ip_address: str | None = None) -> dict[str, Any]:
        """Authenticate and return tokens plus the user record.

        ``username`` may be a username or an email address.
        Raises :class:`AuthenticationFailed` for every failure mode.
        """
        user = AuthService._authenticate(username=username, password=password)

        if user is None:
            # Recorded without the supplied password, and with the attempted identifier
            # truncated, so the trail is useful for brute-force detection but not itself
            # a credential leak. Async: must not delay the 401 response.
            AuthService._record_audit_async(
                actor=None,
                action=audit.LOGIN_FAILED,
                model_name="User",
                target_id=username[:128],
                changes={"reason": "invalid_credentials"},
                ip_address=ip_address,
            )
            raise AuthenticationFailed("Invalid username/email or password.")

        if user.is_deleted or not user.is_active:
            AuthService._record_audit_async(
                actor=None,
                action=audit.LOGIN_FAILED,
                instance=user,
                changes={"reason": "inactive_or_deleted"},
                ip_address=ip_address,
            )
            # Same message as bad credentials: do not disclose account state.
            raise AuthenticationFailed("Invalid username/email or password.")

        tokens = AuthService.issue_tokens(user)
        cognito_tokens = AuthService._sync_cognito_login(username=username, password=password)

        AuthService._record_audit_async(
            actor=user,
            action=audit.LOGIN,
            instance=user,
            changes={"method": "password"},
            ip_address=ip_address,
        )
        logger.info("User %s logged in", user.username)

        return {"user": user, "tokens": tokens, "cognito_tokens": cognito_tokens}

    @staticmethod
    def _authenticate(*, username: str, password: str) -> User | None:
        """Resolve credentials with a single DB query and a single password hash.

        The previous implementation called ``django.contrib.auth.authenticate``
        first (one DB lookup + one PBKDF2), then on miss queried by email and
        called ``authenticate`` again (second PBKDF2 plus Django's dummy hash
        for the initial miss). On throttled cloud CPUs that doubled auth cost.

        Now: one indexed ``Q(username__iexact=...) | Q(email__iexact=...)``
        query with ``select_related('role', 'branch')`` so the serializer that
        follows needs zero extra queries, then exactly one
        ``check_password``. When no candidate exists a single dummy
        ``make_password`` preserves constant-time behaviour against account
        enumeration.
        """
        candidate = (
            User.objects.select_related("role", "branch")
            .filter(
                Q(username__iexact=username) | Q(email__iexact=username),
                is_deleted=False,
            )
            .order_by("date_joined")
            .first()
        )
        if candidate is None:
            # Burn one hash so "unknown user" takes ~as long as "wrong
            # password" and cannot be used for enumeration via timing.
            make_password(password)
            return None
        if not candidate.check_password(password):
            return None
        return candidate

    @staticmethod
    def issue_tokens(user: User) -> dict[str, str]:
        """Mint a refresh/access pair carrying role and branch claims.

        Claims let the frontend render role-appropriate navigation without an extra
        round trip. They are *not* trusted for authorisation - permissions always
        re-read the database (see ``accounts/permissions.py``).
        """
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role_code or ""
        refresh["branch_id"] = str(user.branch_id) if user.branch_id else ""
        refresh["username"] = user.username
        return {"access": str(refresh.access_token), "refresh": str(refresh)}

    @staticmethod
    def _sync_cognito_login(*, username: str, password: str) -> dict[str, Any]:
        """Best-effort Cognito authentication. Never blocks a successful local login."""
        try:
            from aws_services.cognito_service import cognito_service, is_cognito_enabled

            if not is_cognito_enabled():
                return {}
            return cognito_service.authenticate(username, password) or {}
        except Exception as exc:
            logger.debug("Cognito authentication unavailable: %s", exc)
            return {}

    # -------------------------------------------------------- password change

    @staticmethod
    @transaction.atomic
    def change_password(
        *,
        user: User,
        old_password: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> User:
        """Rotate the password of an authenticated user.

        Verifies the current password, applies ``AUTH_PASSWORD_VALIDATORS``, refuses a
        no-op change, and stamps ``password_changed_at``.
        """
        if not user.check_password(old_password):
            audit.record_audit(
                actor=user,
                action=audit.PASSWORD_CHANGE,
                instance=user,
                changes={"result": "rejected", "reason": "incorrect_current_password"},
                ip_address=ip_address,
            )
            raise ValidationFailed(
                "Your current password is incorrect.",
                code="incorrect_current_password",
                field_errors={"old_password": ["Your current password is incorrect."]},
            )

        if old_password == new_password:
            raise ValidationFailed(
                "The new password must be different from your current password.",
                code="password_unchanged",
                field_errors={
                    "new_password": ["Choose a password you have not used before."]
                },
            )

        AuthService.validate_password_strength(new_password, user=user)

        user.set_password(new_password)
        user.mark_password_changed()

        AuthService._sync_cognito_password(user=user, new_password=new_password)

        audit.record_audit(
            actor=user,
            action=audit.PASSWORD_CHANGE,
            instance=user,
            changes={"result": "success"},
            ip_address=ip_address,
        )
        logger.info("Password changed for user %s", user.username)
        return user

    @staticmethod
    def validate_password_strength(password: str, *, user: User | None = None) -> None:
        """Run Django's configured validators, re-raised as a domain error.

        Keeps ``AUTH_PASSWORD_VALIDATORS`` as the single source of truth for policy
        instead of duplicating rules in serializers.
        """
        try:
            validate_password(password, user=user)
        except DjangoValidationError as exc:
            raise ValidationFailed(
                "That password does not meet the security requirements.",
                code="password_too_weak",
                field_errors={"new_password": list(exc.messages)},
            ) from exc

    @staticmethod
    def _sync_cognito_password(*, user: User, new_password: str) -> None:
        """Mirror the new password to Cognito when that integration is live."""
        if not user.cognito_sub:
            return
        try:
            from aws_services.cognito_service import cognito_service, is_cognito_enabled

            if not is_cognito_enabled():
                return

            setter = getattr(cognito_service, "set_user_password", None)
            if callable(setter):
                setter(username=user.username, password=new_password, permanent=True)
        except Exception as exc:
            # Local credentials are authoritative; a Cognito drift is recoverable and
            # must not fail the user's password change.
            logger.warning(
                "Could not mirror password change to Cognito for %s: %s", user.username, exc
            )

    # ---------------------------------------------------------- reset by OTP

    @staticmethod
    def request_password_reset(
        *, email_or_username: str, ip_address: str | None = None
    ) -> dict[str, Any]:
        """Start a reset. Always reports success to prevent account enumeration."""
        if not email_or_username:
            raise ValidationFailed(
                "Please provide your email or username.",
                field_errors={"email_or_username": ["This field is required."]},
            )

        user = AuthService._find_by_identifier(email_or_username)

        if user is not None:
            audit.record_audit(
                actor=None,
                action=audit.PASSWORD_RESET,
                instance=user,
                changes={"stage": "requested"},
                ip_address=ip_address,
            )
            # TODO: dispatch a single-use, expiring token via SES/SNS and persist its
            # hash. The fixed DEMO_OTP below is a placeholder and must not ship to
            # production - tracked as part of the auth hardening follow-up.
            logger.info("Password reset requested for %s", user.username)
        else:
            logger.info("Password reset requested for unknown identifier")

        response: dict[str, Any] = {
            "message": (
                "If an account exists with that username/email, a password reset code "
                "has been sent."
            )
        }
        if settings.DEBUG:
            # Only ever exposed in local development.
            response["demo_otp"] = DEMO_OTP
        return response

    @staticmethod
    @transaction.atomic
    def reset_password(
        *,
        email_or_username: str,
        otp: str,
        new_password: str,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Complete a reset using the delivered code."""
        if not new_password:
            raise ValidationFailed(
                "New password is required.",
                field_errors={"new_password": ["This field is required."]},
            )
        if not otp or otp != DEMO_OTP:
            raise ValidationFailed(
                "Invalid or expired verification code.",
                code="invalid_otp",
                field_errors={"otp": ["Invalid or expired verification code."]},
            )

        user = AuthService._find_by_identifier(email_or_username)
        if user is not None:
            AuthService.validate_password_strength(new_password, user=user)
            user.set_password(new_password)
            user.mark_password_changed()
            AuthService._sync_cognito_password(user=user, new_password=new_password)
            audit.record_audit(
                actor=None,
                action=audit.PASSWORD_RESET,
                instance=user,
                changes={"stage": "completed"},
                ip_address=ip_address,
            )
            logger.info("Password reset completed for %s", user.username)

        # Uniform response whether or not the account existed.
        return {
            "message": (
                "Password reset processed. You can now log in with your new password."
            )
        }

    @staticmethod
    def _find_by_identifier(identifier: str) -> User | None:
        if not identifier:
            return None
        return (
            User.objects.filter(username=identifier, is_deleted=False).first()
            or User.objects.filter(email__iexact=identifier, is_deleted=False)
            .order_by("date_joined")
            .first()
        )

    # ------------------------------------------------------------- utilities

    @staticmethod
    def generate_temporary_password(length: int = 12) -> str:
        """Cryptographically strong temporary password for provisioned accounts.

        Replaces the previous ``uuid4().hex`` slices, which are not intended to be
        unguessable. Guarantees at least one character from each required class.
        """
        alphabet = "abcdefghijkmnopqrstuvwxyz"
        upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"
        digits = "23456789"
        symbols = "!@#$%&*?"
        pool = alphabet + upper + digits + symbols
        required = [
            secrets.choice(alphabet),
            secrets.choice(upper),
            secrets.choice(digits),
            secrets.choice(symbols),
        ]
        remaining = [secrets.choice(pool) for _ in range(max(length - len(required), 4))]
        characters = required + remaining
        secrets.SystemRandom().shuffle(characters)
        return "".join(characters)

    @staticmethod
    def get_profile(user: User) -> User:
        """Fetch the authenticated user with role/branch preloaded for serialisation."""
        resolved = (
            User.objects.select_related("role", "branch").filter(pk=user.pk).first()
        )
        if resolved is None:
            raise NotFoundError("Your user account could not be found.")
        return resolved

    @staticmethod
    def days_since_password_change(user: User) -> int | None:
        """Age of the current password in days, or ``None`` if never rotated."""
        if not user.password_changed_at:
            return None
        return (timezone.now() - user.password_changed_at).days
