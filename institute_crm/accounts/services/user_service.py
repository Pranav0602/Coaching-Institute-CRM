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
        if actor.role_code in (Role.BRANCH_ADMIN, Role.ADMISSION_COUNSELOR):
            # A branch admin with no branch assigned is a data error; return nothing
            # rather than silently exposing every branch.
            return base.filter(branch_id=actor.branch_id) if actor.branch_id else base.none()
        if actor.role_code == Role.RECEPTIONIST:
            # The reception desk may see the student roster of its own campus, but not
            # arbitrary staff accounts. Fails closed without a branch.
            if not actor.branch_id:
                return base.none()
            return base.filter(branch_id=actor.branch_id, role__code=Role.STUDENT)
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
    def _generate_username(*, first_name: str = "", last_name: str = "", email: str = "") -> str:
        """Build a unique, human-readable username for a direct onboarding.

        Preference order: the email local-part, then first/last name. A short numeric
        suffix is appended until the value is free, so two students called "Rahul"
        never collide.
        """
        candidates = []
        if email:
            candidates.append(email.split("@", 1)[0])
        joined = f"{first_name or ''}{last_name or ''}".strip()
        if joined:
            candidates.append(joined)

        base = next((c for c in candidates if c), "student")
        base = "".join(ch for ch in base.lower() if ch.isalnum()) or "student"
        base = base[:24]

        username = base
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            suffix += 1
            username = f"{base}{suffix}"
        return username

    @staticmethod
    def _assert_phone_available(phone: str | None, *, exclude_pk=None) -> None:
        """Reject a phone number already held by a live account.

        The column is not unique at the database level (guardians share numbers), so the
        check is deliberately at the service boundary and only for direct onboarding.
        """
        if not phone:
            return
        queryset = User.objects.filter(is_deleted=False, phone=phone)
        if exclude_pk is not None:
            queryset = queryset.exclude(pk=exclude_pk)
        if queryset.exists():
            raise ConflictError(
                "That phone number is already registered to another account.",
                code="phone_taken",
                field_errors={"phone": ["This phone number is already in use."]},
            )

    @staticmethod
    @transaction.atomic
    def create_user(*, actor: User, data: dict[str, Any], ip_address: str | None = None) -> User:
        """Create a staff or student account.

        Administrators may create any role. A receptionist may create student accounts
        only, and those are pinned to the receptionist's own branch. A branch admin's
        new users are likewise pinned to their own branch.
        """
        if not (actor.is_admin_role or actor.role_code == Role.RECEPTIONIST):
            raise PermissionDeniedError("Only administrators can create user accounts.")

        payload = dict(data)
        password = payload.pop("password", None)
        role = payload.get("role")

        if actor.role_code == Role.RECEPTIONIST:
            if not actor.branch_id:
                raise ValidationFailed(
                    "Your account is not assigned to a branch, so it cannot create students.",
                    code="actor_without_branch",
                )
            if role is not None and getattr(role, "code", role) != Role.STUDENT:
                raise PermissionDeniedError(
                    "The reception desk can only create student accounts.",
                    code="receptionist_student_only",
                )
            if role is None:
                role = Role.objects.filter(code=Role.STUDENT).first()
                if role is None:
                    raise ValidationFailed(
                        "The Student role is not configured.", code="student_role_missing"
                    )
            payload["role"] = role
            payload["branch"] = actor.branch

        if actor.role_code == Role.BRANCH_ADMIN:
            if not actor.branch_id:
                raise ValidationFailed(
                    "Your account is not assigned to a branch, so it cannot create users.",
                    code="actor_without_branch",
                )
            payload["branch"] = actor.branch

        username = (payload.get("username") or "").strip()
        if not username:
            username = UserService._generate_username(
                first_name=payload.get("first_name", ""),
                last_name=payload.get("last_name", ""),
                email=payload.get("email", ""),
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ConflictError(
                f"The username '{username}' is already taken.",
                code="username_taken",
                field_errors={"username": ["This username is already taken."]},
            )
        payload["username"] = username

        UserService._assert_phone_available(payload.get("phone"))

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
    def create_student(
        *, actor: User, data: dict[str, Any], ip_address: str | None = None
    ) -> dict[str, Any]:
        """Direct student onboarding from the reception desk.

        Unlike lead conversion, this does not require a lead to move through the
        pipeline. It creates the student user, their profile (with guardian details) and,
        when a batch is supplied, a course enrolment. All branch/capacity invariants are
        delegated to :class:`EnrolmentService`.
        """
        from academics.services import EnrolmentService
        from users_profiles.models import StudentProfile

        if not (actor.is_admin_role or actor.role_code in (Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR)):
            raise PermissionDeniedError("Only admissions and administrative staff can add students.")

        payload = dict(data)
        first_name = (payload.get("first_name") or "").strip()
        last_name = (payload.get("last_name") or "").strip()
        email = (payload.get("email") or "").strip()
        phone = (payload.get("phone") or "").strip() or None

        if not first_name:
            raise ValidationFailed(
                "A first name is required.",
                field_errors={"first_name": ["This field is required."]},
            )
        if not email:
            raise ValidationFailed(
                "An email address is required.",
                field_errors={"email": ["This field is required."]},
            )
        if User.objects.filter(email__iexact=email, is_deleted=False).exists():
            raise ConflictError(
                "A user with this email already exists.",
                code="email_taken",
                field_errors={"email": ["A user with this email already exists."]},
            )

        student_role = Role.objects.filter(code=Role.STUDENT).first()
        if student_role is None:
            raise ValidationFailed(
                "The Student role is not configured.", code="student_role_missing"
            )

        branch = payload.get("branch")
        if actor.role_code in (Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR):
            if not actor.branch_id:
                raise ValidationFailed(
                    "Your account is not assigned to a branch, so it cannot add students.",
                    code="actor_without_branch",
                )
            branch = actor.branch
        if branch is None:
            raise ValidationFailed(
                "A branch is required.",
                field_errors={"branch": ["This field is required."]},
            )

        course = payload.get("course")
        batch = payload.get("batch")
        if batch is not None:
            if course is not None and getattr(batch, "course_id", None) != getattr(course, "pk", None):
                raise ValidationFailed(
                    "The selected batch does not run the selected course.",
                    field_errors={"batch": ["Choose a batch that belongs to this course."]},
                )
            if getattr(batch, "branch_id", None) != getattr(branch, "pk", None):
                raise ValidationFailed(
                    "The selected batch belongs to another branch.",
                    field_errors={"batch": ["Choose a batch in the selected branch."]},
                )
            course = course or batch.course

        password = payload.get("password") or None
        generated_password = None
        if not password:
            import uuid as _uuid

            generated_password = f"Pass@{_uuid.uuid4().hex[:8]}"
            password = generated_password

        user = UserService.create_user(
            actor=actor,
            data={
                "username": payload.get("username"),
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "phone": phone,
                "role": student_role,
                "branch": branch,
                "password": password,
            },
            ip_address=ip_address,
        )

        reg_no = (payload.get("reg_no") or "").strip()
        if not reg_no:
            import uuid as _uuid

            reg_no = (
                f"ENR/{getattr(branch, 'code', 'BR')}/{timezone.now().year}/"
                f"{_uuid.uuid4().hex[:5].upper()}"
            )
        if StudentProfile.objects.filter(reg_no__iexact=reg_no, is_deleted=False).exists():
            raise ConflictError(
                "That registration number is already in use.",
                code="reg_no_taken",
                field_errors={"reg_no": ["This registration number is already in use."]},
            )

        profile = StudentProfile.objects.create(
            user=user,
            reg_no=reg_no,
            dob=payload.get("dob") or None,
            gender=payload.get("gender") or "MALE",
            blood_group=payload.get("blood_group") or None,
            address=payload.get("address") or None,
            emergency_contact=payload.get("guardian_phone") or payload.get("emergency_contact") or None,
            secondary_phone=payload.get("secondary_phone") or None,
            guardian_name=payload.get("guardian_name") or None,
            guardian_phone=payload.get("guardian_phone") or None,
            guardian_relationship=payload.get("guardian_relationship") or None,
            course=course,
            batch=batch,
        )

        enrolment = None
        if batch is not None:
            enrolment = EnrolmentService.enrol_student(
                actor=actor,
                data={"student": user, "course": course, "batch": batch},
                ip_address=ip_address,
            )

        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=profile,
            model_name="StudentProfile",
            changes={
                "student": str(user.pk),
                "reg_no": reg_no,
                "branch": str(branch.pk),
                "course": str(course.pk) if course else None,
                "batch": str(batch.pk) if batch else None,
            },
            ip_address=ip_address,
        )

        return {
            "user": user,
            "profile": profile,
            "enrolment": enrolment,
            "temporary_password": generated_password,
        }

    @staticmethod
    @transaction.atomic
    def update_user(
        *,
        actor: User,
        user: User,
        data: dict[str, Any],
        ip_address: str | None = None,
    ) -> User:
        """Administrative update of another user (or oneself).

        The reception desk may correct contact details on a student in its own branch;
        it cannot touch staff accounts, roles, branches or activation flags.
        """
        is_self = actor.pk == user.pk
        is_reception_edit = (
            actor.role_code == Role.RECEPTIONIST
            and not is_self
            and user.role_code == Role.STUDENT
            and actor.branch_id
            and user.branch_id == actor.branch_id
        )
        if not (is_self or actor.is_admin_role or is_reception_edit):
            raise PermissionDeniedError("You can only edit your own profile.")

        payload = dict(data)
        password = payload.pop("password", None)

        if is_reception_edit:
            # Contact details only - no role, branch, password or status changes.
            allowed = set(SELF_EDITABLE_FIELDS)
            payload = {key: value for key, value in payload.items() if key in allowed}
            password = None

        # Privilege escalation guard: only a super admin may reassign role or branch.
        if not (actor.is_superuser or actor.role_code == Role.SUPER_ADMIN):
            for protected in ("role", "branch", "is_superuser", "is_staff"):
                payload.pop(protected, None)

        email = payload.get("email")
        if email and User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            raise ConflictError(
                "That email address is already in use by another account.",
                code="email_taken",
                field_errors={"email": ["This email address is already in use."]},
            )
        if "phone" in payload:
            UserService._assert_phone_available(payload.get("phone"), exclude_pk=user.pk)

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
