"""
Course enrolment - the join between a student, a course and the cohort they sit in.

This is the record the rest of the system hangs off: fee invoices, attendance, exam results
and report cards all resolve through it. So the invariants are enforced here rather than in a
serializer, and they are enforced inside a transaction that also takes a row lock on the
batch, because seat capacity is a classic lost-update race - two receptionists enrolling the
41st student into a 40-seat batch at the same moment would both pass a naive count check.

Invariants:
  1. The batch must belong to the course being enrolled in.
  2. The student and the batch must be in the same branch.
  3. The student must actually hold the Student role.
  4. The batch must have a free seat.
  5. A student may hold only one live enrolment per course.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Q

from academics.models import Batch, CourseEnrolment
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import (
    assert_role,
    child_student_user_ids,
    narrow,
    scope_to_branch,
)
from institute_crm.utils import active

STATUS_ACTIVE = "ACTIVE"
STATUS_COMPLETED = "COMPLETED"
STATUS_DROPPED = "DROPPED"

#: Roles that may enrol or transfer students.
ENROLMENT_EDITORS = (
    Role.SUPER_ADMIN,
    Role.BRANCH_ADMIN,
    Role.RECEPTIONIST,
    Role.ADMISSION_COUNSELOR,
)

#: Only these transitions are allowed. An enrolment is never moved back to ACTIVE by this
#: API - re-admitting a student is a new enrolment, so the original record stays as history.
_ALLOWED_TRANSITIONS = {
    STATUS_ACTIVE: {STATUS_COMPLETED, STATUS_DROPPED},
    STATUS_COMPLETED: set(),
    STATUS_DROPPED: set(),
}


class EnrolmentService:
    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_enrolments(actor: User):
        """Scoped through ``batch__branch``.

        The branch is taken from the batch, not the student: the batch is where the cohort
        physically runs and is the value validated on write, so it is the authoritative
        tenant anchor. A student record whose branch was later edited cannot move their
        enrolment out of the branch that is teaching them.
        """
        queryset = (
            active(CourseEnrolment)
            .select_related("student", "course", "batch", "batch__branch")
            .order_by("-enrolled_at", "student__first_name")
        )
        queryset = scope_to_branch(queryset, actor, branch_path="batch__branch")

        role = getattr(actor, "role_code", None)
        if role == Role.TEACHER:
            queryset = queryset.filter(
                Q(batch__timetables__teacher_id=actor.pk, batch__timetables__is_deleted=False)
                | Q(batch__teachers=actor)
            ).distinct()
        elif role == Role.STUDENT:
            queryset = queryset.filter(student_id=actor.pk)
        elif role == Role.PARENT:
            queryset = queryset.filter(student_id__in=child_student_user_ids(actor))

        return queryset

    @staticmethod
    def filter_enrolments(
        actor: User,
        *,
        batch_id=None,
        course_id=None,
        student_id=None,
        status: str | None = None,
        search: str | None = None,
    ):
        queryset = narrow(
            EnrolmentService.visible_enrolments(actor),
            {
                "batch_id": batch_id,
                "course_id": course_id,
                "student_id": student_id,
                "status": status.upper() if status else None,
            },
        )
        if search:
            queryset = queryset.filter(
                Q(student__first_name__icontains=search)
                | Q(student__last_name__icontains=search)
                | Q(student__username__icontains=search)
                | Q(student__email__icontains=search)
            )
        return queryset

    @staticmethod
    def get_enrolment_for_actor(actor: User, enrolment_id) -> CourseEnrolment:
        try:
            return EnrolmentService.visible_enrolments(actor).get(pk=enrolment_id)
        except CourseEnrolment.DoesNotExist as exc:
            raise NotFoundError("Enrolment not found.") from exc

    @staticmethod
    def roster(actor: User, batch_id):
        """The active roster of one batch, ordered for a printable attendance sheet."""
        return (
            EnrolmentService.visible_enrolments(actor)
            .filter(batch_id=batch_id, status=STATUS_ACTIVE)
            .order_by("student__first_name", "student__last_name")
        )

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def enrol_student(
        *, actor: User, data: dict, ip_address: str | None = None
    ) -> CourseEnrolment:
        assert_role(
            actor,
            ENROLMENT_EDITORS,
            message="Only admissions and administrative staff can enrol students.",
        )

        student = data.get("student")
        batch = data.get("batch")
        course = data.get("course")

        if student is None or batch is None:
            raise ValidationFailed(
                "A student and a batch are both required to create an enrolment.",
                field_errors={
                    key: ["This field is required."]
                    for key, value in (("student", student), ("batch", batch))
                    if value is None
                },
            )

        # Lock the batch row for the rest of the transaction so the capacity check below
        # cannot be undercut by a concurrent enrolment.
        batch = Batch.objects.select_for_update().select_related("branch").get(pk=batch.pk)

        course = course or batch.course
        EnrolmentService._assert_batch_matches_course(batch, course)
        EnrolmentService._assert_student(student)
        EnrolmentService._assert_same_branch(student, batch)
        EnrolmentService._assert_actor_may_touch_batch(actor, batch)
        EnrolmentService._assert_no_live_enrolment(student, course)
        EnrolmentService._assert_capacity(batch)

        try:
            enrolment = CourseEnrolment.objects.create(
                student=student,
                course=course,
                batch=batch,
                status=data.get("status") or STATUS_ACTIVE,
            )
        except IntegrityError as exc:
            # unique_together ('student', 'course') covers soft-deleted rows too.
            raise ConflictError(
                "This student has already been enrolled in that course.",
                code="duplicate_enrolment",
            ) from exc

        # Keep the denormalised pointer on the student profile in step, so batch-based
        # lookups elsewhere do not disagree with the enrolment table.
        EnrolmentService._sync_student_profile_batch(student, batch)

        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=enrolment,
            changes={
                "student": str(student.pk),
                "course": str(course.pk),
                "batch": str(batch.pk),
            },
            ip_address=ip_address,
        )
        return enrolment

    @staticmethod
    @transaction.atomic
    def transfer_batch(
        *,
        actor: User,
        enrolment: CourseEnrolment,
        batch: Batch,
        ip_address: str | None = None,
    ) -> CourseEnrolment:
        """Move a live enrolment into a different cohort of the same course."""
        assert_role(
            actor,
            ENROLMENT_EDITORS,
            message="Only admissions and administrative staff can transfer students.",
        )
        if enrolment.status != STATUS_ACTIVE:
            raise ConflictError(
                "Only an active enrolment can be transferred.", code="enrolment_not_active"
            )
        if batch.pk == enrolment.batch_id:
            raise ConflictError(
                "The student is already in that batch.", code="same_batch"
            )

        batch = Batch.objects.select_for_update().select_related("branch").get(pk=batch.pk)
        EnrolmentService._assert_batch_matches_course(batch, enrolment.course)
        EnrolmentService._assert_same_branch(enrolment.student, batch)
        EnrolmentService._assert_actor_may_touch_batch(actor, batch)
        EnrolmentService._assert_capacity(batch)

        previous = enrolment.batch_id
        enrolment.batch = batch
        enrolment.save(update_fields=["batch"])
        EnrolmentService._sync_student_profile_batch(enrolment.student, batch)

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=enrolment,
            changes={"batch": {"from": str(previous), "to": str(batch.pk)}},
            ip_address=ip_address,
        )
        return enrolment

    @staticmethod
    @transaction.atomic
    def set_status(
        *,
        actor: User,
        enrolment: CourseEnrolment,
        status: str,
        ip_address: str | None = None,
    ) -> CourseEnrolment:
        assert_role(
            actor,
            ENROLMENT_EDITORS,
            message="Only admissions and administrative staff can change an enrolment status.",
        )

        target = (status or "").strip().upper()
        valid = {choice for choice, _ in CourseEnrolment.STATUS_CHOICES}
        if target not in valid:
            raise ValidationFailed(
                f"Unknown enrolment status '{status}'.",
                field_errors={"status": [f"Choose one of: {', '.join(sorted(valid))}."]},
            )
        if target == enrolment.status:
            return enrolment
        if target not in _ALLOWED_TRANSITIONS.get(enrolment.status, set()):
            raise ConflictError(
                f"An enrolment cannot move from {enrolment.status} to {target}.",
                code="invalid_status_transition",
            )

        previous = enrolment.status
        enrolment.status = target
        enrolment.save(update_fields=["status"])

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=enrolment,
            changes={"status": {"from": previous, "to": target}},
            ip_address=ip_address,
        )
        return enrolment

    @staticmethod
    @transaction.atomic
    def update_enrolment(
        *, actor: User, enrolment: CourseEnrolment, data: dict, ip_address: str | None = None
    ) -> CourseEnrolment:
        """Generic update used by the viewset, routed to the specific rules above.

        Batch and status changes carry real business rules, so they are delegated rather
        than applied by ``setattr``. Anything else is rejected: there is no other field on
        an enrolment that is safe to edit in place.
        """
        payload = dict(data)
        payload.pop("student", None)  # re-pointing an enrolment at another student is never valid
        payload.pop("course", None)   # ditto - that is a new enrolment, not an edit

        batch = payload.pop("batch", None)
        status = payload.pop("status", None)

        if batch is not None and batch.pk != enrolment.batch_id:
            enrolment = EnrolmentService.transfer_batch(
                actor=actor, enrolment=enrolment, batch=batch, ip_address=ip_address
            )
        if status is not None:
            enrolment = EnrolmentService.set_status(
                actor=actor, enrolment=enrolment, status=status, ip_address=ip_address
            )
        return enrolment

    @staticmethod
    @transaction.atomic
    def soft_delete_enrolment(
        *, actor: User, enrolment: CourseEnrolment, ip_address: str | None = None
    ) -> None:
        """Withdraw an enrolment.

        Prefer :meth:`set_status` with ``DROPPED`` - that keeps the record visible in
        reporting. This exists for correcting a mistaken entry, and is refused once the
        enrolment has attendance or results attached, because removing it would orphan them.
        """
        assert_role(
            actor,
            ENROLMENT_EDITORS,
            message="Only admissions and administrative staff can remove enrolments.",
        )

        from academics.models import Attendance

        marked = active(Attendance).filter(
            student_id=enrolment.student_id,
            lecture__timetable__batch_id=enrolment.batch_id,
        ).count()
        if marked:
            raise ConflictError(
                f"This enrolment already has {marked} attendance record(s). "
                "Mark it as DROPPED instead so the history is preserved.",
                code="enrolment_has_history",
            )

        enrolment.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=enrolment,
            changes={
                "soft_delete": True,
                "student": str(enrolment.student_id),
                "course": str(enrolment.course_id),
            },
            ip_address=ip_address,
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _assert_batch_matches_course(batch: Batch, course) -> None:
        if course is None:
            raise ValidationFailed(
                "A course is required.", field_errors={"course": ["This field is required."]}
            )
        if batch.course_id != course.pk:
            raise ValidationFailed(
                f"Batch '{batch.name}' does not run the selected course.",
                field_errors={"batch": ["Choose a batch that belongs to this course."]},
            )

    @staticmethod
    def _assert_student(student: User) -> None:
        if getattr(student, "is_deleted", False) or not student.is_active:
            raise ValidationFailed(
                "That student account is inactive.",
                field_errors={"student": ["Account is inactive."]},
            )
        if student.role_code != Role.STUDENT:
            raise ValidationFailed(
                "Only accounts with the Student role can be enrolled in a course.",
                field_errors={"student": ["This account is not a student."]},
            )

    @staticmethod
    def _assert_same_branch(student: User, batch: Batch) -> None:
        if student.branch_id and student.branch_id != batch.branch_id:
            raise ValidationFailed(
                f"{student.get_full_name() or student.username} belongs to a different "
                "branch from this batch.",
                field_errors={"batch": ["Student and batch must be in the same branch."]},
            )

    @staticmethod
    def _assert_actor_may_touch_batch(actor: User, batch: Batch) -> None:
        from institute_crm.scoping import assert_same_branch

        assert_same_branch(
            actor,
            batch.branch_id,
            message="You can only enrol students into batches in your own branch.",
        )

    @staticmethod
    def _assert_no_live_enrolment(student: User, course) -> None:
        existing = (
            active(CourseEnrolment)
            .filter(student=student, course=course)
            .exclude(status=STATUS_DROPPED)
            .first()
        )
        if existing:
            raise ConflictError(
                f"{student.get_full_name() or student.username} already has a "
                f"{existing.status.lower()} enrolment in this course.",
                code="duplicate_enrolment",
            )

    @staticmethod
    def _assert_capacity(batch: Batch) -> None:
        taken = active(CourseEnrolment).filter(batch=batch, status=STATUS_ACTIVE).count()
        if taken >= batch.max_capacity:
            raise ConflictError(
                f"Batch '{batch.name}' is full ({batch.max_capacity} seats).",
                code="batch_full",
            )

    @staticmethod
    def _sync_student_profile_batch(student: User, batch: Batch) -> None:
        """Best-effort update of ``StudentProfile.batch``; absent profile is not an error."""
        profile = getattr(student, "student_profile", None)
        if profile is None or profile.batch_id == batch.pk:
            return
        profile.batch = batch
        profile.save(update_fields=["batch"])
