"""
Teaching endpoints: the weekly schedule, the sessions generated from it, and study material.

Every ``get_queryset`` here delegates to a service ``filter_*`` helper. That is deliberate and
load-bearing: ``get_object()`` inside a custom action goes through ``get_queryset()`` too, so
routing reads through the service means the bulk-attendance and cancel actions inherit the
same branch and teacher scoping as the list endpoint. The previous ``LectureViewSet`` had no
``get_queryset`` at all, which let any authenticated user mark attendance on any lecture in
any branch.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import Lecture, StudyMaterial, Timetable
from academics.serializers import (
    AttendanceSerializer,
    BulkAttendanceSerializer,
    LectureGenerateSerializer,
    LectureSerializer,
    StudyMaterialSerializer,
    TimetableAvailabilitySerializer,
    TimetableSerializer,
)
from academics.services import (
    AttendanceService,
    LectureService,
    StudyMaterialService,
    TimetableService,
)
from institute_crm.viewsets import ServiceBackedViewSet, bool_param


class TimetableViewSet(ServiceBackedViewSet):
    """The recurring weekly schedule."""

    serializer_class = TimetableSerializer
    queryset = Timetable.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return TimetableService.filter_slots(
            self.request.user,
            teacher_id=params.get("teacher_id"),
            batch_id=params.get("batch_id"),
            subject_id=params.get("subject_id"),
            day_of_week=params.get("day_of_week"),
        )

    def service_create(self, data):
        return TimetableService.create_slot(actor=self.actor, data=data, ip_address=self.ip)

    def service_update(self, instance, data, *, partial):
        return TimetableService.update_slot(
            actor=self.actor, slot=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        TimetableService.soft_delete_slot(
            actor=self.actor, slot=instance, ip_address=self.ip
        )

    @action(detail=False, methods=["get"], url_path="weekly")
    def weekly(self, request):
        """The schedule grouped by weekday, for the week-view grid."""
        params = request.query_params
        grid = TimetableService.weekly_grid(
            request.user,
            teacher_id=params.get("teacher_id"),
            batch_id=params.get("batch_id"),
            subject_id=params.get("subject_id"),
        )
        context = self.get_serializer_context()
        return Response(
            {
                day: TimetableSerializer(slots, many=True, context=context).data
                for day, slots in grid.items()
            }
        )

    @action(detail=False, methods=["post"], url_path="check-availability")
    def check_availability(self, request):
        """Dry run: report what a proposed slot would clash with, without writing anything."""
        serializer = TimetableAvailabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            TimetableService.check_availability(
                request.user,
                data=serializer.validated_data,
                exclude_pk=request.data.get("exclude_id") or None,
            )
        )

    @action(detail=True, methods=["post"], url_path="generate-lectures")
    def generate_lectures(self, request, pk=None):
        """Materialise this recurring slot into dated lectures. Safe to re-run."""
        slot = self.get_object()
        serializer = LectureGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        created = LectureService.generate_from_timetable(
            actor=request.user,
            slot=slot,
            date_from=serializer.validated_data["date_from"],
            date_to=serializer.validated_data["date_to"],
            topic_template=serializer.validated_data.get("topic_template") or "{subject}",
            ip_address=self.ip,
        )
        return Response(
            {
                "created": len(created),
                "lectures": LectureSerializer(
                    created, many=True, context=self.get_serializer_context()
                ).data,
            }
        )


class LectureViewSet(ServiceBackedViewSet):
    """Individual dated sessions, and the attendance recorded against them."""

    serializer_class = LectureSerializer
    queryset = Lecture.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return LectureService.filter_lectures(
            self.request.user,
            timetable_id=params.get("timetable_id"),
            batch_id=params.get("batch_id"),
            status=params.get("status"),
            date_from=params.get("date_from") or None,
            date_to=params.get("date_to") or None,
        )

    def service_create(self, data):
        return LectureService.create_lecture(actor=self.actor, data=data, ip_address=self.ip)

    def service_update(self, instance, data, *, partial):
        return LectureService.update_lecture(
            actor=self.actor, lecture=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        LectureService.soft_delete_lecture(
            actor=self.actor, lecture=instance, ip_address=self.ip
        )

    @action(detail=True, methods=["get"], url_path="register")
    def register(self, request, pk=None):
        """One row per actively enrolled student, with their current mark if any.

        The marking screen renders this directly - it does not have to reconcile the roster
        against the existing attendance rows itself.
        """
        lecture = self.get_object()
        return Response(
            {
                "lecture_id": str(lecture.pk),
                "lecture_status": lecture.status,
                "date": lecture.date,
                "batch": lecture.timetable.batch.name,
                "subject": lecture.timetable.subject.title,
                "students": AttendanceService.register_for_lecture(request.user, lecture),
            }
        )

    @action(detail=True, methods=["post"], url_path="bulk-attendance")
    def bulk_attendance(self, request, pk=None):
        """Mark a whole class in one transaction."""
        lecture = self.get_object()
        serializer = BulkAttendanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = AttendanceService.mark_bulk_attendance(
            lecture=lecture,
            records=serializer.validated_data["records"],
            actor=request.user,
            complete_lecture=bool_param(
                request.data.get("complete_lecture"),
                default=serializer.validated_data.get("complete_lecture", True),
            ),
            ip_address=self.ip,
        )

        records = result.pop("records", [])
        result["records"] = AttendanceSerializer(
            records, many=True, context=self.get_serializer_context()
        ).data
        return Response(result)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """Cancel a session without destroying it, preserving the schedule's history."""
        lecture = self.get_object()
        updated = LectureService.cancel_lecture(
            actor=request.user,
            lecture=lecture,
            reason=(request.data.get("reason") or "").strip() or None,
            ip_address=self.ip,
        )
        return self.respond(updated)


class StudyMaterialViewSet(ServiceBackedViewSet):
    """Course-wide and per-batch resources."""

    serializer_class = StudyMaterialSerializer
    queryset = StudyMaterial.objects.none()

    def get_queryset(self):
        params = self.request.query_params
        return StudyMaterialService.filter_materials(
            self.request.user,
            subject_id=params.get("subject_id"),
            batch_id=params.get("batch_id"),
            material_type=params.get("material_type"),
            search=params.get("search"),
        )

    def service_create(self, data):
        return StudyMaterialService.publish_material(
            actor=self.actor, data=data, ip_address=self.ip
        )

    def service_update(self, instance, data, *, partial):
        return StudyMaterialService.update_material(
            actor=self.actor, material=instance, data=data, ip_address=self.ip
        )

    def service_delete(self, instance):
        StudyMaterialService.soft_delete_material(
            actor=self.actor, material=instance, ip_address=self.ip
        )
