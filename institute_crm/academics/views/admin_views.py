"""
Administrative endpoints for the shared catalogue and cohorts.

Thin by design: each handler validates, calls one service method, and serialises the result.
All scoping, permission and business rules live in ``academics.services``, so they hold for
management commands and background jobs too - not just for requests that arrive here.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import Batch, Course, CourseEnrolment, Subject, TeacherAssignment
from academics.serializers import (
    BatchSerializer,
    CourseEnrolmentSerializer,
    CourseSerializer,
    EnrolmentStatusSerializer,
    EnrolmentTransferSerializer,
    SubjectSerializer,
    TeacherAssignmentSerializer,
)
from academics.services import (
    BatchService,
    CourseService,
    EnrolmentService,
    SubjectService,
    TeacherAssignmentService,
)
from institute_crm.viewsets import ServiceBackedViewSet
from rest_framework import status
from rest_framework.response import Response


class CourseViewSet(ServiceBackedViewSet):
    """The institute-wide course catalogue. Readable by all staff, writable by admins."""

    serializer_class = CourseSerializer
    queryset = Course.objects.none()  # documentation only; get_queryset is authoritative

    def get_queryset(self):
        return CourseService.filter_courses(
            self.request.user,
            search=self.request.query_params.get("search"),
            field_of_engineering=self.request.query_params.get("field_of_engineering") or self.request.query_params.get("field"),
            branch_id=self.request.query_params.get("branch_id"),
        )

    def service_create(self, data):
        return CourseService.create_course(actor=self.actor, data=data, ip_address=self.ip)

    def service_update(self, instance, data, *, partial):
        return CourseService.update_course(
            actor=self.actor, course=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        CourseService.soft_delete_course(
            actor=self.actor, course=instance, ip_address=self.ip
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Subject, batch and enrolment counts per course, in one aggregate query."""
        return Response(CourseService.catalogue_summary(request.user))

    @action(detail=True, methods=["get"], url_path="syllabus")
    def syllabus(self, request, pk=None):
        """Direct syllabus document linked to a course by ID or code.

        Looks up STUDY_GUIDE / COURSE_CATALOGUE KnowledgeDocuments whose
        metadata_json.course_id matches the course id (or code), falling back
        to a title/code content match. Non-admin callers only see published docs.
        """
        from django.db.models import Q
        from rag.models import KnowledgeDocument
        from rag.serializers import KnowledgeDocumentSerializer
        from academics.models import Course as CourseModel
        from accounts.models import Role as RoleModel
        from institute_crm.utils import active

        course = None
        try:
            course = active(CourseModel).get(pk=pk)
        except Exception:
            try:
                course = active(CourseModel).get(code=str(pk).strip().upper().replace(" ", "_"))
            except Exception:
                try:
                    course = active(CourseModel).get(code__iexact=str(pk).strip())
                except Exception:
                    course = None
        if course is None:
            return Response({"detail": "Course not found."}, status=404)

        user = request.user
        role_code = getattr(getattr(user, "role", None), "code", None)
        is_admin = bool(
            getattr(user, "is_superuser", False)
            or role_code in [RoleModel.SUPER_ADMIN, RoleModel.BRANCH_ADMIN]
        )
        docs = KnowledgeDocument.objects.filter(
            is_deleted=False,
            category__in=["STUDY_GUIDE", "COURSE_CATALOGUE"],
        )
        if not is_admin:
            docs = docs.filter(is_published=True)
        doc = (
            docs.filter(
                Q(metadata_json__course_id=str(course.pk))
                | Q(metadata_json__courseId=str(course.pk))
                | Q(metadata_json__course_id=course.code)
            ).order_by("-updated_at").first()
            or docs.filter(
                Q(title__icontains=course.title) | Q(title__icontains=course.code)
            ).order_by("-updated_at").first()
        )
        if doc is None:
            return Response({"detail": "No syllabus uploaded for this course yet."}, status=404)
        return Response(KnowledgeDocumentSerializer(doc).data)


