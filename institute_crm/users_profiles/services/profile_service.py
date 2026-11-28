"""
Service layer for users_profiles.
Encapsulates business logic for Student, Teacher, and Parent profiles.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.db.models import Q, QuerySet

from accounts.models import Role, User
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile, StudentParent

logger = logging.getLogger('institute_crm.profiles')


class ProfileService:
    @staticmethod
    def filter_students(
        actor: User,
        *,
        batch_id: str | None = None,
        course_id: str | None = None,
        branch_id: str | None = None,
        branch_ids: list | tuple | str | None = None,
        search: str | None = None,
    ) -> QuerySet[StudentProfile]:
        qs = StudentProfile.objects.filter(is_deleted=False).order_by('reg_no').select_related(
            'user', 'user__branch', 'batch', 'batch__course', 'batch__branch'
        ).prefetch_related('user__enrolments__course')

        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if course_id:
            qs = qs.filter(
                Q(course_id=course_id)
                | Q(batch__course_id=course_id)
                | Q(user__enrolments__course_id=course_id)
            ).distinct()

        # Optional branch narrowing. Applied *before* role scoping and only ever
        # narrows: a branch-scoped actor cannot widen their reach by passing a
        # filter value, and a non-global actor can never select another branch.
        requested_branches = ProfileService._normalise_branch_ids(branch_id, branch_ids)
        if requested_branches:
            qs = qs.filter(user__branch_id__in=requested_branches)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__username__icontains=search)
                | Q(user__email__icontains=search)
                | Q(reg_no__icontains=search)
            )

        # Scoping based on actor role. Branch-scoped staff fail closed when they have
        # no branch assigned rather than silently seeing every campus. Global
        # (super admin / superuser) callers are unscoped; optional filters above
        # still apply and can only narrow.
        from institute_crm.scoping import is_global

        if not (actor and actor.is_authenticated):
            return qs.none()

        if is_global(actor):
            return qs.distinct()

        role_code = actor.role.code if actor.role else None
        branch_roles = [
            Role.BRANCH_ADMIN, Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR,
            Role.ACCOUNTANT,
        ]
        if role_code in branch_roles:
            qs = qs.filter(user__branch_id=actor.branch_id) if actor.branch_id else qs.none()
        elif role_code == Role.TEACHER:
            qs = ProfileService._scope_students_for_teacher(qs, actor)
        elif role_code == Role.STUDENT:
            qs = qs.filter(user=actor)
        elif role_code == Role.PARENT:
            qs = qs.filter(parent_links__parent__user=actor)
        else:
            qs = qs.none()

        return qs.distinct()

    @staticmethod
    def _normalise_branch_ids(branch_id, branch_ids) -> list[str]:
        """Accept ``branch_id`` (single) and ``branch_ids`` (list or comma string)."""
        values: list[str] = []
        for raw in (branch_id, branch_ids):
            if raw in (None, '', [], ()):  # noqa: PLC1901 - explicit empty check
                continue
            if isinstance(raw, str):
                values.extend(part.strip() for part in raw.split(','))
            elif isinstance(raw, (list, tuple, set)):
                values.extend(str(part).strip() for part in raw)
            else:
                values.append(str(raw).strip())
        return [v for v in values if v]

    @staticmethod
    def _scope_students_for_teacher(qs: QuerySet[StudentProfile], actor: User) -> QuerySet[StudentProfile]:
        """Teachers see only students in their own branch, in their assigned courses/batches.

        Unconditional: applied *after* (and AND-combined with) any caller-supplied
        filters, so a query parameter can never widen a teacher's scope. A teacher
        with no branch fails closed. Existing assignments (Batch.teachers, timetable
        slots) and explicit teacher-course assignments are all honoured; a teacher
        with no assignments at all sees nothing.
        """
        if not actor.branch_id:
            return qs.none()

        # Lazy import: academics imports users_profiles.
        from academics.models import Batch, Timetable

        assigned_batch_ids = set(
            Batch.objects.filter(is_deleted=False, teachers=actor).values_list('pk', flat=True)
        )
        assigned_batch_ids |= set(
            Timetable.objects.filter(is_deleted=False, teacher=actor).values_list('batch_id', flat=True)
        )
        assigned_course_ids: set = set()
        try:
            from academics.models import Batch as _B
            assigned_course_ids = set(
                _B.objects.filter(is_deleted=False, pk__in=assigned_batch_ids)
                .values_list('course_id', flat=True)
            )
        except Exception:
            assigned_course_ids = set()

        try:
            from academics.services.teacher_assignment_service import TeacherAssignmentService
            assigned = TeacherAssignmentService.assigned_scope(actor)
            assigned_batch_ids |= assigned['batch_ids']
            assigned_course_ids |= assigned['course_ids']
        except Exception:
            pass

        assignment_filter = (
            Q(batch__timetables__teacher=actor, batch__timetables__is_deleted=False)
            | Q(batch__teachers=actor)
        )
        if assigned_batch_ids:
            assignment_filter |= Q(batch_id__in=list(assigned_batch_ids))
        if assigned_course_ids:
            assignment_filter |= (
                Q(batch__course_id__in=list(assigned_course_ids))
                | Q(course_id__in=list(assigned_course_ids))
            )

        return qs.filter(Q(user__branch_id=actor.branch_id)).filter(assignment_filter).distinct()

    @staticmethod
    def filter_teachers(
        actor: User,
        *,
        branch_id: str | None = None,
        branch_ids: list | tuple | str | None = None,
        search: str | None = None,
    ) -> QuerySet[TeacherProfile]:
        qs = TeacherProfile.objects.filter(is_deleted=False).select_related('user', 'user__branch')

        # Optional branch narrowing; only ever narrows, applied before scoping.
        requested_branches = ProfileService._normalise_branch_ids(branch_id, branch_ids)
        if requested_branches:
            qs = qs.filter(user__branch_id__in=requested_branches)

        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(employee_id__icontains=search)
                | Q(qualification__icontains=search)
                | Q(specialization__icontains=search)
            )

        # Branch scoping first, then optional narrowing; non-global callers can
        # never widen their scope with a filter value.
        from institute_crm.scoping import is_global

        if not (actor and actor.is_authenticated):
            return qs.none()

        if is_global(actor):
            return qs

        role_code = actor.role.code if actor.role else None
        if role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR]:
            qs = qs.filter(user__branch_id=actor.branch_id) if actor.branch_id else qs.none()
        elif role_code == Role.TEACHER:
            qs = qs.filter(user=actor)
        else:
            qs = qs.none()

        return qs

    @staticmethod
    def filter_parents(
        actor: User,
        *,
        search: str | None = None,
    ) -> QuerySet[ParentProfile]:
        qs = ParentProfile.objects.filter(is_deleted=False).select_related('user')
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(occupation__icontains=search)
            )
        return qs

    @staticmethod
    @transaction.atomic
    def update_student_profile(
        actor: User,
        profile: StudentProfile,
        data: dict[str, Any],
    ) -> StudentProfile:
        allowed_fields = {
            'dob', 'gender', 'blood_group', 'address', 'emergency_contact',
            'secondary_phone', 'course', 'batch',
            'guardian_name', 'guardian_phone', 'guardian_relationship',
            'agreed_fee', 'discount_amount', 'concession_amount', 'scholarship_amount',
            'fee_notes',
        }
        for field, value in data.items():
            if field in allowed_fields:
                setattr(profile, field, value)
        profile.save()
        return profile

    # ------------------------------------------------- cancellation & removal

    #: Roles allowed to cancel an admission / remove a cancelled-admission student.
    STUDENT_CANCELLERS = (Role.RECEPTIONIST, Role.BRANCH_ADMIN, Role.SUPER_ADMIN)

    @staticmethod
    def cancellation_blocked_reason(profile: StudentProfile) -> str | None:
        """Why this record cannot have its admission cancelled, or ``None``."""
        if profile.is_deleted:
            return 'This student record has already been removed.'
        if profile.admission_status == StudentProfile.ADMISSION_CANCELLED:
            return None  # already cancelled - cancellation is idempotent
        if profile.has_live_enrolment:
            return 'This student has an active course enrolment; drop it before cancelling admission.'
        if profile.is_enrolled:
            return 'This student is enrolled; remove the enrolment before cancelling admission.'
        batch = profile.batch
        if batch is not None and not getattr(batch, 'is_deleted', False):
            return 'This student is assigned to a live batch; remove the batch assignment before cancelling admission.'
        return None

    @staticmethod
    def deletion_blocked_reason(profile: StudentProfile) -> str | None:
        """Why a cancelled-admission record cannot be removed from active views."""
        if profile.is_deleted:
            return 'This student record has already been removed.'
        if profile.admission_status != StudentProfile.ADMISSION_CANCELLED:
            return 'Only students whose admission is cancelled can be removed.'
        if profile.has_live_enrolment:
            return 'This student has an active course enrolment and cannot be removed.'
        batch = profile.batch
        if batch is not None and not getattr(batch, 'is_deleted', False):
            return 'This student is assigned to a live batch and cannot be removed.'
        if profile.is_enrolled:
            return 'This student is enrolled and cannot be removed.'
        return None

    @staticmethod
    def assert_student_admin(actor: User) -> None:
        ProfileService._assert_student_admin(actor)

    @staticmethod
    def _assert_student_admin(actor: User) -> None:
        from institute_crm.exceptions import PermissionDeniedError
        from institute_crm.scoping import assert_role

        if not (actor and actor.is_authenticated):
            raise PermissionDeniedError('Authentication is required.', code='not_authenticated')
        assert_role(
            actor,
            ProfileService.STUDENT_CANCELLERS,
            message='Only the reception desk or an administrator can cancel or remove student admissions.',
        )

    @staticmethod
    def _assert_profile_in_scope(actor: User, profile: StudentProfile) -> None:
        from institute_crm.exceptions import NotFoundError
        from institute_crm.scoping import assert_same_branch, is_global

        if is_global(actor):
            return
        branch_id = profile.user.branch_id or (profile.batch.branch_id if profile.batch_id else None)
        try:
            assert_same_branch(actor, branch_id, message='That student belongs to another branch.')
        except Exception as exc:
            raise NotFoundError('Student not found.') from exc

    @staticmethod
    @transaction.atomic
    def cancel_admission(
        *, actor: User, profile: StudentProfile, reason: str | None = None,
    ) -> StudentProfile:
        """Mark a student's admission cancelled. Soft, audited, idempotent."""
        from django.utils import timezone

        from institute_crm import audit
        from institute_crm.exceptions import ConflictError

        ProfileService._assert_student_admin(actor)
        ProfileService._assert_profile_in_scope(actor, profile)

        if profile.is_deleted:
            from institute_crm.exceptions import NotFoundError
            raise NotFoundError('Student not found.')

        if profile.admission_status == StudentProfile.ADMISSION_CANCELLED:
            # Idempotent: re-record reason if supplied.
            if reason:
                profile.cancellation_reason = reason.strip()
                profile.save(update_fields=['cancellation_reason'])
            return profile

        blocked = ProfileService.cancellation_blocked_reason(profile)
        if blocked:
            raise ConflictError(blocked, code='admission_cancel_blocked')

        profile.admission_status = StudentProfile.ADMISSION_CANCELLED
        profile.cancellation_reason = (reason or '').strip() or None
        profile.cancelled_at = timezone.now()
        # A cancelled admission is no longer attached to a live batch.
        profile.batch = None
        profile.save(update_fields=['admission_status', 'cancellation_reason', 'cancelled_at', 'batch'])

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=profile,
            model_name='StudentProfile',
            changes={
                'admission_status': {'from': StudentProfile.ADMISSION_PENDING, 'to': StudentProfile.ADMISSION_CANCELLED},
                'reason': profile.cancellation_reason,
                'student': profile.user.username,
                'reg_no': profile.reg_no,
            },
        )
        return profile

    @staticmethod
    @transaction.atomic
    def delete_cancelled_student(
        *, actor: User, profile: StudentProfile,
        reason: str | None = None, confirm: bool = False,
    ) -> StudentProfile:
        """Remove a cancelled-admission student from active views (soft delete).

        The row, its history, enrolments and audit trail are retained; nothing is
        hard-deleted. Server-side: role + branch scope + eligibility + explicit
        confirmation are all re-validated here, not just in the UI.
        """
        from institute_crm import audit
        from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed


        ProfileService._assert_student_admin(actor)
        ProfileService._assert_profile_in_scope(actor, profile)

        if profile.is_deleted:
            raise NotFoundError('Student not found.')

        if not confirm:
            raise ValidationFailed(
                'Deletion must be confirmed.',
                field_errors={'confirm': ['Confirm removal before deleting.']},
                code='confirmation_required',
            )

        blocked = ProfileService.deletion_blocked_reason(profile)
        if blocked:
            raise ConflictError(blocked, code='student_not_deletable')

        clean_reason = (reason or '').strip() or None
        profile.deletion_reason = clean_reason
        profile.deleted_by_id = actor.pk
        profile.soft_delete()
        profile.save(update_fields=['deletion_reason', 'deleted_by'])

        # Hide the account from active views but keep it for audit/history.
        user = profile.user
        user.is_deleted = True
        user.is_active = False
        user.save(update_fields=['is_deleted', 'is_active'])

        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=profile,
            model_name='StudentProfile',
            changes={
                'soft_delete': True,
                'student': user.username,
                'reg_no': profile.reg_no,
                'reason': clean_reason,
                'admission_status': profile.admission_status,
                'cancellation_reason': profile.cancellation_reason,
            },
        )
        return profile

    @staticmethod
    @transaction.atomic
    def link_parent_to_student(
        student_profile: StudentProfile,
        parent_profile: ParentProfile,
        is_primary: bool = True,
    ) -> StudentParent:
        link, created = StudentParent.objects.update_or_create(
            student=student_profile,
            parent=parent_profile,
            defaults={'is_primary': is_primary}
        )
        return link
