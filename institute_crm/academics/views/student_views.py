"""
Student-facing attendance endpoints.

Two things are different here from a stock ``ModelViewSet``, and both were security holes in
the original:

* **Reads are scoped, not global.** ``AttendanceService.visible_attendance`` narrows a student
  to their own rows and a parent to their children's, so no query parameter can widen the
  result set.
* **Creation is not exposed at all.** Attendance is recorded through
  ``POST /lectures/{id}/bulk-attendance/`` by a teacher or admin. ``service_create`` is left
  unimplemented, so ``POST`` here returns 405 rather than letting a student insert a row.
  ``PATCH`` maps to :meth:`AttendanceService.amend_attendance`, which re-checks the actor -
  previously unrestricted ``PATCH`` let a student flip their own record to PRESENT.
"""
from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response

from academics.models import Attendance
from academics.serializers import AttendanceAmendSerializer, AttendanceSerializer
from academics.services import LOW_ATTENDANCE_THRESHOLD, AttendanceService
from accounts.models import Role
from institute_crm.exceptions import ValidationFailed
from institute_crm.scoping import child_student_user_ids
from institute_crm.viewsets import ServiceBackedViewSet


def _float_param(raw, default):
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


class AttendanceViewSet(ServiceBackedViewSet):
    serializer_class = AttendanceSerializer
    read_serializer_class = AttendanceSerializer
    queryset = Attendance.objects.none()
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        params = self.request.query_params
        return AttendanceService.filter_attendance(
            self.request.user,
            lecture_id=params.get("lecture_id"),
            student_id=params.get("student_id"),
            batch_id=params.get("batch_id"),
            status=params.get("status"),
            date_from=params.get("date_from") or None,
            date_to=params.get("date_to") or None,
        )

    def get_serializer_class(self):
        # Amendments accept only the two correctable fields; everything else about a mark is
        # derived from the lecture it belongs to.
        if self.action in ("update", "partial_update"):
            return AttendanceAmendSerializer
        return AttendanceSerializer

    def service_update(self, instance, data, *, partial):
        return AttendanceService.amend_attendance(
            actor=self.actor,
            attendance=instance,
            status=data.get("status"),
            remarks=data.get("remarks"),
            ip_address=self.ip,
        )

    def service_delete(self, instance):
        AttendanceService.soft_delete_attendance(
            actor=self.actor, attendance=instance, ip_address=self.ip
        )

    # ------------------------------------------------------------- reporting

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        """Attendance percentage for one student, or for each child of a parent.

        Resolving "whose summary" is a presentation concern, so it happens here. It is not a
        security boundary: the underlying queryset is scoped, so a student who passes someone
        else's ``student_id`` gets zeroes rather than another student's record.
        """
        student_id = request.query_params.get("student_id")
        batch_id = request.query_params.get("batch_id")
        role = getattr(request.user, "role_code", None)

        if not student_id and role == Role.STUDENT:
            student_id = str(request.user.pk)

        if not student_id and role == Role.PARENT:
            return Response(
                [
                    AttendanceService.student_summary(
                        request.user, student_id=child_id, batch_id=batch_id
                    )
                    for child_id in child_student_user_ids(request.user)
                ]
            )

        if not student_id:
            raise ValidationFailed(
                "Specify which student to summarise.",
                field_errors={"student_id": ["This query parameter is required."]},
            )

        return Response(
            AttendanceService.student_summary(
                request.user, student_id=student_id, batch_id=batch_id
            )
        )

    @action(detail=False, methods=["get"], url_path="batch-report")
    def batch_report(self, request):
        """Per-student percentages for a whole cohort, worst first."""
        batch_id = request.query_params.get("batch_id")
        if not batch_id:
            raise ValidationFailed(
                "Specify which batch to report on.",
                field_errors={"batch_id": ["This query parameter is required."]},
            )
        return Response(
            AttendanceService.batch_report(
                request.user,
                batch_id=batch_id,
                date_from=request.query_params.get("date_from") or None,
                date_to=request.query_params.get("date_to") or None,
            )
        )

    @action(detail=False, methods=["get"], url_path="low-attendance")
    def low_attendance(self, request):
        """Students below the threshold - the follow-up list for admins and counsellors."""
        threshold = _float_param(
            request.query_params.get("threshold"), LOW_ATTENDANCE_THRESHOLD
        )
        rows = AttendanceService.low_attendance_students(
            request.user,
            batch_id=request.query_params.get("batch_id"),
            threshold=threshold,
        )
        return Response({"threshold": threshold, "count": len(rows), "students": rows})
