"""
Course and subject catalogue.

Courses and subjects are institute-wide: they carry no branch FK, so a course defined once
is offered by every branch. That makes them *catalogue* data rather than tenant data, and
the rules are correspondingly different from the rest of this app - reads are open to any
authenticated user, but writes are restricted to administrators, because changing
``total_fee`` or deleting a subject reverberates through every branch's enrolments and
invoices at once.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Q

from academics.models import Batch, Course, CourseEnrolment, Subject
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import assert_role, is_global
from institute_crm.utils import active

#: Roles allowed to edit the shared catalogue.
CATALOGUE_EDITORS = Role.ADMIN_ROLES


class CourseService:
    """Catalogue reads and writes for :class:`academics.Course` and its subjects."""

    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_courses(actor: User):
        """The catalogue is shared, so every authenticated caller sees all of it."""
        return active(Course).prefetch_related(
            # Without the filtered Prefetch, a soft-deleted subject reappears nested inside
            # its course - the delete looks successful in the subjects endpoint and silently
            # fails in the courses endpoint.
            CourseService._subject_prefetch()
        ).order_by("title")

    @staticmethod
    def _subject_prefetch():
        from django.db.models import Prefetch

        return Prefetch(
            "subjects",
            queryset=active(Subject).order_by("code"),
        )

    @staticmethod
    def filter_courses(actor: User, *, search: str | None = None, field_of_engineering: str | None = None):
        queryset = CourseService.visible_courses(actor)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(code__icontains=search) | Q(field_of_engineering__icontains=search)
            )
        if field_of_engineering:
            queryset = queryset.filter(field_of_engineering=field_of_engineering)
        return queryset

    @staticmethod
    def get_course(course_id) -> Course:
        try:
            return active(Course).get(pk=course_id)
        except Course.DoesNotExist as exc:
            raise NotFoundError("Course not found.") from exc

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def create_course(*, actor: User, data: dict, ip_address: str | None = None) -> Course:
        assert_role(
            actor,
            CATALOGUE_EDITORS,
            message="Only administrators can add courses to the catalogue.",
        )
        CourseService._validate_fee(data.get("total_fee"))

        code = CourseService._normalise_code(data.get("code"))
        if active(Course).filter(code=code).exists():
            raise ConflictError(
                f"A course with code '{code}' already exists.", code="course_code_taken"
            )

        course = Course.objects.create(**{**data, "code": code})
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=course,
            changes={"code": course.code, "title": course.title},
            ip_address=ip_address,
        )
        return course

    @staticmethod
    @transaction.atomic
    def update_course(
        *, actor: User, course: Course, data: dict, ip_address: str | None = None
    ) -> Course:
        assert_role(
            actor,
            CATALOGUE_EDITORS,
            message="Only administrators can edit the course catalogue.",
        )
        if "total_fee" in data:
            CourseService._validate_fee(data["total_fee"])

        if "code" in data:
            code = CourseService._normalise_code(data["code"])
            if code != course.code:
                if active(Course).filter(code=code).exclude(pk=course.pk).exists():
                    raise ConflictError(
                        f"A course with code '{code}' already exists.",
                        code="course_code_taken",
                    )
                if not is_global(actor):
                    # The code appears on invoices and certificates already issued.
                    raise ConflictError(
                        "Course codes can only be changed by a super admin.",
                        code="course_code_locked",
                    )
            data = {**data, "code": code}

        changes = audit.diff_fields(course, data)
        for field, value in data.items():
            setattr(course, field, value)
        course.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=course,
            changes=changes,
            ip_address=ip_address,
        )
        return course

    @staticmethod
    @transaction.atomic
    def soft_delete_course(
        *, actor: User, course: Course, ip_address: str | None = None
    ) -> None:
        """Retire a course. Refused while live batches or enrolments still reference it."""
        assert_role(
            actor,
            CATALOGUE_EDITORS,
            message="Only administrators can retire courses.",
        )

        live_batches = active(Batch).filter(course=course).count()
        live_enrolments = active(CourseEnrolment).filter(course=course, status="ACTIVE").count()
        if live_batches or live_enrolments:
            raise ConflictError(
                "This course still has "
                f"{live_batches} active batch(es) and {live_enrolments} active enrolment(s). "
                "Close those first so student records stay consistent.",
                code="course_in_use",
            )

        course.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=course,
            changes={"soft_delete": True, "code": course.code},
            ip_address=ip_address,
        )

    # ------------------------------------------------------------- statistics

    @staticmethod
    def catalogue_summary(actor: User):
        """Per-course counts, used by the courses list and the admin dashboard."""
        return list(
            CourseService.visible_courses(actor)
            .annotate(
                subject_count=Count("subjects", filter=Q(subjects__is_deleted=False), distinct=True),
                batch_count=Count("batches", filter=Q(batches__is_deleted=False), distinct=True),
                enrolment_count=Count(
                    "enrolments",
                    filter=Q(enrolments__is_deleted=False, enrolments__status="ACTIVE"),
                    distinct=True,
                ),
            )
            .values("id", "code", "title", "total_fee", "field_of_engineering", "subject_count", "batch_count", "enrolment_count")
        )

    # --------------------------------------------------------------- internals

    @staticmethod
    def _normalise_code(code) -> str:
        if not code or not str(code).strip():
            raise ValidationFailed(
                "Course code is required.", field_errors={"code": ["This field is required."]}
            )
        return str(code).strip().upper().replace(" ", "_")

    @staticmethod
    def _validate_fee(total_fee) -> None:
        if total_fee is None:
            return
        if total_fee < 0:
            raise ValidationFailed(
                "Total fee cannot be negative.",
                field_errors={"total_fee": ["Enter a value of zero or more."]},
            )


class SubjectService:
    """Subjects always belong to exactly one course."""

    @staticmethod
    def visible_subjects(actor: User):
        return active(Subject).select_related("course").order_by("course__code", "code")

    @staticmethod
    def filter_subjects(actor: User, *, course_id=None, search: str | None = None):
        from institute_crm.scoping import narrow

        queryset = narrow(SubjectService.visible_subjects(actor), {"course_id": course_id})
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(code__icontains=search)
            )
        return queryset

    @staticmethod
    @transaction.atomic
    def create_subject(*, actor: User, data: dict, ip_address: str | None = None) -> Subject:
        assert_role(
            actor,
            CATALOGUE_EDITORS,
            message="Only administrators can add subjects.",
        )
        course = data.get("course")
        code = CourseService._normalise_code(data.get("code"))
        if active(Subject).filter(course=course, code=code).exists():
            raise ConflictError(
                f"Subject code '{code}' is already used in this course.",
                code="subject_code_taken",
            )

        subject = Subject.objects.create(**{**data, "code": code})
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=subject,
            changes={"code": subject.code, "course": str(subject.course_id)},
            ip_address=ip_address,
        )
        return subject

    @staticmethod
    @transaction.atomic
    def update_subject(
        *, actor: User, subject: Subject, data: dict, ip_address: str | None = None
    ) -> Subject:
        assert_role(
            actor, CATALOGUE_EDITORS, message="Only administrators can edit subjects."
        )

        target_course = data.get("course", subject.course)
        if "code" in data or "course" in data:
            code = CourseService._normalise_code(data.get("code", subject.code))
            clash = (
                active(Subject)
                .filter(course=target_course, code=code)
                .exclude(pk=subject.pk)
                .exists()
            )
            if clash:
                raise ConflictError(
                    f"Subject code '{code}' is already used in that course.",
                    code="subject_code_taken",
                )
            data = {**data, "code": code}

        changes = audit.diff_fields(subject, data)
        for field, value in data.items():
            setattr(subject, field, value)
        subject.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=subject,
            changes=changes,
            ip_address=ip_address,
        )
        return subject

    @staticmethod
    @transaction.atomic
    def soft_delete_subject(
        *, actor: User, subject: Subject, ip_address: str | None = None
    ) -> None:
        assert_role(
            actor, CATALOGUE_EDITORS, message="Only administrators can remove subjects."
        )

        # A scheduled session pointing at a deleted subject would render as a blank slot in
        # every timetable, so block the delete rather than produce broken schedules.
        from academics.models import Timetable

        scheduled = active(Timetable).filter(subject=subject).count()
        if scheduled:
            raise ConflictError(
                f"This subject is still on {scheduled} timetable slot(s). "
                "Remove those sessions first.",
                code="subject_in_use",
            )

        subject.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=subject,
            changes={"soft_delete": True, "code": subject.code},
            ip_address=ip_address,
        )
