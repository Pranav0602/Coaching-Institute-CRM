"""
Routes for the ``academics`` app, mounted at ``/api/v1/academics/``.

The router generates the standard list/detail routes plus the ``@action`` endpoints declared
on each viewset:

    courses/summary/                        catalogue counts
    batches/summary/                        roster + schedule counts per cohort
    batches/{id}/roster/                    active students in a batch
    batches/{id}/attendance-report/         per-student percentages for a batch
    enrolments/{id}/transfer/               move a live enrolment to another cohort
    enrolments/{id}/set-status/             complete or drop an enrolment
    timetables/weekly/                      schedule grouped by weekday
    timetables/check-availability/          dry-run conflict check (writes nothing)
    timetables/{id}/generate-lectures/      materialise recurring slot into dated lectures
    lectures/{id}/register/                 marking screen roster with current marks
    lectures/{id}/bulk-attendance/          mark a whole class in one transaction
    lectures/{id}/cancel/                   cancel without deleting
    attendances/summary/                    one student's percentage (or a parent's children)
    attendances/batch-report/               per-student percentages for a cohort
    attendances/low-attendance/             students below the threshold

``POST /attendances/`` is intentionally absent - attendance is created through
``lectures/{id}/bulk-attendance/`` so the teacher/branch checks cannot be bypassed.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from academics.views import (
    AttendanceViewSet,
    BatchViewSet,
    CourseEnrolmentViewSet,
    CourseViewSet,
    LectureViewSet,
    StudyMaterialViewSet,
    SubjectViewSet,
    TimetableViewSet,
)

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'batches', BatchViewSet, basename='batch')
router.register(r'enrolments', CourseEnrolmentViewSet, basename='enrolment')
router.register(r'timetables', TimetableViewSet, basename='timetable')
router.register(r'lectures', LectureViewSet, basename='lecture')
router.register(r'attendances', AttendanceViewSet, basename='attendance')
router.register(r'study-materials', StudyMaterialViewSet, basename='studymaterial')

urlpatterns = [
    path('', include(router.urls)),
]
