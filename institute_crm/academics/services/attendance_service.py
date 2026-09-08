"""
Attendance recording and lecture lifecycle.

Rewritten from the original because the previous version had three defects that all shared
the same root cause - it trusted its input and its queries:

1. It looked up existing rows with ``update_or_create`` **without** excluding soft-deleted
   ones, so re-marking a student whose record had been deleted updated the deleted row in
   place. The write appeared to succeed and was invisible to every read path.
2. It accepted an unvalidated ``records`` payload straight from the request body, so a
   missing or unknown ``student_id`` produced an ``IntegrityError`` (HTTP 500) rather than a
   400, and an arbitrary ``status`` string bypassed the model's choices entirely.
3. It marked the lecture ``COMPLETED`` unconditionally - including for an empty payload, and
   including for a lecture that was already ``CANCELLED``.

It also imported a serializer, which inverted the dependency between the service and the
presentation layer. Services here return model instances; views serialise them.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from academics.models import Attendance, CourseEnrolment, Lecture, Timetable
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import (
    assert_role,
    assert_same_branch,
    child_student_user_ids,
    is_global,
    narrow,
    scope_to_branch,
)
from institute_crm.utils import active

STATUS_PRESENT = "PRESENT"
STATUS_ABSENT = "ABSENT"
_ATTENDANCE_STATUSES = {code for code, _ in Attendance.STATUS_CHOICES}

LECTURE_SCHEDULED = "SCHEDULED"
LECTURE_COMPLETED = "COMPLETED"
LECTURE_CANCELLED = "CANCELLED"
_LECTURE_STATUSES = {LECTURE_SCHEDULED, LECTURE_COMPLETED, LECTURE_CANCELLED}

#: Roles that may record attendance. Teachers are included, but a teacher may only mark
#: lectures on their own timetable - see :meth:`AttendanceService._assert_may_mark`.
ATTENDANCE_MARKERS = (
    Role.SUPER_ADMIN,
    Role.BRANCH_ADMIN,
    Role.TEACHER,
)

#: Below this percentage a student is flagged to their branch admin and parents.
LOW_ATTENDANCE_THRESHOLD = 75.0


class LectureService:
    """Individual class sessions generated from a timetable slot."""

    @staticmethod
    def visible_lectures(actor: User):
        """Scoped through the owning timetable's batch.

        The original viewset had no scoping at all here, which meant the object lookup
        inside the bulk-attendance action could reach any lecture in any branch.
        """
        queryset = (
            active(Lecture)
            .select_related(
                "timetable",
                "timetable__batch",
                "timetable__batch__branch",
                "timetable__subject",
                "timetable__teacher",
            )
            .order_by("-date")
        )
        queryset = scope_to_branch(queryset, actor, branch_path="timetable__batch__branch")

        role = getattr(actor, "role_code", None)
        if role == Role.TEACHER:
            queryset = queryset.filter(timetable__teacher_id=actor.pk)
        elif role == Role.STUDENT:
            queryset = queryset.filter(
                timetable__batch__enrolments__student_id=actor.pk,
                timetable__batch__enrolments__is_deleted=False,
            ).distinct()
        elif role == Role.PARENT:
            queryset = queryset.filter(
                timetable__batch__enrolments__student_id__in=child_student_user_ids(actor),
                timetable__batch__enrolments__is_deleted=False,
            ).distinct()

        return queryset

    @staticmethod
    def filter_lectures(
        actor: User,
        *,
        timetable_id=None,
        batch_id=None,
        status: str | None = None,
        date_from=None,
        date_to=None,
    ):
        queryset = narrow(
            LectureService.visible_lectures(actor),
            {
                "timetable_id": timetable_id,
                "timetable__batch_id": batch_id,
                "status": status.upper() if status else None,
            },
        )
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        return queryset

    @staticmethod
    def get_lecture_for_actor(actor: User, lecture_id) -> Lecture:
        try:
            return LectureService.visible_lectures(actor).get(pk=lecture_id)
        except Lecture.DoesNotExist as exc:
            raise NotFoundError("Lecture not found.") from exc

    @staticmethod
    @transaction.atomic
    def create_lecture(*, actor: User, data: dict, ip_address: str | None = None) -> Lecture:
        assert_role(
            actor,
            ATTENDANCE_MARKERS,
            message="Only teachers and administrators can add lectures.",
        )

        payload = dict(data)
        slot = payload.get("timetable")
        date = payload.get("date")
        if slot is None or date is None:
            raise ValidationFailed(
                "A lecture needs a timetable slot and a date.",
                field_errors={
                    name: ["This field is required."]
                    for name, value in (("timetable", slot), ("date", date))
                    if value is None
                },
            )
        if not (payload.get("topic") or "").strip():
            raise ValidationFailed(
                "Give the lecture a topic so students can identify it.",
                field_errors={"topic": ["This field is required."]},
            )

        LectureService._assert_may_manage_slot(actor, slot)

        if slot.day_of_week != LectureService._day_code(date):
            raise ValidationFailed(
                f"That timetable slot runs on {slot.day_of_week.title()}, but the date "
                f"you chose is a {LectureService._day_code(date).title()}.",
                field_errors={"date": ["Date does not fall on the slot's weekday."]},
            )
        if active(Lecture).filter(timetable=slot, date=date).exists():
            raise ConflictError(
                "A lecture already exists for that slot on that date.",
                code="duplicate_lecture",
            )

        payload["status"] = (payload.get("status") or LECTURE_SCHEDULED).upper()
        LectureService._assert_valid_status(payload["status"])

        lecture = Lecture.objects.create(**payload)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=lecture,
            changes={"timetable": str(slot.pk), "date": str(date), "topic": lecture.topic},
            ip_address=ip_address,
        )
        return lecture

    @staticmethod
    @transaction.atomic
    def update_lecture(
        *, actor: User, lecture: Lecture, data: dict, ip_address: str | None = None
    ) -> Lecture:
        assert_role(
            actor,
            ATTENDANCE_MARKERS,
            message="Only teachers and administrators can edit lectures.",
        )
        LectureService._assert_may_manage_slot(actor, lecture.timetable)

        payload = dict(data)
        payload.pop("timetable", None)  # moving a lecture between slots would orphan its attendance
        if "status" in payload:
            payload["status"] = (payload["status"] or "").upper()
            LectureService._assert_valid_status(payload["status"])
        if "topic" in payload and not (payload["topic"] or "").strip():
            raise ValidationFailed(
                "The lecture topic cannot be blank.",
                field_errors={"topic": ["This field is required."]},
            )

        changes = audit.diff_fields(lecture, payload)
        for field, value in payload.items():
            setattr(lecture, field, value)
        lecture.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=lecture,
            changes=changes,
            ip_address=ip_address,
        )
        return lecture

    @staticmethod
    @transaction.atomic
    def cancel_lecture(
        *,
        actor: User,
        lecture: Lecture,
        reason: str | None = None,
        ip_address: str | None = None,
    ) -> Lecture:
        assert_role(
            actor,
            ATTENDANCE_MARKERS,
            message="Only teachers and administrators can cancel lectures.",
        )
        LectureService._assert_may_manage_slot(actor, lecture.timetable)

        if lecture.status == LECTURE_COMPLETED:
            raise ConflictError(
                "This lecture is already marked complete and cannot be cancelled.",
                code="lecture_already_completed",
            )
        if lecture.status == LECTURE_CANCELLED:
            return lecture

        lecture.status = LECTURE_CANCELLED
        lecture.save(update_fields=["status"])
        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=lecture,
            changes={"status": {"from": LECTURE_SCHEDULED, "to": LECTURE_CANCELLED},
                     "reason": reason or ""},
            ip_address=ip_address,
        )
        return lecture

    @staticmethod
    @transaction.atomic
    def soft_delete_lecture(
        *, actor: User, lecture: Lecture, ip_address: str | None = None
    ) -> None:
        """Remove a lecture created in error. Refused once attendance has been recorded."""
        assert_role(
            actor, Role.ADMIN_ROLES, message="Only administrators can remove lectures."
        )
        LectureService._assert_may_manage_slot(actor, lecture.timetable)

        marked = active(Attendance).filter(lecture=lecture).count()
        if marked:
            raise ConflictError(
                f"Attendance has already been recorded for {marked} student(s). "
                "Cancel the lecture instead so the records are preserved.",
                code="lecture_has_attendance",
            )

        lecture.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=lecture,
            changes={"soft_delete": True, "topic": lecture.topic, "date": str(lecture.date)},
            ip_address=ip_address,
        )

    @staticmethod
    @transaction.atomic
    def generate_from_timetable(
        *,
        actor: User,
        slot: Timetable,
        date_from,
        date_to,
        topic_template: str = "{subject}",
        ip_address: str | None = None,
    ) -> list[Lecture]:
        """Materialise weekly recurring sessions into dated lectures.

        Idempotent: dates that already have a lecture for this slot are skipped, so the
        endpoint can be re-run after extending a batch's end date.
        """
        assert_role(
            actor, Role.ADMIN_ROLES, message="Only administrators can generate lectures."
        )
        LectureService._assert_may_manage_slot(actor, slot)

        if date_to < date_from:
            raise ValidationFailed(
                "The end date cannot be before the start date.",
                field_errors={"date_to": ["Must be on or after the start date."]},
            )
        if (date_to - date_from).days > 366:
            raise ValidationFailed(
                "Generate at most one year of lectures at a time.",
                field_errors={"date_to": ["Range is longer than 366 days."]},
            )

        existing = set(
            active(Lecture)
            .filter(timetable=slot, date__gte=date_from, date__lte=date_to)
            .values_list("date", flat=True)
        )
        topic = topic_template.format(
            subject=slot.subject.title, batch=slot.batch.name, day=slot.day_of_week.title()
        )

        pending = []
        cursor = date_from
        one_day = timedelta(days=1)
        while cursor <= date_to:
            if LectureService._day_code(cursor) == slot.day_of_week and cursor not in existing:
                pending.append(
                    Lecture(timetable=slot, date=cursor, topic=topic, status=LECTURE_SCHEDULED)
                )
            cursor += one_day

        created = Lecture.objects.bulk_create(pending)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            model_name="Lecture",
            target_id=str(slot.pk),
            changes={
                "generated": len(created),
                "timetable": str(slot.pk),
                "from": str(date_from),
                "to": str(date_to),
            },
            ip_address=ip_address,
        )
        return created

    # -------------------------------------------------------------- internals

    @staticmethod
    def _day_code(date) -> str:
        return [
            "MONDAY",
            "TUESDAY",
            "WEDNESDAY",
            "THURSDAY",
            "FRIDAY",
            "SATURDAY",
            "SUNDAY",
        ][date.weekday()]

    @staticmethod
    def _assert_valid_status(status: str) -> None:
        if status not in _LECTURE_STATUSES:
            raise ValidationFailed(
                f"Unknown lecture status '{status}'.",
                field_errors={"status": [f"Choose one of: {', '.join(sorted(_LECTURE_STATUSES))}."]},
            )

    @staticmethod
    def _assert_may_manage_slot(actor: User, slot: Timetable) -> None:
        assert_same_branch(
            actor,
            slot.batch.branch_id,
            message="That lecture belongs to another branch.",
        )
        if actor.role_code == Role.TEACHER and slot.teacher_id != actor.pk:
            from institute_crm.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "You can only manage lectures for sessions you are timetabled to teach.",
                code="not_your_session",
            )


class AttendanceService:
    """Recording and reporting of student attendance."""

    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_attendance(actor: User):
        """Scoped through the lecture's batch, and self-scoped for students and parents."""
        queryset = (
            active(Attendance)
            .select_related(
                "student",
                "lecture",
                "lecture__timetable",
                "lecture__timetable__batch",
                "lecture__timetable__subject",
            )
            .order_by("-lecture__date", "student__first_name")
        )
        queryset = scope_to_branch(
            queryset, actor, branch_path="lecture__timetable__batch__branch"
        )

        role = getattr(actor, "role_code", None)
        if role == Role.TEACHER:
            queryset = queryset.filter(lecture__timetable__teacher_id=actor.pk)
        elif role == Role.STUDENT:
            queryset = queryset.filter(student_id=actor.pk)
        elif role == Role.PARENT:
            queryset = queryset.filter(student_id__in=child_student_user_ids(actor))

        return queryset

    @staticmethod
    def filter_attendance(
        actor: User,
        *,
        lecture_id=None,
        student_id=None,
        batch_id=None,
        status: str | None = None,
        date_from=None,
        date_to=None,
    ):
        queryset = narrow(
            AttendanceService.visible_attendance(actor),
            {
                "lecture_id": lecture_id,
                "student_id": student_id,
                "lecture__timetable__batch_id": batch_id,
                "status": status.upper() if status else None,
            },
        )
        if date_from:
            queryset = queryset.filter(lecture__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(lecture__date__lte=date_to)
        return queryset

    @staticmethod
    def get_attendance_for_actor(actor: User, attendance_id) -> Attendance:
        try:
            return AttendanceService.visible_attendance(actor).get(pk=attendance_id)
        except Attendance.DoesNotExist as exc:
            raise NotFoundError("Attendance record not found.") from exc

    @staticmethod
    def register_for_lecture(actor: User, lecture: Lecture) -> list[dict]:
        """The roster of a lecture with each student's current mark, for the marking screen.

        Returns one entry per *actively enrolled* student, whether or not they have been
        marked yet, so the UI does not have to reconcile two lists.
        """
        AttendanceService._assert_may_mark(actor, lecture)

        enrolments = (
            active(CourseEnrolment)
            .filter(batch_id=lecture.timetable.batch_id, status="ACTIVE")
            .select_related("student")
            .order_by("student__first_name", "student__last_name")
        )
        marks = {
            record.student_id: record
            for record in active(Attendance).filter(lecture=lecture)
        }

        register = []
        for enrolment in enrolments:
            record = marks.get(enrolment.student_id)
            register.append(
                {
                    "student_id": str(enrolment.student_id),
                    "student_name": enrolment.student.get_full_name() or enrolment.student.username,
                    "enrolment_id": str(enrolment.pk),
                    "status": record.status if record else None,
                    "remarks": (record.remarks or "") if record else "",
                    "attendance_id": str(record.pk) if record else None,
                }
            )
        return register

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def mark_bulk_attendance(
        *,
        lecture: Lecture,
        records: list,
        actor: User,
        complete_lecture: bool = True,
        ip_address: str | None = None,
    ) -> dict:
        """Record attendance for a whole class in one transaction.

        Returns a summary plus the resulting model instances; the caller serialises them.
        """
        AttendanceService._assert_may_mark(actor, lecture)

        if lecture.status == LECTURE_CANCELLED:
            raise ConflictError(
                "This lecture was cancelled, so attendance cannot be recorded against it.",
                code="lecture_cancelled",
            )

        cleaned = AttendanceService._validate_records(records)
        if not cleaned:
            raise ValidationFailed(
                "No attendance records were supplied.",
                field_errors={"records": ["Provide at least one record."]},
            )

        eligible = AttendanceService._eligible_student_ids(lecture)
        unknown = [sid for sid in cleaned if sid not in eligible]
        if unknown:
            raise ValidationFailed(
                f"{len(unknown)} of the students supplied are not actively enrolled in "
                "this batch.",
                field_errors={"records": [f"Not enrolled: {', '.join(sorted(unknown))}"]},
            )

        # Include soft-deleted rows in the lookup. `unique_together (lecture, student)` means
        # a deleted row still occupies the slot, so re-marking has to revive it rather than
        # attempt an insert that would fail - or worse, update it while leaving it hidden.
        existing = {
            str(record.student_id): record
            for record in Attendance.objects.filter(
                lecture=lecture, student_id__in=list(cleaned)
            )
        }

        to_create, to_update, touched = [], [], []
        for student_id, entry in cleaned.items():
            record = existing.get(student_id)
            if record is None:
                to_create.append(
                    Attendance(
                        lecture=lecture,
                        student_id=student_id,
                        status=entry["status"],
                        remarks=entry["remarks"],
                    )
                )
            else:
                record.status = entry["status"]
                record.remarks = entry["remarks"]
                record.is_deleted = False
                record.deleted_at = None
                record.version += 1
                to_update.append(record)

        if to_create:
            Attendance.objects.bulk_create(to_create)
            touched.extend(to_create)
        if to_update:
            Attendance.objects.bulk_update(
                to_update, ["status", "remarks", "is_deleted", "deleted_at", "version", "updated_at"]
            )
            touched.extend(to_update)

        if complete_lecture and lecture.status != LECTURE_COMPLETED:
            lecture.status = LECTURE_COMPLETED
            lecture.save(update_fields=["status"])

        tally = {}
        for entry in cleaned.values():
            tally[entry["status"]] = tally.get(entry["status"], 0) + 1

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            model_name="Lecture",
            target_id=str(lecture.pk),
            changes={
                "attendance_marked": len(cleaned),
                "created": len(to_create),
                "updated": len(to_update),
                "tally": tally,
                "lecture_status": lecture.status,
            },
            ip_address=ip_address,
        )

        return {
            "lecture_id": str(lecture.pk),
            "lecture_status": lecture.status,
            "count": len(touched),
            "created": len(to_create),
            "updated": len(to_update),
            "tally": tally,
            "records": touched,
        }

    @staticmethod
    @transaction.atomic
    def amend_attendance(
        *,
        actor: User,
        attendance: Attendance,
        status: str | None = None,
        remarks: str | None = None,
        ip_address: str | None = None,
    ) -> Attendance:
        """Correct a single mark.

        Students and parents are read-only here. The original viewset exposed unrestricted
        ``PATCH``, which let a student flip their own record from ABSENT to PRESENT.
        """
        AttendanceService._assert_may_mark(actor, attendance.lecture)

        updates = {}
        if status is not None:
            normalised = status.strip().upper()
            if normalised not in _ATTENDANCE_STATUSES:
                raise ValidationFailed(
                    f"Unknown attendance status '{status}'.",
                    field_errors={
                        "status": [f"Choose one of: {', '.join(sorted(_ATTENDANCE_STATUSES))}."]
                    },
                )
            updates["status"] = normalised
        if remarks is not None:
            updates["remarks"] = remarks[:255]

        if not updates:
            return attendance

        changes = audit.diff_fields(attendance, updates)
        for field, value in updates.items():
            setattr(attendance, field, value)
        attendance.save(update_fields=list(updates))

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=attendance,
            changes={**changes, "student": str(attendance.student_id)},
            ip_address=ip_address,
        )
        return attendance

    @staticmethod
    @transaction.atomic
    def soft_delete_attendance(
        *, actor: User, attendance: Attendance, ip_address: str | None = None
    ) -> None:
        assert_role(
            actor,
            Role.ADMIN_ROLES,
            message="Only administrators can delete an attendance record.",
        )
        assert_same_branch(
            actor,
            attendance.lecture.timetable.batch.branch_id,
            message="That record belongs to another branch.",
        )

        attendance.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=attendance,
            changes={"soft_delete": True, "student": str(attendance.student_id)},
            ip_address=ip_address,
        )

    # -------------------------------------------------------------- reporting

    @staticmethod
    def student_summary(actor: User, *, student_id, batch_id=None) -> dict:
        """Attendance percentage for one student, computed in a single aggregate query."""
        queryset = AttendanceService.filter_attendance(
            actor, student_id=student_id, batch_id=batch_id
        )
        totals = queryset.aggregate(
            total=Count("id"),
            present=Count("id", filter=Q(status=STATUS_PRESENT)),
            late=Count("id", filter=Q(status="LATE")),
            excused=Count("id", filter=Q(status="EXCUSED")),
            absent=Count("id", filter=Q(status=STATUS_ABSENT)),
        )
        total = totals["total"] or 0
        # Late still counts as attended; excused is neither credited nor penalised, so it is
        # removed from the denominator rather than counted as an absence.
        countable = total - (totals["excused"] or 0)
        attended = (totals["present"] or 0) + (totals["late"] or 0)
        percentage = round((attended / countable) * 100, 2) if countable else None

        return {
            "student_id": str(student_id),
            "total_sessions": total,
            "present": totals["present"] or 0,
            "late": totals["late"] or 0,
            "excused": totals["excused"] or 0,
            "absent": totals["absent"] or 0,
            "percentage": percentage,
            "below_threshold": percentage is not None and percentage < LOW_ATTENDANCE_THRESHOLD,
            "threshold": LOW_ATTENDANCE_THRESHOLD,
        }

    @staticmethod
    def batch_report(actor: User, *, batch_id, date_from=None, date_to=None) -> list[dict]:
        """Per-student attendance percentages for a batch, ordered worst first.

        One grouped query for the whole cohort rather than one per student, so this stays
        usable for a large batch.
        """
        queryset = AttendanceService.filter_attendance(
            actor, batch_id=batch_id, date_from=date_from, date_to=date_to
        )
        rows = (
            queryset.values(
                "student_id", "student__first_name", "student__last_name", "student__username"
            )
            .annotate(
                total=Count("id"),
                present=Count("id", filter=Q(status=STATUS_PRESENT)),
                late=Count("id", filter=Q(status="LATE")),
                excused=Count("id", filter=Q(status="EXCUSED")),
                absent=Count("id", filter=Q(status=STATUS_ABSENT)),
            )
        )

        report = []
        for row in rows:
            countable = row["total"] - row["excused"]
            attended = row["present"] + row["late"]
            percentage = round((attended / countable) * 100, 2) if countable else None
            full_name = f"{row['student__first_name']} {row['student__last_name']}".strip()
            report.append(
                {
                    "student_id": str(row["student_id"]),
                    "student_name": full_name or row["student__username"],
                    "total_sessions": row["total"],
                    "present": row["present"],
                    "late": row["late"],
                    "excused": row["excused"],
                    "absent": row["absent"],
                    "percentage": percentage,
                    "below_threshold": percentage is not None
                    and percentage < LOW_ATTENDANCE_THRESHOLD,
                }
            )
        # Students with no countable sessions sort last; the point of the list is to surface
        # the students who need chasing.
        report.sort(key=lambda row: (row["percentage"] is None, row["percentage"] or 0))
        return report

    @staticmethod
    def low_attendance_students(actor: User, *, batch_id=None, threshold: float | None = None):
        """Students below the attendance threshold, for the alert panel and parent emails."""
        limit = LOW_ATTENDANCE_THRESHOLD if threshold is None else float(threshold)
        if batch_id:
            rows = AttendanceService.batch_report(actor, batch_id=batch_id)
        else:
            from academics.services.batch_service import BatchService

            rows = []
            for batch in BatchService.visible_batches(actor):
                rows.extend(AttendanceService.batch_report(actor, batch_id=batch.pk))
        return [
            row for row in rows if row["percentage"] is not None and row["percentage"] < limit
        ]

    # -------------------------------------------------------------- internals

    @staticmethod
    def _validate_records(records) -> dict[str, dict]:
        """Turn an untrusted payload into ``{student_id: {status, remarks}}``.

        Rejects anything that is not a list of objects, normalises the status against the
        model's choices, and collapses duplicate entries for the same student (last wins)
        so ``bulk_create`` cannot hit the unique constraint.
        """
        if records is None:
            raise ValidationFailed(
                "Provide a 'records' list.", field_errors={"records": ["This field is required."]}
            )
        if not isinstance(records, (list, tuple)):
            raise ValidationFailed(
                "'records' must be a list of attendance entries.",
                field_errors={"records": ["Expected a list."]},
            )
        if len(records) > 500:
            raise ValidationFailed(
                "Mark at most 500 students in one request.",
                field_errors={"records": ["Too many entries."]},
            )

        cleaned: dict[str, dict] = {}
        errors: list[str] = []
        for index, entry in enumerate(records):
            if not isinstance(entry, dict):
                errors.append(f"Entry {index}: expected an object.")
                continue

            student_id = entry.get("student_id") or entry.get("student")
            if not student_id:
                errors.append(f"Entry {index}: 'student_id' is required.")
                continue

            status = str(entry.get("status") or STATUS_PRESENT).strip().upper()
            if status not in _ATTENDANCE_STATUSES:
                errors.append(
                    f"Entry {index}: unknown status '{status}'. "
                    f"Choose one of: {', '.join(sorted(_ATTENDANCE_STATUSES))}."
                )
                continue

            remarks = entry.get("remarks") or ""
            cleaned[str(student_id)] = {"status": status, "remarks": str(remarks)[:255]}

        if errors:
            raise ValidationFailed(
                "Some attendance entries were rejected.", field_errors={"records": errors}
            )
        return cleaned

    @staticmethod
    def _eligible_student_ids(lecture: Lecture) -> set[str]:
        return {
            str(pk)
            for pk in active(CourseEnrolment)
            .filter(batch_id=lecture.timetable.batch_id, status="ACTIVE")
            .values_list("student_id", flat=True)
        }

    @staticmethod
    def _assert_may_mark(actor: User, lecture: Lecture) -> None:
        assert_role(
            actor,
            ATTENDANCE_MARKERS,
            message="Only teachers and administrators can record attendance.",
        )
        if is_global(actor):
            return
        assert_same_branch(
            actor,
            lecture.timetable.batch.branch_id,
            message="That lecture belongs to another branch.",
        )
        if actor.role_code == Role.TEACHER and lecture.timetable.teacher_id != actor.pk:
            from institute_crm.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "You can only record attendance for sessions you are timetabled to teach.",
                code="not_your_session",
            )
