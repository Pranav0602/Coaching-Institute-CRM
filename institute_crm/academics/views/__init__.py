"""
HTTP layer for the ``academics`` app.

Split by primary audience rather than by model: ``admin_views`` holds the catalogue and
cohort management, ``teacher_views`` the schedule and the sessions run from it, and
``student_views`` the attendance a student or parent reads. Access control does not come from
this grouping - it comes from the services, so a teacher hitting an "admin" endpoint gets the
teacher's scoped result rather than a 403 on the wrong axis.
"""
from academics.views.admin_views import (
    CourseViewSet,
    SubjectViewSet,
    BatchViewSet,
    CourseEnrolmentViewSet,
)
from academics.views.teacher_views import (
    TimetableViewSet,
    LectureViewSet,
    StudyMaterialViewSet,
)
from academics.views.student_views import (
    AttendanceViewSet,
)

__all__ = [
    "CourseViewSet",
    "SubjectViewSet",
    "BatchViewSet",
    "CourseEnrolmentViewSet",
    "TimetableViewSet",
    "LectureViewSet",
    "StudyMaterialViewSet",
    "AttendanceViewSet",
]
