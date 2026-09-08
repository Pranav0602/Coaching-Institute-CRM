"""
Administrative endpoints for the shared catalogue and cohorts.

Thin by design: each handler validates, calls one service method, and serialises the result.
All scoping, permission and business rules live in ``academics.services``, so they hold for
management commands and background jobs too - not just for requests that arrive here.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import Batch, Course, CourseEnrolment, Subject
from academics.serializers import (
    BatchSerializer,
    CourseEnrolmentSerializer,
    CourseSerializer,
    EnrolmentStatusSerializer,
    EnrolmentTransferSerializer,
    SubjectSerializer,
)
from academics.services import (
    BatchService,
    CourseService,
    EnrolmentService,
    SubjectService,
)
from institute_crm.viewsets import ServiceBackedViewSet


class CourseViewSet(ServiceBackedViewSet):
    """The institute-wide course catalogue. Readable by all staff, writable by admins."""

    serializer_class = CourseSerializer
    queryset = Course.objects.none()  # documentation only; get_queryset is authoritative

    def get_queryset(self):
        return CourseService.filter_courses(
            self.request.user,
            search=self.request.query_params.get("search"),
            field_of_engineering=self.request.query_params.get("field_of_engineering") or self.request.query_params.get("field"),
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
