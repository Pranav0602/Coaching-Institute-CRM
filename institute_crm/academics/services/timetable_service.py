"""
Timetable scheduling with conflict detection.

The recurring weekly schedule is the one place in this app where a write can be *silently*
wrong: nothing stops you booking the same teacher into two rooms at 10:00 on Monday, and the
mistake only surfaces when the teacher fails to show up for one of them. So the interesting
work here is :meth:`TimetableService.find_conflicts`, which checks three resources against a
proposed slot - the teacher, the batch (a cohort cannot be in two classes at once) and the
room - before anything is written.

Overlap test: two half-open intervals ``[a_start, a_end)`` and ``[b_start, b_end)`` collide
exactly when ``a_start < b_end and b_start < a_end``. Using half-open intervals means a
session ending at 10:00 and one starting at 10:00 are *not* a conflict, which is what a
back-to-back timetable needs.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from academics.models import Lecture, Timetable
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import (
    assert_role,
    assert_same_branch,
    child_student_user_ids,
    narrow,
    scope_to_branch,
)
from institute_crm.utils import active

#: Roles that may edit the weekly schedule.
TIMETABLE_EDITORS = Role.ADMIN_ROLES

_DAY_CODES = {code for code, _ in Timetable.DAY_CHOICES}


class TimetableService:
    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_slots(actor: User):
        queryset = (
            active(Timetable)
            .select_related("batch", "batch__branch", "subject", "teacher")
            .order_by("day_of_week", "start_time")
        )
        queryset = scope_to_branch(queryset, actor, branch_path="batch__branch")

        role = getattr(actor, "role_code", None)
        if role == Role.TEACHER:
            queryset = queryset.filter(
                Q(teacher_id=actor.pk) | Q(batch__teachers=actor)
            ).distinct()
        elif role == Role.STUDENT:
            queryset = queryset.filter(
                batch__enrolments__student_id=actor.pk,
                batch__enrolments__is_deleted=False,
                batch__enrolments__status="ACTIVE",
            ).distinct()
        elif role == Role.PARENT:
            queryset = queryset.filter(
                batch__enrolments__student_id__in=child_student_user_ids(actor),
                batch__enrolments__is_deleted=False,
                batch__enrolments__status="ACTIVE",
            ).distinct()

        return queryset

    @staticmethod
    def filter_slots(
        actor: User,
        *,
        teacher_id=None,
        batch_id=None,
        subject_id=None,
        day_of_week: str | None = None,
    ):
        return narrow(
            TimetableService.visible_slots(actor),
            {
                "teacher_id": teacher_id,
                "batch_id": batch_id,
                "subject_id": subject_id,
                "day_of_week": day_of_week.upper() if day_of_week else None,
            },
        )

    @staticmethod
    def get_slot_for_actor(actor: User, slot_id) -> Timetable:
        try:
            return TimetableService.visible_slots(actor).get(pk=slot_id)
        except Timetable.DoesNotExist as exc:
            raise NotFoundError("Timetable slot not found.") from exc

    @staticmethod
    def weekly_grid(actor: User, **filters) -> dict:
        """The schedule keyed by day, ready for a week-view UI."""
        grid: dict[str, list] = {code: [] for code, _ in Timetable.DAY_CHOICES}
        for slot in TimetableService.filter_slots(actor, **filters):
            grid[slot.day_of_week].append(slot)
        return grid

    # ------------------------------------------------------- conflict checking

    @staticmethod
    def find_conflicts(
        *,
        batch,
        teacher,
        day_of_week: str,
        start_time,
        end_time,
        room_number: str | None = None,
        exclude_pk=None,
    ) -> list[dict]:
        """Return every clash a proposed slot would cause, as plain dicts.

        Returns a list rather than raising, so callers can either preview conflicts (a
        "check availability" endpoint) or reject the write. Dicts rather than model
        instances keeps the result trivially serialisable.
        """
        if not (day_of_week and start_time and end_time):
            return []

        overlapping = (
            active(Timetable)
            .filter(day_of_week=day_of_week, start_time__lt=end_time, end_time__gt=start_time)
            .select_related("batch", "subject", "teacher")
        )
        if exclude_pk:
            overlapping = overlapping.exclude(pk=exclude_pk)

        resource_filter = Q()
        if teacher is not None:
            resource_filter |= Q(teacher_id=teacher.pk)
        if batch is not None:
            resource_filter |= Q(batch_id=batch.pk)
        if room_number:
            # A room clash only matters within the branch that owns the room, since two
            # branches can each have a "Room 101".
            branch_id = getattr(batch, "branch_id", None)
            room_q = Q(room_number__iexact=room_number)
            if branch_id:
                room_q &= Q(batch__branch_id=branch_id)
            resource_filter |= room_q

        if not resource_filter:
            return []

        conflicts = []
        for other in overlapping.filter(resource_filter):
            if teacher is not None and other.teacher_id == teacher.pk:
                reason, resource = "teacher", other.teacher.get_full_name() or other.teacher.username
            elif batch is not None and other.batch_id == batch.pk:
                reason, resource = "batch", other.batch.name
            else:
                reason, resource = "room", other.room_number
            conflicts.append(
                {
                    "reason": reason,
                    "resource": resource,
                    "timetable_id": str(other.pk),
                    "batch": other.batch.name,
                    "subject": other.subject.title,
                    "day_of_week": other.day_of_week,
                    "start_time": other.start_time.strftime("%H:%M"),
                    "end_time": other.end_time.strftime("%H:%M"),
                    "room_number": other.room_number,
                }
            )
        return conflicts

    @staticmethod
    def check_availability(actor: User, *, data: dict, exclude_pk=None) -> dict:
        """Dry-run endpoint backing the "is this slot free?" hint in the scheduling form."""
        conflicts = TimetableService.find_conflicts(
            batch=data.get("batch"),
            teacher=data.get("teacher"),
            day_of_week=(data.get("day_of_week") or "").upper(),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            room_number=data.get("room_number"),
            exclude_pk=exclude_pk,
        )
        return {"available": not conflicts, "conflicts": conflicts}

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def create_slot(*, actor: User, data: dict, ip_address: str | None = None) -> Timetable:
        assert_role(
            actor, TIMETABLE_EDITORS, message="Only administrators can edit the timetable."
        )

        payload = dict(data)
        TimetableService._validate_slot(payload)

        batch = payload["batch"]
        assert_same_branch(
            actor,
            batch.branch_id,
            message="You can only schedule sessions for batches in your own branch.",
        )

        conflicts = TimetableService.find_conflicts(
            batch=batch,
            teacher=payload.get("teacher"),
            day_of_week=payload["day_of_week"],
            start_time=payload["start_time"],
            end_time=payload["end_time"],
            room_number=payload.get("room_number"),
        )
        TimetableService._raise_for_conflicts(conflicts)

        slot = Timetable.objects.create(**payload)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=slot,
            changes={
                "batch": str(slot.batch_id),
                "subject": str(slot.subject_id),
                "teacher": str(slot.teacher_id),
                "when": f"{slot.day_of_week} {slot.start_time}-{slot.end_time}",
                "room": slot.room_number,
            },
            ip_address=ip_address,
        )
        return slot

    @staticmethod
    @transaction.atomic
    def update_slot(
        *, actor: User, slot: Timetable, data: dict, ip_address: str | None = None
    ) -> Timetable:
        """The counterpart the previous implementation was missing.

        ``perform_create`` guarded the branch but ``perform_update`` did not exist, so a
        branch admin could ``PATCH`` a slot onto another branch's batch. Both paths run the
        same checks now.
        """
        assert_role(
            actor, TIMETABLE_EDITORS, message="Only administrators can edit the timetable."
        )

        merged = {
            "batch": data.get("batch", slot.batch),
            "subject": data.get("subject", slot.subject),
            "teacher": data.get("teacher", slot.teacher),
            "day_of_week": (data.get("day_of_week") or slot.day_of_week or "").upper(),
            "start_time": data.get("start_time", slot.start_time),
            "end_time": data.get("end_time", slot.end_time),
            "room_number": data.get("room_number", slot.room_number),
        }
        TimetableService._validate_slot(merged)

        # Guard both ends of a move: the branch it is leaving and the branch it is entering.
        assert_same_branch(
            actor,
            slot.batch.branch_id,
            message="You can only edit sessions in your own branch.",
        )
        assert_same_branch(
            actor,
            merged["batch"].branch_id,
            message="You can only move a session to a batch in your own branch.",
        )

        conflicts = TimetableService.find_conflicts(
            batch=merged["batch"],
            teacher=merged["teacher"],
            day_of_week=merged["day_of_week"],
            start_time=merged["start_time"],
            end_time=merged["end_time"],
            room_number=merged["room_number"],
            exclude_pk=slot.pk,
        )
        TimetableService._raise_for_conflicts(conflicts)

        changes = audit.diff_fields(slot, merged)
        for field, value in merged.items():
            setattr(slot, field, value)
        slot.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=slot,
            changes=changes,
            ip_address=ip_address,
        )
        return slot

    @staticmethod
    @transaction.atomic
    def soft_delete_slot(
        *, actor: User, slot: Timetable, ip_address: str | None = None
    ) -> None:
        assert_role(
            actor, TIMETABLE_EDITORS, message="Only administrators can edit the timetable."
        )
        assert_same_branch(
            actor,
            slot.batch.branch_id,
            message="You can only remove sessions in your own branch.",
        )

        # Lectures already held are history and must survive; only future scheduled ones
        # are withdrawn along with the slot.
        from django.utils import timezone

        future = active(Lecture).filter(
            timetable=slot, status="SCHEDULED", date__gte=timezone.localdate()
        )
        withdrawn = future.count()
        for lecture in future:
            lecture.soft_delete()

        slot.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=slot,
            changes={"soft_delete": True, "future_lectures_withdrawn": withdrawn},
            ip_address=ip_address,
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _validate_slot(payload: dict) -> None:
        """Field-level and cross-field rules that used to live in the serializer."""
        batch = payload.get("batch")
        subject = payload.get("subject")
        teacher = payload.get("teacher")
        start_time = payload.get("start_time")
        end_time = payload.get("end_time")
        day_of_week = (payload.get("day_of_week") or "").upper()

        missing = {
            name: ["This field is required."]
            for name, value in (
                ("batch", batch),
                ("subject", subject),
                ("teacher", teacher),
                ("start_time", start_time),
                ("end_time", end_time),
            )
            if value is None
        }
        if missing:
            raise ValidationFailed(
                "A session needs a batch, subject, teacher and time range.",
                field_errors=missing,
            )

        if day_of_week not in _DAY_CODES:
            raise ValidationFailed(
                "Choose a valid day of the week.",
                field_errors={"day_of_week": [f"Choose one of: {', '.join(sorted(_DAY_CODES))}."]},
            )
        payload["day_of_week"] = day_of_week

        if end_time <= start_time:
            raise ValidationFailed(
                "The session end time must be after its start time.",
                field_errors={"end_time": ["Must be after the start time."]},
            )

        if subject.course_id != batch.course_id:
            raise ValidationFailed(
                f"'{subject.title}' is not part of the course this batch runs.",
                field_errors={"subject": ["Choose a subject from the batch's course."]},
            )

        # An authorisation-shaped rule, so it belongs here and not in a serializer.
        if teacher.role_code != Role.TEACHER:
            raise ValidationFailed(
                "Only users with the Teacher role can be assigned to a session.",
                field_errors={"teacher": ["This account is not a teacher."]},
            )
        if getattr(teacher, "is_deleted", False) or not teacher.is_active:
            raise ValidationFailed(
                "That teacher account is inactive.",
                field_errors={"teacher": ["Account is inactive."]},
            )
        if teacher.branch_id and teacher.branch_id != batch.branch_id:
            raise ValidationFailed(
                f"{teacher.get_full_name() or teacher.username} is assigned to a different "
                "branch from this batch.",
                field_errors={"teacher": ["Teacher and batch must be in the same branch."]},
            )

    @staticmethod
    def _raise_for_conflicts(conflicts: list[dict]) -> None:
        if not conflicts:
            return
        first = conflicts[0]
        label = {
            "teacher": f"{first['resource']} is already teaching",
            "batch": f"Batch {first['resource']} already has a session",
            "room": f"{first['resource']} is already booked",
        }[first["reason"]]
        raise ConflictError(
            f"{label} on {first['day_of_week'].title()} from {first['start_time']} to "
            f"{first['end_time']} ({first['subject']}).",
            code=f"timetable_{first['reason']}_conflict",
            field_errors={"conflicts": conflicts},
        )
