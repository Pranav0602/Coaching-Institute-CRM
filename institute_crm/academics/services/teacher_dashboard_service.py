"""
Teacher dashboard aggregation.

Scoped strictly to the requesting teacher's own assignments and courses:

* explicit teacher-course assignments (:class:`TeacherAssignment`), plus
* existing batch-level assignment (``Batch.teachers``) and per-slot
  ``Timetable.teacher`` links,

all within the teacher's own branch. Teachers with no course assignments
still get a valid, empty dashboard; nothing outside their scope is exposed.
"""
from __future__ import annotations

from django.db.models import Count, Q

from accounts.models import Role
from academics.models import (
    Attendance,
    Batch,
    Course,
    CourseEnrolment,
    Lecture,
    TeacherAssignment,
    Timetable,
)
from academics.services.teacher_assignment_service import TeacherAssignmentService
from institute_crm.exceptions import PermissionDeniedError
from institute_crm.utils import active

_LOW_ATTENDANCE = 75.0


class TeacherDashboardService:
    @staticmethod
    def teacher_dashboard(actor) -> dict:
        if not (actor and actor.is_authenticated and actor.role_code == Role.TEACHER):
            raise PermissionDeniedError(
                "Only teachers can view the teacher dashboard.", code="teacher_only"
            )

        branch = actor.branch
        branch_id = actor.branch_id
        scope = TeacherAssignmentService.assigned_scope(actor)
        assigned_course_ids = set(scope["course_ids"])
        assigned_batch_ids = set(scope["batch_ids"])

        # Explicit teacher-course assignments for this teacher (active rows).
        explicit = list(
            active(TeacherAssignment)
            .filter(teacher_id=actor.pk)
            .select_related("course", "branch")
        )
        explicit_by_course: dict = {}
        for row in explicit:
            explicit_by_course.setdefault(row.course_id, []).append(row)

        course_ids = set(assigned_course_ids) | set(explicit_by_course.keys())

        # Batches in scope: own branch, in an assigned course, or explicitly assigned.
        batch_qs = active(Batch).filter(is_deleted=False).select_related("course", "branch")
        if branch_id:
            batch_qs = batch_qs.filter(branch_id=branch_id)
        scope_batch_filter = Q(pk__in=list(assigned_batch_ids))
        if course_ids:
            scope_batch_filter |= Q(course_id__in=list(course_ids))
        batches = list(batch_qs.filter(scope_batch_filter).distinct())

        batches_by_course: dict = {}
        for b in batches:
            batches_by_course.setdefault(b.course_id, []).append(b)

        # Ordered list of assigned courses.
        courses = list(
            active(Course).filter(pk__in=list(course_ids)).order_by("title")
        )

        assigned_courses = [
            TeacherDashboardService._course_payload(
                actor, course, batches_by_course.get(course.pk, []),
                explicit_by_course.get(course.pk, []),
            )
            for course in courses
        ]

        schedule = TeacherDashboardService._schedule(actor, batches)
        notices = TeacherDashboardService._notices(actor)
        notifications = TeacherDashboardService._notifications(actor)
        upcoming_activities = TeacherDashboardService._upcoming_activities(actor, batches)
        tasks = TeacherDashboardService._tasks(actor, batches)

        total_students = len({
            s["student_id"]
            for c in assigned_courses
            for s in c["students"]
        })

        return {
            "teacher": {
                "id": str(actor.pk),
                "username": actor.username,
                "name": actor.get_full_name() or actor.username,
                "email": actor.email,
                "phone": actor.phone,
                "role": Role.TEACHER,
            },
            "branch": (
                {
                    "id": str(branch.pk), "name": branch.name, "code": branch.code,
                    "city": branch.city,
                }
                if branch else None
            ),
            "assigned_branch": branch.name if branch else None,
            "summary": {
                "assigned_courses": len(assigned_courses),
                "assigned_batches": len(batches),
                "total_students": total_students,
                "has_course_assignments": bool(explicit_by_course),
                "schedule_slots": len(schedule),
                "notices": len(notices),
                "pending_tasks": len(tasks),
            },
            "assigned_courses": assigned_courses,
            "schedule": schedule,
            "today_schedule": [s for s in schedule if s["day_of_week"] == TeacherDashboardService._today_code()],
            "notices": notices,
            "notifications": notifications,
            "upcoming_activities": upcoming_activities,
            "tasks": tasks,
        }

    # ------------------------------------------------------------- internals

    @staticmethod
    def _course_payload(actor, course, batches, explicit_rows) -> dict:
        batch_ids = [b.pk for b in batches]

        # Students enrolled in this assigned course, within the teacher's branch.
        enrolments = []
        if batch_ids:
            enrolments = list(
                active(CourseEnrolment)
                .filter(course_id=course.pk, batch_id__in=batch_ids, status="ACTIVE")
                .select_related("student", "batch")
            )
        student_map: dict = {}
        for e in enrolments:
            sid = str(e.student_id)
            student_map.setdefault(sid, {
                "student_id": sid,
                "name": e.student.get_full_name() or e.student.username,
                "username": e.student.username,
                "email": e.student.email,
                "phone": e.student.phone,
                "reg_no": TeacherDashboardService._reg_no(e.student),
                "batch": e.batch.name,
                "batch_id": str(e.batch_id),
                "enrolment_status": e.status,
            })
        # Also students linked directly to the course in this branch.
        try:
            from users_profiles.models import StudentProfile

            direct = (
                active(StudentProfile)
                .filter(course_id=course.pk, is_deleted=False, user__branch_id=actor.branch_id)
                .select_related("user")
            )
            for p in direct:
                sid = str(p.user_id)
                if sid not in student_map:
                    student_map[sid] = {
                        "student_id": sid,
                        "name": p.user.get_full_name() or p.user.username,
                        "username": p.user.username,
                        "email": p.user.email,
                        "phone": p.user.phone,
                        "reg_no": p.reg_no,
                        "batch": p.batch.name if p.batch_id else None,
                        "batch_id": str(p.batch_id) if p.batch_id else None,
                        "enrolment_status": None,
                    }
        except Exception:
            pass

        students = sorted(student_map.values(), key=lambda s: (s["name"] or "").lower())

        # Per-batch progress snapshot (attendance etc.) reusing BatchService.
        batch_summaries = []
        for b in batches:
            batch_summaries.append(TeacherDashboardService._batch_summary(actor, b))

        schedule = TeacherDashboardService._schedule(actor, [b for b in batches])

        return {
            "course_id": str(course.pk),
            "course_code": course.code,
            "course_title": course.title,
            "field_of_engineering": course.field_of_engineering,
            "duration_months": course.duration_months,
            "assignment_ids": [str(r.pk) for r in explicit_rows],
            "branch_names": sorted({b.branch.name for b in batches}),
            "batches": batch_summaries,
            "schedule": schedule,
            "students": students,
            "student_count": len(students),
            "has_course_assignment": bool(explicit_rows),
            "attendance": TeacherDashboardService._attendance_summary(actor, course, batch_ids),
        }

    @staticmethod
    def _batch_summary(actor, batch) -> dict:
        from academics.services.batch_service import BatchService

        enrolled = (
            active(CourseEnrolment).filter(batch=batch, status="ACTIVE").count()
        )
        try:
            progress = BatchService.batch_progress(actor, str(batch.pk))
            attendance_pct = progress["attendance"]["overall_pct"]
            syllabus_pct = progress["lectures"]["syllabus_progress_pct"]
            pending_evals = progress["assignments"]["pending_evaluations"]
        except Exception:
            attendance_pct = None
            syllabus_pct = None
            pending_evals = 0
        return {
            "id": str(batch.pk),
            "name": batch.name,
            "code": batch.code,
            "branch_name": batch.branch.name,
            "enrolled_count": enrolled,
            "max_capacity": batch.max_capacity,
            "start_date": batch.start_date.isoformat() if batch.start_date else None,
            "end_date": batch.end_date.isoformat() if batch.end_date else None,
            "attendance_pct": attendance_pct,
            "syllabus_progress_pct": syllabus_pct,
            "pending_evaluations": pending_evals,
        }

    @staticmethod
    def _schedule(actor, batches) -> list:
        batch_ids = [b.pk for b in batches]
        if not batch_ids:
            return []
        slots = (
            active(Timetable)
            .filter(batch_id__in=batch_ids)
            .select_related("batch", "batch__branch", "subject", "teacher")
            .order_by("day_of_week", "start_time")
        )
        return [
            {
                "id": str(s.pk),
                "batch_id": str(s.batch_id),
                "batch_name": s.batch.name,
                "course_title": s.batch.course.title if s.batch.course_id else None,
                "branch_name": s.batch.branch.name if s.batch.branch_id else None,
                "subject": s.subject.title if s.subject_id else None,
                "subject_id": str(s.subject_id) if s.subject_id else None,
                "day_of_week": s.day_of_week,
                "start_time": s.start_time.strftime("%H:%M") if s.start_time else None,
                "end_time": s.end_time.strftime("%H:%M") if s.end_time else None,
                "room_number": s.room_number,
                "teacher_name": s.teacher.get_full_name() if s.teacher_id else None,
                "is_own_slot": s.teacher_id == actor.pk,
            }
            for s in slots
        ]

    @staticmethod
    def _attendance_summary(actor, course, batch_ids) -> dict:
        if not batch_ids:
            return {"overall_pct": None, "low_attendance_count": 0, "threshold": _LOW_ATTENDANCE}
        qs = active(Attendance).filter(
            lecture__timetable__batch_id__in=batch_ids,
            lecture__timetable__batch__course_id=course.pk,
            lecture__is_deleted=False,
            lecture__timetable__is_deleted=False,
        )
        totals = qs.aggregate(
            total=Count("id"),
            present=Count("id", filter=Q(status__in=["PRESENT", "LATE"])),
            excused=Count("id", filter=Q(status="EXCUSED")),
        )
        total = totals["total"] or 0
        excused = totals["excused"] or 0
        countable = total - excused
        pct = round(((totals["present"] or 0) / countable) * 100, 2) if countable else None
        low = (
            qs.values("student_id").annotate(
                total=Count("id"),
                present=Count("id", filter=Q(status__in=["PRESENT", "LATE"])),
                excused=Count("id", filter=Q(status="EXCUSED")),
            )
        )
        low_count = 0
        for row in low:
            countable = row["total"] - row["excused"]
            p = round((row["present"] / countable) * 100, 2) if countable else None
            if p is not None and p < _LOW_ATTENDANCE:
                low_count += 1
        return {"overall_pct": pct, "low_attendance_count": low_count, "threshold": _LOW_ATTENDANCE}

    @staticmethod
    def _notices(actor) -> list:
        try:
            from communications.models import Announcement

            qs = active(Announcement).filter(is_deleted=False).select_related("published_by")
            scope = Q(branch__isnull=True) | Q(target_role__isnull=True) | Q(target_role__code=Role.TEACHER)
            if actor.branch_id:
                scope &= Q(branch__isnull=True) | Q(branch_id=actor.branch_id)
            return [
                {
                    "id": str(a.pk),
                    "title": a.title,
                    "content": a.content,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                    "published_by": a.published_by.get_full_name() if a.published_by_id else None,
                }
                for a in qs.filter(scope).order_by("-created_at")[:20]
            ]
        except Exception:
            return []

    @staticmethod
    def _notifications(actor) -> list:
        try:
            from communications.models import Notification

            qs = (
                active(Notification)
                .filter(recipient_id=actor.pk, is_deleted=False)
                .order_by("-created_at")[:20]
            )
            return [
                {
                    "id": str(n.pk), "title": n.title, "message": n.message,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in qs
            ]
        except Exception:
            return []

    @staticmethod
    def _upcoming_activities(actor, batches) -> list:
        from django.utils import timezone

        today = timezone.localdate()
        batch_ids = [b.pk for b in batches]
        items = []
        if batch_ids:
            lectures = (
                active(Lecture)
                .filter(
                    timetable__batch_id__in=batch_ids,
                    timetable__is_deleted=False,
                    date__gte=today, status="SCHEDULED",
                )
                .select_related("timetable", "timetable__batch", "timetable__subject")
                .order_by("date", "timetable__start_time")[:20]
            )
            for l in lectures:
                items.append({
                    "type": "LECTURE", "id": str(l.pk), "title": l.topic,
                    "date": l.date.isoformat(),
                    "batch_name": l.timetable.batch.name,
                    "subject": l.timetable.subject.title if l.timetable.subject_id else None,
                    "status": l.status,
                })
            try:
                from assignments_exams.models import Exam

                exams = (
                    active(Exam)
                    .filter(batch_id__in=batch_ids, exam_date__gte=today)
                    .order_by("exam_date")[:20]
                )
                for e in exams:
                    items.append({
                        "type": "EXAM", "id": str(e.pk), "title": e.title,
                        "date": e.exam_date.isoformat() if e.exam_date else None,
                        "batch_name": None, "subject": None, "status": None,
                    })
            except Exception:
                pass
        items.sort(key=lambda i: i.get("date") or "")
        return items[:20]

    @staticmethod
    def _tasks(actor, batches) -> list:
        """Actionable items: submissions awaiting grading in the teacher's batches."""
        batch_ids = [b.pk for b in batches]
        if not batch_ids:
            return []
        try:
            from assignments_exams.models import Assignment, Submission

            assignments = active(Assignment).filter(batch_id__in=batch_ids)
            a_ids = list(assignments.values_list("pk", flat=True))
            if not a_ids:
                return []
            pending = (
                active(Submission)
                .filter(assignment_id__in=a_ids, marks_obtained__isnull=True)
                .select_related("assignment", "student")
                .order_by("-submitted_at")[:50]
            )
            return [
                {
                    "type": "GRADE_SUBMISSION",
                    "assignment_id": str(s.assignment_id),
                    "assignment_title": s.assignment.title,
                    "student": s.student.get_full_name() or s.student.username,
                    "student_id": str(s.student_id),
                    "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                }
                for s in pending
            ]
        except Exception:
            return []

    @staticmethod
    def _today_code() -> str:
        from django.utils import timezone

        return timezone.localtime().strftime("%A").upper()

    @staticmethod
    def _reg_no(user) -> str | None:
        try:
            return user.student_profile.reg_no
        except Exception:
            return None
