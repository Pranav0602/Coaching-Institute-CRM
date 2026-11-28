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

    #: Roles allowed to edit a student profile (server-enforced).
    STUDENT_PROFILE_EDITORS = (
        Role.RECEPTIONIST, Role.ADMISSION_COUNSELOR, Role.BRANCH_ADMIN, Role.SUPER_ADMIN,
    )

    #: All editable StudentProfile fields. System-managed fields (id, reg_no,
    #: user, created_at/updated_at/deleted_at, version, is_deleted, deleted_by,
    #: admission_status, cancellation_*, deletion_*, and read-only computed
    #: values) are deliberately excluded; a client cannot set them.
    EDITABLE_PROFILE_FIELDS = frozenset({
        'dob', 'gender', 'blood_group', 'address', 'emergency_contact',
        'secondary_phone', 'course',
        'academic_branch', 'source_course_label', 'source_softwares',
        'documents_url',
        'guardian_name', 'guardian_phone', 'guardian_relationship',
        'agreed_fee', 'discount_amount', 'concession_amount', 'scholarship_amount',
        'fee_notes',
    })

    @staticmethod
    def assert_student_profile_editor(actor: User) -> None:
        from institute_crm.exceptions import PermissionDeniedError
        from institute_crm.scoping import assert_role

        if not (actor and actor.is_authenticated):
            raise PermissionDeniedError('Authentication is required.', code='not_authenticated')
        assert_role(
            actor, ProfileService.STUDENT_PROFILE_EDITORS,
            message='Only authorized staff can edit student profiles.',
        )

    @staticmethod
    @transaction.atomic
    def update_student_profile(
        actor: User,
        profile: StudentProfile,
        data: dict[str, Any],
    ) -> StudentProfile:
        from institute_crm.exceptions import PermissionDeniedError, ValidationFailed
        from institute_crm.scoping import assert_role, assert_same_branch, is_global

        if not (actor and actor.is_authenticated):
            raise PermissionDeniedError('Authentication is required.', code='not_authenticated')
        # Unauthorized users cannot edit student profiles.
        assert_role(
            actor, ProfileService.STUDENT_PROFILE_EDITORS,
            message='Only authorized staff can edit student profiles.',
        )
        if not is_global(actor):
            assert_same_branch(actor, profile.user.branch_id or (profile.batch.branch_id if profile.batch_id else None))

        payload = {k: v for k, v in data.items() if k in ProfileService.EDITABLE_PROFILE_FIELDS}
        # `batch` is applied separately with server validation (assign_batch).

        # Validation reusing existing domain rules.
        if 'gender' in payload and payload['gender'] not in {c for c, _ in StudentProfile.GENDER_CHOICES}:
            raise ValidationFailed(
                'Invalid gender.', field_errors={'gender': ['Choose MALE, FEMALE or OTHER.']},
            )
        for money_field in ('agreed_fee', 'discount_amount', 'concession_amount', 'scholarship_amount'):
            if money_field in payload and payload[money_field] is not None:
                try:
                    if float(payload[money_field]) < 0:
                        raise ValueError
                except (TypeError, ValueError):
                    raise ValidationFailed(
                        f'{money_field} must be a non-negative number.',
                        field_errors={money_field: ['Enter a value of zero or more.']},
                    )

        # Course must exist; batch assignment is validated separately.
        if 'course' in payload and payload['course'] is not None:
            from academics.models import Course
            course = payload['course']
            if isinstance(course, Course):
                if course.is_deleted:
                    raise ValidationFailed('Course not found.', field_errors={'course': ['Unknown course.']})
            else:
                if not Course.objects.filter(pk=course, is_deleted=False).exists():
                    raise ValidationFailed('Course not found.', field_errors={'course': ['Unknown course.']})

        # Capture `batch` separately so it is validated + synced consistently.
        batch_provided = 'batch' in data
        new_batch = data.get('batch')

        for field, value in payload.items():
            setattr(profile, field, value)
        profile.save()

        if batch_provided:
            ProfileService.assign_batch(
                actor=actor, profile=profile, batch=new_batch, _already_authorized=True,
            )

        return profile

    # --------------------------------------------------- batch assignment

    @staticmethod
    @transaction.atomic
    def assign_batch(
        *, actor: User, profile: StudentProfile, batch, _already_authorized: bool = False,
    ) -> StudentProfile:
        """Assign a valid batch to a student, or clear it when ``batch`` is None.

        Server-enforced. Assigning (non-null) a batch is intended for a student
        who currently has no batch. Validates: caller is authorized staff in
        scope; batch is active; **batch branch matches the student's branch**;
        **batch course matches the student's course** when one is set; the
        student is not already assigned that batch and has no live enrolment in
        that course (no duplicate); batch has free capacity. Syncs
        ``StudentProfile.batch`` and creates a ``CourseEnrolment`` via
        :class:`EnrolmentService`; audited.
        """
        from institute_crm import audit
        from institute_crm.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationFailed
        from institute_crm.scoping import assert_role, assert_same_branch, is_global

        if not (actor and actor.is_authenticated):
            raise PermissionDeniedError('Authentication is required.', code='not_authenticated')
        if not _already_authorized:
            assert_role(
                actor, ProfileService.STUDENT_PROFILE_EDITORS,
                message='Only authorized staff can assign batches.',
            )
        if not is_global(actor):
            assert_same_branch(actor, profile.user.branch_id or (profile.batch.branch_id if profile.batch_id else None))

        if profile.is_deleted:
            raise NotFoundError('Student not found.')

        # Clearing a batch assignment.
        if batch is None or batch == '' or batch == []:
            profile.batch = None
            profile.save(update_fields=['batch'])
            audit.record_audit(
                actor=actor, action=audit.UPDATE, instance=profile, model_name='StudentProfile',
                changes={'batch': None},
            )
            return profile

        from academics.models import Batch, CourseEnrolment
        from academics.services.enrolment_service import EnrolmentService

        batch_obj = batch if isinstance(batch, Batch) else None
        if batch_obj is None:
            batch_obj = Batch.objects.filter(pk=batch, is_deleted=False).select_related('course', 'branch').first()
        if batch_obj is None or getattr(batch_obj, 'is_deleted', False):
            raise ValidationFailed(
                'Batch not found.', field_errors={'batch': ['Unknown or inactive batch.']}, code='batch_not_found',
            )

        # No duplicate: already assigned this batch.
        if profile.batch_id == batch_obj.pk:
            raise ConflictError(
                'This student is already assigned to that batch.',
                field_errors={'batch': ['Already assigned.']}, code='duplicate_assignment',
            )

        # Only a currently-unassigned student can be assigned (for assignment flow).
        # (Re-assignment for full edit is handled by clearing first; here we guard duplicates.)
        if profile.has_live_enrolment:
            existing = CourseEnrolment.objects.filter(
                student_id=profile.user_id, course_id=batch_obj.course_id, is_deleted=False,
            ).exclude(status='DROPPED').first()
            if existing is not None:
                raise ConflictError(
                    'This student is already enrolled in this course.',
                    field_errors={'batch': ['Duplicate enrolment.']}, code='duplicate_enrolment',
                )

        # Branch match.
        student_branch_id = profile.user.branch_id
        if student_branch_id and batch_obj.branch_id != student_branch_id:
            raise ValidationFailed(
                'Batch belongs to a different branch than the student.',
                field_errors={'batch': ['Choose a batch in the student’s branch.']}, code='cross_branch_batch',
            )
        assert_same_branch(actor, batch_obj.branch_id, message='You can only assign batches in your own branch.')

        # Course match (when the student already has a course).
        if profile.course_id and batch_obj.course_id != profile.course_id:
            raise ValidationFailed(
                'Batch runs a different course than the student’s course.',
                field_errors={'batch': ['Choose a batch for the student’s course.']}, code='course_mismatch',
            )

        # Inactive student / cancelled admission can't be assigned.
        if not profile.user.is_active or profile.user.is_deleted:
            raise ValidationFailed(
                'Student account is inactive.', field_errors={'batch': ['Student inactive.']}, code='student_inactive',
            )

        # Capacity + no-live-enrolment + branch invariants enforced by EnrolmentService.
        try:
            EnrolmentService.enrol_student(
                actor=actor,
                data={'student': profile.user, 'course': batch_obj.course, 'batch': batch_obj, 'status': 'ACTIVE'},
            )
        except ConflictError:
            raise
        except Exception as exc:
            raise ValidationFailed(
                str(exc) or 'Could not assign batch.', field_errors={'batch': [str(exc)]}, code='batch_assign_failed',
            ) from exc

        profile.refresh_from_db(fields=['batch', 'admission_status'])
        audit.record_audit(
            actor=actor, action=audit.UPDATE, instance=profile, model_name='StudentProfile',
            changes={'batch': str(batch_obj.pk), 'course': str(batch_obj.course_id)},
        )
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