class SubjectViewSet(ServiceBackedViewSet):
    serializer_class = SubjectSerializer
    queryset = Subject.objects.none()

    def get_queryset(self):
        return SubjectService.filter_subjects(
            self.request.user,
            course_id=self.request.query_params.get("course_id"),
            search=self.request.query_params.get("search"),
        )

    def service_create(self, data):
        return SubjectService.create_subject(actor=self.actor, data=data, ip_address=self.ip)

    def service_update(self, instance, data, *, partial):
        return SubjectService.update_subject(
            actor=self.actor, subject=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        SubjectService.soft_delete_subject(
            actor=self.actor, subject=instance, ip_address=self.ip
        )


class BatchViewSet(ServiceBackedViewSet):
    """Cohorts. Branch-scoped for staff, teaching-scoped for teachers."""

    serializer_class = BatchSerializer
    queryset = Batch.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return BatchService.filter_batches(
            self.request.user,
            course_id=params.get("course_id"),
            branch_id=params.get("branch_id"),
            status=params.get("status"),
            search=params.get("search"),
        )

    def service_create(self, data):
        return BatchService.create_batch(actor=self.actor, data=data, ip_address=self.ip)

    def service_update(self, instance, data, *, partial):
        return BatchService.update_batch(
            actor=self.actor, batch=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        BatchService.soft_delete_batch(actor=self.actor, batch=instance, ip_address=self.ip)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Roster and schedule counts per batch, for the batches list and dashboard."""
        params = request.query_params
        return Response(
            BatchService.batch_summary(
                request.user,
                course_id=params.get("course_id"),
                branch_id=params.get("branch_id"),
                status=params.get("status"),
                search=params.get("search"),
            )
        )

    @action(detail=True, methods=["get"], url_path="roster")
    def roster(self, request, pk=None):
        """The active students in this batch, ordered for a printable register."""
        batch = self.get_object()
        enrolments = EnrolmentService.roster(request.user, batch.pk)
        return Response(
            CourseEnrolmentSerializer(
                enrolments, many=True, context=self.get_serializer_context()
            ).data
        )

    @action(detail=True, methods=["get"], url_path="attendance-report")
    def attendance_report(self, request, pk=None):
        from academics.services import AttendanceService

        batch = self.get_object()
        return Response(
            AttendanceService.batch_report(
                request.user,
                batch_id=batch.pk,
                date_from=request.query_params.get("date_from") or None,
                date_to=request.query_params.get("date_to") or None,
            )
        )

    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request, pk=None):
        """Full operational snapshot for one batch (timeline, faculty, 360 matrix)."""
        return Response(BatchService.batch_progress(request.user, str(pk)))

    @action(detail=False, methods=["get"], url_path="progress-summary")
    def progress_summary(self, request):
        """Lightweight progress summary across all visible batches."""
        params = request.query_params
        return Response(
            BatchService.batches_progress_overview(
                request.user,
                course_id=params.get("course_id"),
                branch_id=params.get("branch_id"),
                status=params.get("status"),
                search=params.get("search"),
            )
        )

    @action(detail=True, methods=["post"], url_path="assign-teachers")
    def assign_teachers(self, request, pk=None):
        """Replace the assigned-teacher roster for a batch."""
        batch = self.get_object()
        teacher_ids = (
            request.data.get("teacher_ids")
            if isinstance(request.data, dict)
            else None
        )
        if teacher_ids is None:
            teacher_ids = request.data.get("teachers", [])
        updated = BatchService.assign_teachers(
            actor=request.user,
            batch=batch,
            teacher_ids=list(teacher_ids or []),
            ip_address=self.ip,
        )
        return self.respond(updated)


class TeacherAssignmentViewSet(ServiceBackedViewSet):
    """Teacher <-> branch <-> course assignments. Branch-scoped; admin-only writes."""

    serializer_class = TeacherAssignmentSerializer
    queryset = TeacherAssignment.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return TeacherAssignmentService.list_assignments(
            self.request.user,
            teacher_id=params.get("teacher_id"),
            branch_id=params.get("branch_id"),
            course_id=params.get("course_id"),
        )

    def service_create(self, data):
        created = TeacherAssignmentService.assign(
            actor=self.actor,
            teacher=data.get("teacher"),
            branch=data.get("branch"),
            course=data.get("course"),
            course_ids=[str(c) for c in (data.get("course_ids") or [])],
            notes=data.get("notes"),
            ip_address=self.ip,
        )
        self._created_many = created
        return created[0]

    def respond(self, instance, *, status_code=200, many=False):
        # create() returns a single row but we may have created several.
        created = getattr(self, "_created_many", None)
        if created is not None and status_code == 201:
            return Response(
                self.get_read_serializer(created, many=True).data, status=201
            )
        return super().respond(instance, status_code=status_code, many=many)

    def service_update(self, instance, data, *, partial):
        return TeacherAssignmentService.update_assignment(
            actor=self.actor,
            assignment=instance,
            course=data.get("course"),
            branch=data.get("branch"),
            teacher=data.get("teacher"),
            notes=data.get("notes"),
            ip_address=self.ip,
        )

    def service_delete(self, instance):
        TeacherAssignmentService.remove_assignment(
            actor=self.actor, assignment=instance, ip_address=self.ip
        )

    @action(detail=False, methods=["get"], url_path="available-courses")
    def available_courses(self, request):
        """Courses offered at a branch, for the assignment picker."""
        from academics.serializers import CourseSerializer

        branch_id = request.query_params.get("branch_id")
        if not branch_id:
            return Response({"detail": "branch_id is required."}, status=400)
        from accounts.models import Branch

        branch = Branch.objects.filter(pk=branch_id, is_deleted=False).first()
        if branch is None:
            return Response({"detail": "Branch not found."}, status=404)
        # Branch scope: non-global callers can only inspect their own branch.
        from institute_crm.scoping import is_global

        if not is_global(request.user) and request.user.branch_id and str(request.user.branch_id) != str(branch.pk):
            return Response({"detail": "That branch is outside your scope."}, status=403)
        courses = TeacherAssignmentService.courses_for_branch(branch)
        return Response(CourseSerializer(courses, many=True).data)

    @action(detail=False, methods=["get"], url_path="my")
    def my(self, request):
        """The requesting teacher's own assignments (never anyone else's)."""
        assignments = TeacherAssignmentService.list_assignments(request.user)
        return Response(self.get_read_serializer(assignments, many=True).data)


class CourseEnrolmentViewSet(ServiceBackedViewSet):
    """Student enrolments. Every invariant is enforced in ``EnrolmentService``."""

    serializer_class = CourseEnrolmentSerializer
    queryset = CourseEnrolment.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return EnrolmentService.filter_enrolments(
            self.request.user,
            batch_id=params.get("batch_id"),
            course_id=params.get("course_id"),
            student_id=params.get("student_id"),
            status=params.get("status"),
            search=params.get("search"),
        )

    def service_create(self, data):
        return EnrolmentService.enrol_student(
            actor=self.actor, data=data, ip_address=self.ip
        )

    def service_update(self, instance, data, *, partial):
        return EnrolmentService.update_enrolment(
            actor=self.actor, enrolment=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        EnrolmentService.soft_delete_enrolment(
            actor=self.actor, enrolment=instance, ip_address=self.ip
        )

    @action(detail=True, methods=["post"], url_path="transfer")
    def transfer(self, request, pk=None):
        """Move a live enrolment to another cohort of the same course."""
        enrolment = self.get_object()
        serializer = EnrolmentTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = EnrolmentService.transfer_batch(
            actor=request.user,
            enrolment=enrolment,
            batch=serializer.validated_data["batch"],
            ip_address=self.ip,
        )
        return self.respond(updated)

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        """Complete or drop an enrolment. Only forward transitions are permitted."""
        enrolment = self.get_object()
        serializer = EnrolmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = EnrolmentService.set_status(
            actor=request.user,
            enrolment=enrolment,
            status=serializer.validated_data["status"],
            ip_address=self.ip,
        )
        return self.respond(updated)
