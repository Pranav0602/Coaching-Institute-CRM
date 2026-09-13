"""
Serialisers for the ``academics`` app.

These shape data in and out. They do not enforce domain rules, and they do not create,
update or delete anything - that belongs to ``academics.services``. Cross-field rules that
used to live here (subject-belongs-to-batch-course, teacher-must-hold-the-Teacher-role,
branch assignment policy) moved into the services, because they are tenancy and
authorisation decisions that must hold for *every* caller, including management commands and
future RAG tooling that never passes through a serialiser.

What is left here is deliberately narrow: field selection, read-only display names, and the
kind of shape validation that a client can fix by changing its request.
"""
from rest_framework import serializers

from academics.models import (
    Attendance,
    Batch,
    Course,
    CourseEnrolment,
    Lecture,
    StudyMaterial,
    Subject,
    Timetable,
)
from accounts.models import User


def _annotated(instance, attribute):
    """Read an annotation if the queryset supplied one, otherwise ``None``.

    Lets one serialiser serve both the plain list endpoint and the annotated summary
    endpoint without a second class or an N+1 per row.
    """
    value = getattr(instance, attribute, None)
    return value


class SubjectSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Subject
        fields = ["id", "course", "course_title", "code", "title", "description"]


class CourseSerializer(serializers.ModelSerializer):
    # Populated from a filtered Prefetch in CourseService so soft-deleted subjects do not
    # reappear nested inside their course.
    subjects = SubjectSerializer(many=True, read_only=True)
    subject_count = serializers.SerializerMethodField()
    batch_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "code",
            "title",
            "description",
            "duration_months",
            "total_fee",
            "field_of_engineering",
            "subjects",
            "subject_count",
            "batch_count",
        ]

    def get_subject_count(self, obj):
        return _annotated(obj, "subject_count")

    def get_batch_count(self, obj):
        return _annotated(obj, "batch_count")


class BatchSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    enrolled_count = serializers.SerializerMethodField()
    seats_available = serializers.SerializerMethodField()
    teachers = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(is_deleted=False, is_active=True),
        required=False,
    )
    teacher_details = serializers.SerializerMethodField()
    teacher_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, write_only=True
    )

    class Meta:
        model = Batch
        fields = [
            "id",
            "course",
            "course_title",
            "branch",
            "branch_name",
            "code",
            "name",
            "start_date",
            "end_date",
            "max_capacity",
            "enrolled_count",
            "seats_available",
            "teachers",
            "teacher_details",
            "teacher_ids",
        ]
        extra_kwargs = {
            # BatchService.create_batch imposes the caller's branch; a super admin must name
            # one explicitly. Either way the request body is not the authority.
            "branch": {"required": False},
        }

    def get_enrolled_count(self, obj):
        return _annotated(obj, "enrolled_count")

    def get_seats_available(self, obj):
        enrolled = _annotated(obj, "enrolled_count")
        if enrolled is None:
            return None
        return max(obj.max_capacity - enrolled, 0)

    def get_teacher_details(self, obj):
        teachers = getattr(obj, "teachers", None)
        if teachers is None:
            return []
        try:
            qs = teachers.all()
        except Exception:
            qs = teachers
        details = []
        for teacher in qs:
            details.append(
                {
                    "id": str(teacher.pk),
                    "name": teacher.get_full_name() or teacher.username,
                    "email": teacher.email,
                }
            )
        return details

    def validate(self, attrs):
        # Merge `teachers` and `teacher_ids` aliases into `teacher_ids` for the service.
        teacher_ids = attrs.pop("teacher_ids", None)
        teachers = attrs.pop("teachers", None)
        if teacher_ids is not None:
            attrs["teacher_ids"] = [str(t) for t in teacher_ids]
        elif teachers is not None:
            attrs["teacher_ids"] = [str(getattr(t, "pk", t)) for t in teachers]
        return attrs


class CourseEnrolmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    student_username = serializers.CharField(source="student.username", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    batch_name = serializers.CharField(source="batch.name", read_only=True)
    branch_name = serializers.CharField(source="batch.branch.name", read_only=True)

    class Meta:
        model = CourseEnrolment
        fields = [
            "id",
            "student",
            "student_name",
            "student_username",
            "course",
            "course_title",
            "batch",
            "batch_name",
            "branch_name",
            "enrolled_at",
            "status",
        ]
        read_only_fields = ["enrolled_at"]
        extra_kwargs = {
            # Defaulted from the batch by EnrolmentService when omitted.
            "course": {"required": False},
        }


class EnrolmentTransferSerializer(serializers.Serializer):
    """Payload for ``POST /enrolments/{id}/transfer/``."""

    batch = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.filter(is_deleted=False))


