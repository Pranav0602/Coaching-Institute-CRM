"""
User lifecycle and self-service profile management.

Responsibilities: creating and updating users under branch-scoping rules, soft deletion,
profile detail edits, and profile photo upload/removal (local media, optionally mirrored
to S3).

Branch scoping rule
-------------------
A ``BRANCH_ADMIN`` may only see and administer users in their own branch, and any user
they create is forced into that branch regardless of what the request asked for. This is
enforced here rather than in the view so it holds for management commands and future
callers too.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import Branch, Role, User
from institute_crm import audit
from institute_crm.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailed,
)

logger = logging.getLogger("institute_crm.accounts")

#: Fields a user may edit on their own profile. Deliberately excludes role, branch,
#: is_active and is_staff - privilege changes go through `UserService.update_user`,
#: which is permission-gated.
SELF_EDITABLE_FIELDS = ("first_name", "last_name", "email", "phone")

#: Magic bytes for the image formats we accept. Checked in addition to the file
#: extension, because an extension is attacker-controlled metadata.
_IMAGE_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"RIFF", "webp"),  # followed by 'WEBP' at offset 8
)


class UserService:
    # ------------------------------------------------------------- retrieval

    @staticmethod
    def visible_users(actor: User) -> QuerySet[User]:
        """Base queryset an actor is permitted to see.

        Branch admins are confined to their own branch. Anyone without an
        administrative role sees only themselves.
        """
        base = User.objects.filter(is_deleted=False).select_related("role", "branch")

        if actor.is_superuser or actor.role_code == Role.SUPER_ADMIN:
            return base
        if actor.role_code == Role.BRANCH_ADMIN:
            # A branch admin with no branch assigned is a data error; return nothing
            # rather than silently exposing every branch.
            return base.filter(branch_id=actor.branch_id) if actor.branch_id else base.none()
        return base.filter(pk=actor.pk)

    @staticmethod
    def filter_users(
        actor: User,
        *,
        role: str | None = None,
        branch_id: Any | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> QuerySet[User]:
        """Apply list filters on top of the actor's visibility scope."""
        queryset = UserService.visible_users(actor)

        if role:
            queryset = queryset.filter(role__code=role)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        if search:
            from django.db.models import Q

            term = search.strip()
            queryset = queryset.filter(
                Q(first_name__icontains=term)
                | Q(last_name__icontains=term)
                | Q(username__icontains=term)
                | Q(email__icontains=term)
                | Q(phone__icontains=term)
            )
        return queryset

    @staticmethod
    def get_user_for_actor(actor: User, user_id: Any) -> User:
        """Fetch one user within the actor's scope.

        Raises ``NotFoundError`` (not ``PermissionDeniedError``) for out-of-scope records
        so an ID cannot be probed for existence.
        """
        user = UserService.visible_users(actor).filter(pk=user_id).first()
        if user is None:
            raise NotFoundError("User not found.")
        return user

    # -------------------------------------------------------- create / update

    @staticmethod
    @transaction.atomic
    def create_user(*, actor: User, data: dict[str, Any], ip_address: str | None = None) -> User:
        """Create a staff or student account.

        A branch admin's new users are pinned to the admin's own branch.
        """
        if not actor.is_admin_role:
            raise PermissionDeniedError("Only administrators can create user accounts.")

        payload = dict(data)
        password = payload.pop("password", None)

        if actor.role_code == Role.BRANCH_ADMIN:
            if not actor.branch_id:
                raise ValidationFailed(
                    "Your account is not assigned to a branch, so it cannot create users.",
                    code="actor_without_branch",
                )
            payload["branch"] = actor.branch

        username = payload.get("username")
        if username and User.objects.filter(username=username).exists():
            raise ConflictError(
                f"The username '{username}' is already taken.",
                code="username_taken",
                field_errors={"username": ["This username is already taken."]},
            )

        user = User(**payload)
        if password:
            from accounts.services.auth_service import AuthService

            AuthService.validate_password_strength(password, user=user)
            user.set_password(password)
            user.password_changed_at = timezone.now()
        else:
            # No usable password: the account is provisioned but must go through the
            # reset flow before first login.
            user.set_unusable_password()
        user.save()

        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=user,
            changes={
                "username": user.username,
                "email": user.email,
                "role": user.role_code,
                "branch": str(user.branch_id) if user.branch_id else None,
            },
            ip_address=ip_address,
        )
        logger.info("User %s created by %s", user.username, actor.username)
        return user

    @staticmethod
    @transaction.atomic
    def update_user(
        *,
        actor: User,
        user: User,
        data: dict[str, Any],
        ip_address: str | None = None,
    ) -> User:
        """Administrative update of another user (or oneself)."""
        is_self = actor.pk == user.pk
        if not (is_self or actor.is_admin_role):
            raise PermissionDeniedError("You can only edit your own profile.")

        payload = dict(data)
        password = payload.pop("password", None)

        # Privilege escalation guard: only a super admin may reassign role or branch.
        if not (actor.is_superuser or actor.role_code == Role.SUPER_ADMIN):
            for protected in ("role", "branch", "is_superuser", "is_staff"):
                payload.pop(protected, None)

        changes = audit.diff_fields(user, payload)

        for field, value in payload.items():
            setattr(user, field, value)

        if password:
            from accounts.services.auth_service import AuthService

            AuthService.validate_password_strength(password, user=user)
            user.set_password(password)
            user.password_changed_at = timezone.now()
            changes["password"] = {"from": "***", "to": "***"}

        user.save()

        if changes:
            audit.record_audit(
                actor=actor,
                action=audit.UPDATE,
                instance=user,
                changes=changes,
                ip_address=ip_address,
            )
        return user

    @staticmethod
    @transaction.atomic
    def soft_delete_user(*, actor: User, user: User, ip_address: str | None = None) -> User:
        """Deactivate and hide a user, retaining the row for audit and history."""
        if not actor.is_admin_role:
            raise PermissionDeniedError("Only administrators can remove user accounts.")
        if actor.pk == user.pk:
            raise ConflictError(
                "You cannot delete your own account.", code="cannot_delete_self"
            )

        user.is_deleted = True
        user.is_active = False
        user.save(update_fields=["is_deleted", "is_active", "version"])

        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=user,
            changes={"soft_delete": True, "username": user.username},
            ip_address=ip_address,
        )
        logger.info("User %s soft-deleted by %s", user.username, actor.username)
        return user

    # ------------------------------------------------------ self-service profile

    @staticmethod
    @transaction.atomic
    def update_profile(
        *,
        user: User,
        data: dict[str, Any] | None = None,
        photo: UploadedFile | None = None,
        ip_address: str | None = None,
    ) -> User:
        """Update the signed-in user's own details, and optionally their photo.

        Only :data:`SELF_EDITABLE_FIELDS` are applied; anything else in ``data`` is
        ignored rather than rejected, so a client sending a full user object cannot
        accidentally escalate its own role.
        """
        payload = {
            field: value
            for field, value in (data or {}).items()
            if field in SELF_EDITABLE_FIELDS
        }

        email = payload.get("email")
        if email and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise ConflictError(
                "That email address is already in use by another account.",
                code="email_taken",
                field_errors={"email": ["This email address is already in use."]},
            )

        changes = audit.diff_fields(user, payload)
        for field, value in payload.items():
            setattr(user, field, value)

        if payload:
            user.save()

        if photo is not None:
            UserService.set_profile_photo(user=user, photo=photo, ip_address=ip_address)
            changes["profile_photo"] = {"from": "previous", "to": "updated"}

        if changes:
            audit.record_audit(
                actor=user,
                action=audit.UPDATE,
                instance=user,
                model_name="UserProfile",
                changes=changes,
                ip_address=ip_address,
            )
        return user

    @staticmethod
    @transaction.atomic
    def set_profile_photo(
        *, user: User, photo: UploadedFile, ip_address: str | None = None
    ) -> User:
        """Validate and store a new avatar, replacing any existing one.

        Local media is authoritative. When ``USE_S3_FOR_UPLOADS`` is on the file is also
        mirrored to S3 and the object URL recorded in ``profile_picture``, so the avatar
        keeps resolving if the app server's disk is ephemeral.
        """
        UserService._validate_image(photo)

        old_file = user.profile_photo.name if user.profile_photo else None

        user.profile_photo = photo
        user.save(update_fields=["profile_photo", "version"])

        # Remove the superseded file only after the new one is committed, so a failure
        # never leaves the user without an avatar.
        if old_file:
            UserService._delete_stored_file(user, old_file)

        mirrored_url = UserService._mirror_to_s3(user)
        if mirrored_url:
            user.profile_picture = mirrored_url
            user.save(update_fields=["profile_picture", "version"])

        audit.record_audit(
            actor=user,
            action=audit.UPDATE,
            instance=user,
            model_name="UserProfilePhoto",
            changes={"filename": photo.name, "size_bytes": photo.size},
            ip_address=ip_address,
        )
        logger.info("Profile photo updated for %s", user.username)
        return user

    @staticmethod
    @transaction.atomic
    def remove_profile_photo(*, user: User, ip_address: str | None = None) -> User:
        """Clear the avatar, deleting the stored file and any mirrored URL."""
        if not user.profile_photo and not user.profile_picture:
            raise ConflictError(
                "There is no profile photo to remove.", code="no_profile_photo"
            )

        stored = user.profile_photo.name if user.profile_photo else None

        user.profile_photo = None
        user.profile_picture = None
        user.save(update_fields=["profile_photo", "profile_picture", "version"])

        if stored:
            UserService._delete_stored_file(user, stored)

        audit.record_audit(
            actor=user,
            action=audit.UPDATE,
            instance=user,
            model_name="UserProfilePhoto",
            changes={"removed": True},
            ip_address=ip_address,
        )
        return user

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _validate_image(photo: UploadedFile) -> None:
        """Reject oversized files, disallowed extensions and content/extension mismatch."""
        max_bytes = getattr(settings, "MAX_UPLOAD_SIZE_BYTES", 5 * 1024 * 1024)
        if photo.size and photo.size > max_bytes:
            raise ValidationFailed(
                f"The image is too large. Maximum size is {max_bytes // (1024 * 1024)} MB.",
                code="file_too_large",
                field_errors={"photo": ["Please choose a smaller image."]},
            )
        if not photo.size:
            raise ValidationFailed(
                "The uploaded file is empty.",
                code="empty_file",
                field_errors={"photo": ["The uploaded file is empty."]},
            )

        allowed: Iterable[str] = getattr(
            settings, "ALLOWED_IMAGE_EXTENSIONS", ("jpg", "jpeg", "png", "webp")
        )
        extension = Path(photo.name or "").suffix.lower().lstrip(".")
        if extension not in {ext.lower() for ext in allowed}:
            raise ValidationFailed(
                f"Unsupported image type '.{extension or 'unknown'}'. "
                f"Allowed types: {', '.join(allowed)}.",
                code="unsupported_image_type",
                field_errors={"photo": [f"Allowed types: {', '.join(allowed)}."]},
            )

        # Content sniffing: an extension alone is not evidence of file type.
        try:
            photo.seek(0)
            header = photo.read(12)
            photo.seek(0)
        except Exception:
            header = b""

        if header and not any(header.startswith(sig) for sig, _ in _IMAGE_SIGNATURES):
            raise ValidationFailed(
                "That file does not appear to be a valid image.",
                code="invalid_image_content",
                field_errors={"photo": ["Please upload a valid JPEG, PNG or WebP image."]},
            )

    @staticmethod
    def _delete_stored_file(user: User, name: str) -> None:
        """Delete a superseded media file. Never fatal - an orphan is preferable to a 500."""
        try:
            user.profile_photo.storage.delete(name)
        except Exception as exc:
            logger.warning("Could not delete old profile photo %s: %s", name, exc)

    @staticmethod
    def _mirror_to_s3(user: User) -> str | None:
        """Copy the stored avatar to S3 when configured. Returns the object URL, or None."""
        if not getattr(settings, "USE_S3_FOR_UPLOADS", False):
            return None
        if not user.profile_photo:
            return None
        try:
            from aws_services.s3_service import s3_service

            uploader = getattr(s3_service, "upload_fileobj", None)
            if not callable(uploader):
                return None
            user.profile_photo.open("rb")
            try:
                return uploader(
                    fileobj=user.profile_photo.file,
                    key=user.profile_photo.name,
                    content_type=None,
                )
            finally:
                user.profile_photo.close()
        except Exception as exc:
            # Local media still serves the avatar, so this is a warning, not an error.
            logger.warning("Could not mirror profile photo to S3 for %s: %s", user.username, exc)
            return None

    # -------------------------------------------------------------- summaries

    @staticmethod
    def role_distribution(actor: User) -> list[dict[str, Any]]:
        """Counts of active users per role, within the actor's visibility scope."""
        from django.db.models import Count

        rows = (
            UserService.visible_users(actor)
            .values("role__code", "role__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return [
            {
                "role_code": row["role__code"] or "UNASSIGNED",
                "role_name": row["role__name"] or "Unassigned",
                "count": row["count"],
            }
            for row in rows
        ]


def resolve_branch(branch_id: Any) -> Branch:
    """Fetch an active branch or raise a domain error. Shared by several services."""
    branch = Branch.objects.filter(pk=branch_id, is_deleted=False).first()
    if branch is None:
        raise NotFoundError("Branch not found.", code="branch_not_found")
    return branch
