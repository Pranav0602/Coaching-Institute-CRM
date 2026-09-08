"""
Branch (centre) administration.

A branch is the tenancy boundary for almost every other model in the system, so its
lifecycle rules are stricter than a normal CRUD resource: codes are normalised and
immutable once staff or students are attached, and a branch cannot be removed while it
still holds active records.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from django.db import transaction
from django.db.models import Count, Q, QuerySet

from accounts.models import Branch, Role, User
from institute_crm import audit
from institute_crm.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationFailed,
)

logger = logging.getLogger("institute_crm.accounts")

#: Branch codes appear in receipts, roll numbers and exports, so they are constrained to
#: a short, stable, uppercase alphanumeric token.
BRANCH_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_-]{1,19}$")


class BranchService:
    # ------------------------------------------------------------- retrieval

    @staticmethod
    def visible_branches(actor: User) -> QuerySet[Branch]:
        """Branches an actor may see.

        Super admins see every branch. Everyone else sees only their own, so a branch
        admin cannot enumerate the rest of the organisation.
        """
        base = Branch.objects.filter(is_deleted=False)
        if actor.is_superuser or actor.role_code == Role.SUPER_ADMIN:
            return base
        return base.filter(pk=actor.branch_id) if actor.branch_id else base.none()

    @staticmethod
    def get_branch_for_actor(actor: User, branch_id: Any) -> Branch:
        branch = BranchService.visible_branches(actor).filter(pk=branch_id).first()
        if branch is None:
            raise NotFoundError("Branch not found.", code="branch_not_found")
        return branch

    # -------------------------------------------------------- create / update

    @staticmethod
    @transaction.atomic
    def create_branch(
        *, actor: User, data: dict[str, Any], ip_address: str | None = None
    ) -> Branch:
        """Create a branch. Restricted to super admins - branches are tenancy roots."""
        if not (actor.is_superuser or actor.role_code == Role.SUPER_ADMIN):
            raise PermissionDeniedError("Only a super admin can create branches.")

        payload = dict(data)
        payload["code"] = BranchService.normalise_code(payload.get("code"))
        BranchService._assert_code_available(payload["code"])

        branch = Branch.objects.create(**payload)

        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=branch,
            changes={"code": branch.code, "name": branch.name, "city": branch.city},
            ip_address=ip_address,
        )
        logger.info("Branch %s (%s) created by %s", branch.name, branch.code, actor.username)
        return branch

    @staticmethod
    @transaction.atomic
    def update_branch(
        *,
        actor: User,
        branch: Branch,
        data: dict[str, Any],
        ip_address: str | None = None,
    ) -> Branch:
        """Update branch details.

        A branch admin may edit contact details of their own branch but not its code -
        the code is embedded in already-issued identifiers.
        """
        is_super = actor.is_superuser or actor.role_code == Role.SUPER_ADMIN
        if not is_super:
            if actor.role_code != Role.BRANCH_ADMIN or actor.branch_id != branch.pk:
                raise PermissionDeniedError("You can only edit your own branch.")

        payload = dict(data)

        if "code" in payload:
            new_code = BranchService.normalise_code(payload["code"])
            if new_code != branch.code:
                if not is_super:
                    raise PermissionDeniedError(
                        "Only a super admin can change a branch code."
                    )
                if BranchService.member_count(branch) > 0:
                    raise ConflictError(
                        "This branch code cannot be changed because users are already "
                        "assigned to it.",
                        code="branch_code_locked",
                        field_errors={"code": ["Branch already has assigned users."]},
                    )
                BranchService._assert_code_available(new_code, exclude_pk=branch.pk)
            payload["code"] = new_code

        changes = audit.diff_fields(branch, payload)
        for field, value in payload.items():
            setattr(branch, field, value)
        branch.save()

        if changes:
            audit.record_audit(
                actor=actor,
                action=audit.UPDATE,
                instance=branch,
                changes=changes,
                ip_address=ip_address,
            )
        return branch

    @staticmethod
    @transaction.atomic
    def soft_delete_branch(
        *, actor: User, branch: Branch, ip_address: str | None = None
    ) -> Branch:
        """Retire a branch, refusing while active users remain attached."""
        if not (actor.is_superuser or actor.role_code == Role.SUPER_ADMIN):
            raise PermissionDeniedError("Only a super admin can remove branches.")

        remaining = BranchService.member_count(branch)
        if remaining:
            raise ConflictError(
                f"This branch still has {remaining} active user"
                f"{'s' if remaining != 1 else ''}. Reassign or deactivate them first.",
                code="branch_not_empty",
            )

        branch.is_deleted = True
        branch.save(update_fields=["is_deleted", "version"])

        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=branch,
            changes={"soft_delete": True, "code": branch.code},
            ip_address=ip_address,
        )
        logger.info("Branch %s soft-deleted by %s", branch.code, actor.username)
        return branch

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def normalise_code(code: Any) -> str:
        """Uppercase, trim and validate a branch code."""
        if not code or not str(code).strip():
            raise ValidationFailed(
                "Branch code is required.",
                field_errors={"code": ["This field is required."]},
            )
        normalised = str(code).strip().upper().replace(" ", "_")
        if not BRANCH_CODE_PATTERN.match(normalised):
            raise ValidationFailed(
                "Branch code must be 2-20 characters using letters, numbers, hyphens "
                "or underscores.",
                code="invalid_branch_code",
                field_errors={"code": ["Use 2-20 letters, numbers, '-' or '_'."]},
            )
        return normalised

    @staticmethod
    def _assert_code_available(code: str, *, exclude_pk: Any | None = None) -> None:
        """Guard uniqueness across soft-deleted rows too, since the column is unique."""
        queryset = Branch.objects.filter(code=code)
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
        existing = queryset.first()
        if existing is None:
            return
        if existing.is_deleted:
            raise ConflictError(
                f"Branch code '{code}' belonged to a retired branch. "
                "Choose a different code or restore that branch.",
                code="branch_code_retired",
                field_errors={"code": ["Previously used by a retired branch."]},
            )
        raise ConflictError(
            f"Branch code '{code}' is already in use.",
            code="branch_code_taken",
            field_errors={"code": ["This branch code is already in use."]},
        )

    @staticmethod
    def member_count(branch: Branch) -> int:
        return User.objects.filter(
            branch=branch, is_deleted=False, is_active=True
        ).count()

    # -------------------------------------------------------------- summaries

    @staticmethod
    def branch_statistics(actor: User) -> list[dict[str, Any]]:
        """Per-branch headcount for dashboards, within the actor's visibility scope.

        A single aggregate query rather than N queries per branch.
        """
        rows = (
            BranchService.visible_branches(actor)
            .annotate(
                total_users=Count(
                    "users", filter=Q(users__is_deleted=False, users__is_active=True),
                    distinct=True,
                ),
                student_count=Count(
                    "users",
                    filter=Q(
                        users__is_deleted=False,
                        users__is_active=True,
                        users__role__code=Role.STUDENT,
                    ),
                    distinct=True,
                ),
                teacher_count=Count(
                    "users",
                    filter=Q(
                        users__is_deleted=False,
                        users__is_active=True,
                        users__role__code=Role.TEACHER,
                    ),
                    distinct=True,
                ),
            )
            .order_by("name")
        )

        return [
            {
                "id": str(branch.pk),
                "code": branch.code,
                "name": branch.name,
                "city": branch.city,
                "total_users": branch.total_users,
                "student_count": branch.student_count,
                "teacher_count": branch.teacher_count,
            }
            for branch in rows
        ]
