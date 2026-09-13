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
            # granting a teacher access to the cohort. Assigned (primary/co/substitute)
            # teachers via Batch.teachers also retain access even without a slot.
            queryset = queryset.filter(
                Q(timetables__teacher_id=actor.pk, timetables__is_deleted=False)
                | Q(teachers=actor)
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
        teacher_ids = payload.pop("teacher_ids", None)
        if teacher_ids is None:
            # Allow `teachers` (list of ids or instances) as an alias from serializers.
            alias = payload.pop("teachers", None)
            if alias is not None:
                teacher_ids = [
                    str(getattr(item, "pk", item)) for item in alias
                ]
        # A non-global caller's branch is imposed, not accepted from the request body.
        payload["branch"] = resolve_write_branch(actor, payload.get("branch"))

        code = BatchService._normalise_code(payload.get("code"))
        BatchService._assert_code_available(code)
        payload["code"] = code

        BatchService._validate_dates(payload.get("start_date"), payload.get("end_date"))
        BatchService._validate_capacity(payload.get("max_capacity"))

        batch = Batch.objects.create(**payload)
        if teacher_ids is not None:
            teachers = BatchService._resolve_teacher_ids(teacher_ids, batch)
            batch.teachers.set(teachers)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=batch,
            changes={
                "code": batch.code,
                "name": batch.name,
                "branch": str(batch.branch_id),
                "course": str(batch.course_id),
                "teachers": [str(t.pk) for t in batch.teachers.all()] if teacher_ids is not None else [],
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

        teacher_ids = payload.pop("teacher_ids", None)
        if teacher_ids is None and "teachers" in payload:
            alias = payload.pop("teachers")
            teacher_ids = [
                str(getattr(item, "pk", item)) for item in alias
            ] if alias is not None else None

        changes = audit.diff_fields(batch, payload)
        for field, value in payload.items():
            setattr(batch, field, value)
        batch.save()

        if teacher_ids is not None:
            teachers = BatchService._resolve_teacher_ids(teacher_ids, batch)
            batch.teachers.set(teachers)
            changes["teachers"] = [str(t.pk) for t in teachers]

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
    def assign_teachers(
        *, actor: User, batch: Batch, teacher_ids: list, ip_address: str | None = None
    ) -> Batch:
        """Replace the assigned-teacher roster for a batch."""
        assert_role(actor, BATCH_EDITORS, message="Only administrators can assign teachers.")
        # Access check: batch must be visible to actor (enforces branch scoping).
        BatchService.get_batch_for_actor(actor, batch.pk)
        teachers = BatchService._resolve_teacher_ids(teacher_ids or [], batch)
        batch.teachers.set(teachers)
        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=batch,
            changes={"teachers": [str(t.pk) for t in teachers]},
            ip_address=ip_address,
        )
        return batch

    @staticmethod
    def batch_progress(actor: User, batch_id: str) -> dict:
        """Full operational snapshot for one batch: timeline, lectures, attendance,
        assignments, exams and per-student 360 scorecard."""
        from django.utils import timezone

        batch = BatchService.get_batch_for_actor(actor, batch_id)
        today = timezone.localdate()

        enrolled_qs = active(CourseEnrolment).filter(batch=batch, status="ACTIVE").select_related("student")
        enrolments = list(enrolled_qs)
        enrolled_count = len(enrolments)
        dropped_completed = active(CourseEnrolment).filter(batch=batch).exclude(status="ACTIVE").count()
        seats_remaining = max(batch.max_capacity - enrolled_count, 0)

        teachers = list(batch.teachers.filter(is_deleted=False))
        teacher_list = [
            {
                "id": str(t.pk),
                "name": t.get_full_name() or t.username,
                "email": t.email,
            }
            for t in teachers
        ]

        total_days = (batch.end_date - batch.start_date).days + 1 if batch.end_date and batch.start_date else 0
        elapsed_days = (min(today, batch.end_date) - batch.start_date).days + 1 if batch.start_date and batch.end_date and today >= batch.start_date else 0
        elapsed_days = max(min(elapsed_days, total_days) if total_days else 0, 0)
        remaining_days = max(total_days - elapsed_days, 0) if total_days else 0
        progress_pct = round((elapsed_days / total_days) * 100, 2) if total_days else 0
        if today < batch.start_date:
            lifecycle = "UPCOMING"
        elif today > batch.end_date:
            lifecycle = "FINISHED"
        else:
            lifecycle = "RUNNING"

        from academics.models import Attendance, Lecture, Timetable
        lectures_qs = active(Lecture).filter(timetable__batch=batch, timetable__is_deleted=False)
        total_lectures = lectures_qs.count()
        completed_lectures = lectures_qs.filter(status="COMPLETED").count()
        cancelled_lectures = lectures_qs.filter(status="CANCELLED").count()
        scheduled_lectures = lectures_qs.filter(status="SCHEDULED").count()
        topics_taught = list(
            lectures_qs.filter(status="COMPLETED").values_list("topic", flat=True).distinct()[:100]
        )
        syllabus_progress = round((completed_lectures / total_lectures) * 100, 2) if total_lectures else 0
        timetable_count = active(Timetable).filter(batch=batch).count()

        att_qs = active(Attendance).filter(lecture__timetable__batch=batch, lecture__is_deleted=False)
        total_att_rows = att_qs.count()
        present_rows = att_qs.filter(status__in=["PRESENT", "LATE"]).count()
        attendance_pct = round((present_rows / total_att_rows) * 100, 2) if total_att_rows else None
        # Per-student attendance for low-attendance count + 360 matrix.
        from django.db.models import Count, Q as _Q
        per_student_att = (
            att_qs.values("student_id")
            .annotate(
                total=Count("id"),
                present=Count("id", filter=_Q(status__in=["PRESENT", "LATE"])),
                excused=Count("id", filter=_Q(status="EXCUSED")),
            )
        )
        att_map: dict[str, dict] = {}
        low_attendance_count = 0
        for row in per_student_att:
            countable = row["total"] - row["excused"]
            pct = round((row["present"] / countable) * 100, 2) if countable else None
            att_map[str(row["student_id"])] = {"percentage": pct, "sessions": row["total"]}
            if pct is not None and pct < 75:
                low_attendance_count += 1

        batch_avg_attendance = attendance_pct
        if att_map:
            pcts = [v["percentage"] for v in att_map.values() if v["percentage"] is not None]
            batch_avg_attendance = round(sum(pcts) / len(pcts), 2) if pcts else None

        # Assignments stats.
        try:
            from assignments_exams.models import Assignment, Submission
            assignments = list(active(Assignment).filter(batch=batch))
            total_assignments = len(assignments)
            expected_submissions = total_assignments * enrolled_count
            subs_qs = active(Submission).filter(assignment__batch=batch)
            total_received = subs_qs.count()
            pending_evals = subs_qs.filter(marks_obtained__isnull=True).count()
            submission_rate = round((total_received / expected_submissions) * 100, 2) if expected_submissions else 0
            evaluated = list(subs_qs.exclude(marks_obtained__isnull=True).select_related("assignment"))
            if evaluated:
                ratios = [
                    (float(s.marks_obtained) / float(s.assignment.total_marks) * 100)
                    for s in evaluated if s.assignment.total_marks
                ]
                avg_assignment_score = round(sum(ratios) / len(ratios), 2) if ratios else None
            else:
                avg_assignment_score = None
            # Per-student submission aggregates.
            from django.db.models import Avg as _Avg
            sub_rows = subs_qs.values("student_id").annotate(
                submitted=Count("id"), avg_marks=_Avg("marks_obtained")
            )
            sub_map = {str(r["student_id"]): r for r in sub_rows}
        except Exception:
            total_assignments = 0
            total_received = 0
            expected_submissions = 0
            submission_rate = 0
            pending_evals = 0
            avg_assignment_score = None
            sub_map = {}

        # Exams stats.
        try:
            from assignments_exams.models import Exam, Result
            exams = list(active(Exam).filter(batch=batch))
            total_exams = len(exams)
            results_qs = active(Result).filter(exam__batch=batch)
            results_published = results_qs.count()
            exam_scores: list[float] = []
            passed = 0
            grade_dist = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
            per_exam_results = list(results_qs.select_related("exam"))
            for res in per_exam_results:
                total_marks = float(res.exam.total_marks) if res.exam.total_marks else 0
                obtained = float(res.marks_obtained or 0)
                pct = (obtained / total_marks * 100) if total_marks else 0
                exam_scores.append(pct)
                if obtained >= float(res.exam.passing_marks or 0):
                    passed += 1
                grade = (res.grade or "").strip() or BatchService._grade_for_pct(pct)
                if grade in grade_dist:
                    grade_dist[grade] += 1
                else:
                    grade_dist[grade] = grade_dist.get(grade, 0) + 1
            pass_rate = round((passed / results_published) * 100, 2) if results_published else None
            avg_exam_score = round(sum(exam_scores) / len(exam_scores), 2) if exam_scores else None
            top_score = round(max(exam_scores), 2) if exam_scores else None
            lowest_score = round(min(exam_scores), 2) if exam_scores else None
            res_rows = results_qs.values("student_id").annotate(
                taken=Count("id"), avg_marks=_Avg("marks_obtained")
            )
            # Need per-student average percentage (marks relative to each exam's total).
            res_map: dict[str, dict] = {}
            for r in res_rows:
                sid = str(r["student_id"])
                res_map[sid] = {"taken": r["taken"], "avg_marks": float(r["avg_marks"]) if r["avg_marks"] is not None else None}
            # Compute percentage average per student.
            student_results = {}
            for res in per_exam_results:
                sid = str(res.student_id)
                total_marks = float(res.exam.total_marks) if res.exam.total_marks else 0
                pct = (float(res.marks_obtained or 0) / total_marks * 100) if total_marks else 0
                student_results.setdefault(sid, []).append(pct)
            exam_avg_map = {sid: round(sum(v) / len(v), 2) for sid, v in student_results.items()}
        except Exception:
            total_exams = 0
            results_published = 0
            pass_rate = None
            avg_exam_score = None
            top_score = None
            lowest_score = None
            grade_dist = {}
            res_map = {}
            exam_avg_map = {}

        # 360 scorecard.
        scorecard = []
        for enr in enrolments:
            sid = str(enr.student_id)
            s_att = (att_map.get(sid) or {}).get("percentage")
            sub_info = sub_map.get(sid) or {}
            submitted_count = sub_info.get("submitted", 0)
            assignment_pct = round((submitted_count / total_assignments) * 100, 2) if total_assignments else None
            exam_avg = exam_avg_map.get(sid)
            health = BatchService._health_flag(s_att, assignment_pct, exam_avg)
            scorecard.append(
                {
                    "student_id": sid,
                    "student_name": enr.student.get_full_name() or enr.student.username,
                    "student_email": enr.student.email,
                    "attendance_pct": s_att,
                    "assignments_submitted": submitted_count,
                    "assignments_total": total_assignments,
                    "assignment_completion_pct": assignment_pct,
                    "exams_taken": (res_map.get(sid) or {}).get("taken", 0),
                    "exam_avg_pct": exam_avg,
                    "health": health,
                }
            )

        return {
            "batch": {
                "id": str(batch.pk),
                "name": batch.name,
                "code": batch.code,
                "course": str(batch.course_id),
                "course_title": getattr(batch.course, "title", ""),
                "branch": str(batch.branch_id),
                "branch_name": getattr(batch.branch, "name", ""),
                "max_capacity": batch.max_capacity,
                "enrolled_count": enrolled_count,
                "dropped_completed_count": dropped_completed,
                "seats_remaining": seats_remaining,
                "status": lifecycle,
            },
            "teachers": teacher_list,
            "timeline": {
                "start_date": batch.start_date.isoformat() if batch.start_date else None,
                "end_date": batch.end_date.isoformat() if batch.end_date else None,
                "total_days": total_days,
                "elapsed_days": elapsed_days,
                "remaining_days": remaining_days,
                "progress_pct": progress_pct,
                "status": lifecycle,
            },
            "lectures": {
                "total": total_lectures,
                "completed": completed_lectures,
                "cancelled": cancelled_lectures,
                "scheduled": scheduled_lectures,
                "timetable_slots": timetable_count,
                "syllabus_progress_pct": syllabus_progress,
                "topics_taught": topics_taught,
            },
            "attendance": {
                "total_rows": total_att_rows,
                "overall_pct": batch_avg_attendance,
                "low_attendance_count": low_attendance_count,
                "threshold": 75.0,
            },
            "assignments": {
                "total_assignments": total_assignments,
                "submissions_received": total_received,
                "expected_submissions": expected_submissions,
                "submission_rate_pct": submission_rate,
                "pending_evaluations": pending_evals,
                "average_score_pct": avg_assignment_score,
            },
            "exams": {
                "total_exams": total_exams,
                "results_published": results_published,
                "pass_rate_pct": pass_rate,
                "average_score_pct": avg_exam_score,
                "top_score_pct": top_score,
                "lowest_score_pct": lowest_score,
                "grade_distribution": grade_dist,
            },
            "students": scorecard,
        }

    @staticmethod
    def batches_progress_overview(actor: User, **filters) -> list[dict]:
        """Lightweight per-batch summary for dashboard cards and list views."""
        batches = list(BatchService.filter_batches(actor, **filters).select_related("course", "branch"))
        overview = []
        for batch in batches:
            try:
                progress = BatchService.batch_progress(actor, str(batch.pk))
                overview.append(
                    {
                        "id": str(batch.pk),
                        "name": batch.name,
                        "code": batch.code,
                        "course_title": getattr(batch.course, "title", ""),
                        "branch_name": getattr(batch.branch, "name", ""),
                        "status": progress["timeline"]["status"],
                        "timeline_pct": progress["timeline"]["progress_pct"],
                        "enrolled_count": progress["batch"]["enrolled_count"],
                        "max_capacity": batch.max_capacity,
                        "capacity_filled_pct": round(
                            (progress["batch"]["enrolled_count"] / batch.max_capacity) * 100, 2
                        ) if batch.max_capacity else 0,
                        "teachers": progress["teachers"],
                        "attendance_pct": progress["attendance"]["overall_pct"],
                        "assignment_submission_pct": progress["assignments"]["submission_rate_pct"],
                        "exam_pass_rate_pct": progress["exams"]["pass_rate_pct"],
                        "syllabus_progress_pct": progress["lectures"]["syllabus_progress_pct"],
                        "at_risk_count": sum(1 for s in progress["students"] if s["health"] == "AT_RISK"),
                    }
                )
            except Exception:
                continue
        return overview

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

    @staticmethod
    def _resolve_teacher_ids(teacher_ids, batch: Batch) -> list[User]:
        """Validate teacher ids: must hold TEACHER role and belong to batch branch (or be global)."""
        if not teacher_ids:
            return []
        ids = [str(getattr(t, "pk", t)) for t in teacher_ids]
        teachers = list(active(User).filter(pk__in=ids).select_related("role", "branch"))
        found = {str(t.pk) for t in teachers}
        missing = [tid for tid in ids if tid not in found]
        if missing:
            raise ValidationFailed(
                f"{len(missing)} teacher account(s) were not found or are inactive.",
                field_errors={"teacher_ids": [f"Unknown teachers: {', '.join(missing)}"]},
            )
        errors = []
        for teacher in teachers:
            if teacher.role_code != Role.TEACHER:
                errors.append(f"{teacher.username} is not a Teacher.")
            elif teacher.branch_id and teacher.branch_id != batch.branch_id:
                errors.append(
                    f"{teacher.username} belongs to a different branch from this batch."
                )
        if errors:
            raise ValidationFailed(
                "Some teachers cannot be assigned to this batch.",
                field_errors={"teacher_ids": errors},
            )
        return teachers

    @staticmethod
    def _grade_for_pct(pct: float) -> str:
        if pct >= 90:
            return "A+"
        if pct >= 80:
            return "A"
        if pct >= 70:
            return "B"
        if pct >= 60:
            return "C"
        if pct >= 40:
            return "D"
        return "F"

    @staticmethod
    def _health_flag(att_pct, assign_pct, exam_avg) -> str:
        """ON_TRACK / NEEDS_ATTENTION / AT_RISK based on attendance, assignments, exams."""
        risks = 0
        warnings = 0
        if att_pct is not None:
            if att_pct < 75:
                risks += 1
            elif att_pct < 85:
                warnings += 1
        if assign_pct is not None:
            if assign_pct < 50:
                risks += 1
            elif assign_pct < 75:
                warnings += 1
        if exam_avg is not None:
            if exam_avg < 40:
                risks += 1
            elif exam_avg < 60:
                warnings += 1
        if risks >= 1:
            return "AT_RISK"
        if warnings >= 1:
            return "NEEDS_ATTENTION"
        return "ON_TRACK"