class EnrolmentStatusSerializer(serializers.Serializer):
    """Payload for ``POST /enrolments/{id}/set-status/``."""

    status = serializers.ChoiceField(choices=CourseEnrolment.STATUS_CHOICES)


class TimetableSerializer(serializers.ModelSerializer):
    batch_name = serializers.CharField(source="batch.name", read_only=True)
    subject_title = serializers.CharField(source="subject.title", read_only=True)
    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)
    branch_name = serializers.CharField(source="batch.branch.name", read_only=True)

    class Meta:
        model = Timetable
        fields = [
            "id",
            "batch",
            "batch_name",
            "subject",
            "subject_title",
            "teacher",
            "teacher_name",
            "branch_name",
            "day_of_week",
            "start_time",
            "end_time",
            "room_number",
        ]


class TimetableAvailabilitySerializer(serializers.Serializer):
    """Dry-run payload for the "is this slot free?" check.

    Mirrors :class:`TimetableSerializer`'s writable fields but validates nothing beyond
    types - the point is to *report* conflicts, not reject the request.
    """

    batch = serializers.PrimaryKeyRelatedField(queryset=Batch.objects.filter(is_deleted=False))
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_deleted=False, is_active=True),
        required=False,
        allow_null=True,
    )
    day_of_week = serializers.ChoiceField(choices=Timetable.DAY_CHOICES)
    start_time = serializers.TimeField()
    end_time = serializers.TimeField()
    room_number = serializers.CharField(required=False, allow_blank=True)


class LectureSerializer(serializers.ModelSerializer):
    batch = serializers.PrimaryKeyRelatedField(source="timetable.batch", read_only=True)
    batch_name = serializers.CharField(source="timetable.batch.name", read_only=True)
    subject_title = serializers.CharField(source="timetable.subject.title", read_only=True)
    teacher_name = serializers.CharField(
        source="timetable.teacher.get_full_name", read_only=True
    )
    day_of_week = serializers.CharField(source="timetable.day_of_week", read_only=True)
    conducted_by_name = serializers.CharField(
        source="conducted_by.get_full_name", read_only=True
    )

    class Meta:
        model = Lecture
        fields = [
            "id",
            "timetable",
            "batch",
            "batch_name",
            "subject_title",
            "teacher_name",
            "day_of_week",
            "date",
            "topic",
            "status",
            "conducted_by",
            "conducted_by_name",
        ]
        extra_kwargs = {"conducted_by": {"required": False}}


class LectureGenerateSerializer(serializers.Serializer):
    """Payload for ``POST /timetables/{id}/generate-lectures/``."""

    date_from = serializers.DateField()
    date_to = serializers.DateField()
    topic_template = serializers.CharField(required=False, default="{subject}")


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.get_full_name", read_only=True)
    lecture_date = serializers.DateField(source="lecture.date", read_only=True)
    subject_title = serializers.CharField(
        source="lecture.timetable.subject.title", read_only=True
    )

    class Meta:
        model = Attendance
        fields = [
            "id",
            "lecture",
            "lecture_date",
            "subject_title",
            "student",
            "student_name",
            "status",
            "remarks",
        ]


class AttendanceAmendSerializer(serializers.Serializer):
    """Partial correction of a single mark."""

    status = serializers.ChoiceField(choices=Attendance.STATUS_CHOICES, required=False)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=255)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("Provide a status or a remark to change.")
        return attrs


class BulkAttendanceEntrySerializer(serializers.Serializer):
    student_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=Attendance.STATUS_CHOICES, required=False, default="PRESENT"
    )
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=255)


class BulkAttendanceSerializer(serializers.Serializer):
    """Shape check for the bulk-marking payload.

    ``AttendanceService`` re-validates and cross-checks enrolment - this exists so an
    obviously malformed body fails fast with per-index errors instead of reaching the
    service. Belt and braces is warranted here: the previous version accepted the raw list
    and turned a missing ``student_id`` into a 500.
    """

    records = serializers.ListField(
        child=BulkAttendanceEntrySerializer(), allow_empty=False, max_length=500
    )
    complete_lecture = serializers.BooleanField(required=False, default=True)


class StudyMaterialSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(source="subject.title", read_only=True)
    course_title = serializers.CharField(source="subject.course.title", read_only=True)
    batch_name = serializers.CharField(source="batch.name", read_only=True)
    uploader_name = serializers.CharField(
        source="uploaded_by.get_full_name", read_only=True
    )

    class Meta:
        model = StudyMaterial
        fields = [
            "id",
            "subject",
            "subject_title",
            "course_title",
            "batch",
            "batch_name",
            "title",
            "material_type",
            "file_url",
            "external_link",
            "uploaded_by",
            "uploader_name",
            "created_at",
        ]
        # Authorship and timestamps are set by the service and the database, not the client.
        read_only_fields = ["uploaded_by", "created_at"]
