"""
Batch (cohort) management.

A batch is the unit that actually runs: it pins a course to a branch, a date range and a
seat limit. Because it owns a ``branch`` FK it is tenant data, so every read here goes
through :func:`scope_to_branch` and every write through :func:`resolve_write_branch`.

Two rules deserve calling out because the previous view-level implementation got them wrong:

* Filter parameters are applied *after* scoping and can only narrow. Previously a teacher
  who passed ``?branch_id=<other branch>`` skipped the teacher scope entirely.
* A caller with no branch assigned sees nothing, not everything.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q

from academics.models import Batch, CourseEnrolment, Timetable
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import (
    assert_role,
    child_student_user_ids,
    is_global,
    narrow,
    resolve_write_branch,
    scope_to_branch,
)
from institute_crm.utils import active

#: Roles that may create or reshape cohorts.
BATCH_EDITORS = Role.ADMIN_ROLES

#: Roles whose view of batches is limited to their own branch (everyone except super admin).
_TEACHER = Role.TEACHER
_STUDENT = Role.STUDENT
_PARENT = Role.PARENT


class BatchService:
    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_batches(actor: User):
        """Batches ``actor`` may see, scoped unconditionally.

        Staff see their branch. Teachers see only the batches they are timetabled on.
        Students and parents see only batches the student is enrolled in.
        """
        queryset = (
            active(Batch)
            .select_related("course", "branch")
            .order_by("-start_date", "name")
        )
        queryset = scope_to_branch(queryset, actor, branch_path="branch")

        role = getattr(actor, "role_code", None)
        if role == _TEACHER:
            # Join through live timetable rows only; a soft-deleted slot must not keep
            # granting a teacher access to the cohort.
            queryset = queryset.filter(
                timetables__teacher_id=actor.pk, timetables__is_deleted=False
            ).distinct()
        elif role == _STUDENT:
            queryset = queryset.filter(
                enrolments__student_id=actor.pk, enrolments__is_deleted=False
            ).distinct()
        elif role == _PARENT:
            child_ids = child_student_user_ids(actor)
            queryset = queryset.filter(
                enrolments__student_id__in=child_ids, enrolments__is_deleted=False
            ).distinct()

        return queryset

    @staticmethod
    def filter_batches(
        actor: User,
        *,
        course_id=None,
        branch_id=None,
        status: str | None = None,
        search: str | None = None,
    ):
        queryset = narrow(
            BatchService.visible_batches(actor),
            {"course_id": course_id, "branch_id": branch_id},
        )
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )
        if status:
            queryset = BatchService._filter_by_lifecycle(queryset, status)
        return queryset

    @staticmethod
    def _filter_by_lifecycle(queryset, status: str):
        """``upcoming`` / ``running`` / ``finished``, derived from the date range."""
        from django.utils import timezone

        today = timezone.localdate()
        key = status.strip().lower()
        if key == "upcoming":
            return queryset.filter(start_date__gt=today)
        if key == "running":
            return queryset.filter(start_date__lte=today, end_date__gte=today)
        if key == "finished":
            return queryset.filter(end_date__lt=today)
        raise ValidationFailed(
            "Unknown batch status filter. Use upcoming, running or finished.",
            field_errors={"status": ["Use upcoming, running or finished."]},
        )

    @staticmethod
    def get_batch_for_actor(actor: User, batch_id) -> Batch:
        try:
            return BatchService.visible_batches(actor).get(pk=batch_id)
        except Batch.DoesNotExist as exc:
            raise NotFoundError("Batch not found.") from exc

    # -------------------------------------------------------------- capacity

    @staticmethod
    def seats_taken(batch: Batch) -> int:
        return active(CourseEnrolment).filter(batch=batch, status="ACTIVE").count()

    @staticmethod
    def seats_available(batch: Batch) -> int:
        return max(batch.max_capacity - BatchService.seats_taken(batch), 0)

    @staticmethod
    def assert_has_capacity(batch: Batch) -> None:
        if BatchService.seats_available(batch) <= 0:
            raise ConflictError(
                f"Batch '{batch.name}' is full ({batch.max_capacity} seats).",
                code="batch_full",
            )

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def create_batch(*, actor: User, data: dict, ip_address: str | None = None) -> Batch:
        assert_role(actor, BATCH_EDITORS, message="Only administrators can create batches.")

        payload = dict(data)
        # A non-global caller's branch is imposed, not accepted from the request body.
        payload["branch"] = resolve_write_branch(actor, payload.get("branch"))

        code = BatchService._normalise_code(payload.get("code"))
        BatchService._assert_code_available(code)
        payload["code"] = code

        BatchService._validate_dates(payload.get("start_date"), payload.get("end_date"))
        BatchService._validate_capacity(payload.get("max_capacity"))

        batch = Batch.objects.create(**payload)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=batch,
            changes={
                "code": batch.code,
                "name": batch.name,
                "branch": str(batch.branch_id),
                "course": str(batch.course_id),
            },
            ip_address=ip_address,
        )
        return batch

    @staticmethod
    @transaction.atomic
    def update_batch(
        *, actor: User, batch: Batch, data: dict, ip_address: str | None = None
    ) -> Batch:
        assert_role(actor, BATCH_EDITORS, message="Only administrators can edit batches.")

        payload = dict(data)

        # Moving a cohort between branches would orphan its timetable, enrolments and
        # invoices, so only a super admin may do it - and only explicitly.
        if "branch" in payload and payload["branch"] and payload["branch"].pk != batch.branch_id:
            if not is_global(actor):
                raise ConflictError(
                    "A batch cannot be moved to another branch.",
                    code="batch_branch_locked",
                )
        else:
            payload.pop("branch", None)

        if "code" in payload:
            code = BatchService._normalise_code(payload["code"])
            if code != batch.code:
                BatchService._assert_code_available(code, exclude_pk=batch.pk)
            payload["code"] = code

        start = payload.get("start_date", batch.start_date)
        end = payload.get("end_date", batch.end_date)
        BatchService._validate_dates(start, end)

        if "max_capacity" in payload:
            BatchService._validate_capacity(payload["max_capacity"])
            taken = BatchService.seats_taken(batch)
            if payload["max_capacity"] < taken:
                raise ConflictError(
                    f"{taken} student(s) are already enrolled, so capacity cannot be "
                    f"reduced to {payload['max_capacity']}.",
                    code="capacity_below_enrolled",
                )

        if "course" in payload and payload["course"] and payload["course"].pk != batch.course_id:
            if active(CourseEnrolment).filter(batch=batch).exists():
                raise ConflictError(
                    "This batch already has enrolments, so its course cannot be changed.",
                    code="batch_course_locked",
                )

        changes = audit.diff_fields(batch, payload)
        for field, value in payload.items():
            setattr(batch, field, value)
        batch.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=batch,
            changes=changes,
            ip_address=ip_address,
        )
        return batch

    @staticmethod
    @transaction.atomic
    def soft_delete_batch(
        *, actor: User, batch: Batch, ip_address: str | None = None
    ) -> None:
        """Retire a batch and its timetable. Refused while students are actively enrolled."""
        assert_role(actor, BATCH_EDITORS, message="Only administrators can remove batches.")

        enrolled = active(CourseEnrolment).filter(batch=batch, status="ACTIVE").count()
        if enrolled:
            raise ConflictError(
                f"{enrolled} student(s) are still actively enrolled in this batch. "
                "Complete or drop those enrolments first.",
                code="batch_not_empty",
            )

        # Cascade the soft delete to the schedule, otherwise orphaned slots keep appearing
        # on teacher timetables for a cohort that no longer exists.
        slots = list(active(Timetable).filter(batch=batch))
        for slot in slots:
            slot.soft_delete()

        batch.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=batch,
            changes={
                "soft_delete": True,
                "code": batch.code,
                "timetable_slots_removed": len(slots),
            },
            ip_address=ip_address,
        )

    # ------------------------------------------------------------- statistics

    @staticmethod
    def batch_summary(actor: User, **filters):
        """Roster and schedule counts per batch, in one aggregate query."""
        return list(
            BatchService.filter_batches(actor, **filters)
            .annotate(
                enrolled_count=Count(
                    "enrolments",
                    filter=Q(enrolments__is_deleted=False, enrolments__status="ACTIVE"),
                    distinct=True,
                ),
                session_count=Count(
                    "timetables", filter=Q(timetables__is_deleted=False), distinct=True
                ),
            )
            .values(
                "id",
                "code",
                "name",
                "start_date",
                "end_date",
                "max_capacity",
                "course__title",
                "branch__name",
                "enrolled_count",
                "session_count",
            )
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _normalise_code(code) -> str:
        if not code or not str(code).strip():
            raise ValidationFailed(
                "Batch code is required.", field_errors={"code": ["This field is required."]}
            )
        return str(code).strip().upper().replace(" ", "_")

    @staticmethod
    def _assert_code_available(code: str, *, exclude_pk=None) -> None:
        # `code` is unique at the database level *including* soft-deleted rows, so a retired
        # batch still holds its code. Say so explicitly instead of surfacing an IntegrityError.
        queryset = Batch.objects.filter(code=code)
        if exclude_pk:
            queryset = queryset.exclude(pk=exclude_pk)
        existing = queryset.first()
        if existing is None:
            return
        if existing.is_deleted:
            raise ConflictError(
                f"Batch code '{code}' belonged to a retired batch and cannot be reused.",
                code="batch_code_retired",
            )
        raise ConflictError(
            f"Batch code '{code}' is already in use.", code="batch_code_taken"
        )

    @staticmethod
    def _validate_dates(start_date, end_date) -> None:
        if start_date and end_date and end_date < start_date:
            raise ValidationFailed(
                "The batch end date cannot be before its start date.",
                field_errors={"end_date": ["Must be on or after the start date."]},
            )

    @staticmethod
    def _validate_capacity(max_capacity) -> None:
        if max_capacity is None:
            return
        if max_capacity < 1:
            raise ValidationFailed(
                "A batch needs at least one seat.",
                field_errors={"max_capacity": ["Enter 1 or more."]},
            )
