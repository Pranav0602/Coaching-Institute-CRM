"""
Business logic for the ``academics`` app.

Layering contract, identical across every app in this project (``accounts`` is the reference
implementation):

1. **One ``XxxService`` class per module, containing only ``@staticmethod``s.** There is no
   instance state to hold, and a flat namespace keeps call sites readable
   (``BatchService.create_batch(...)``).
2. **``@transaction.atomic`` goes directly below ``@staticmethod``** on any method that
   writes more than one row - including its audit entry, so a rolled-back change leaves no
   misleading log behind.
3. **Failures are ``institute_crm.exceptions.DomainError`` subclasses**, never DRF
   exceptions and never a bare ``ValueError``. Services know nothing about HTTP;
   ``institute_crm.renderers.custom_exception_handler`` maps them to status codes.
4. **The actor is passed explicitly as ``actor=``.** Services never receive ``request``, so
   they are callable from a management command, a Celery task or a test with no HTTP layer.
5. **Scoping is applied unconditionally and fails closed.** Use the helpers in
   ``institute_crm.scoping``; never let an optional filter parameter decide whether a
   tenancy check runs.
6. **Services return model instances**, not serialized dicts. Serialisation is the view's
   job, so the dependency points from presentation to domain and never back.

Module map:

``course_service``     - :class:`CourseService`, :class:`SubjectService` (shared catalogue)
``batch_service``      - :class:`BatchService` (cohorts, capacity, branch scoping)
``enrolment_service``  - :class:`EnrolmentService` (student <-> batch, status transitions)
``timetable_service``  - :class:`TimetableService` (weekly schedule, conflict detection)
``attendance_service`` - :class:`LectureService`, :class:`AttendanceService` (sessions, marks,
                         attendance reporting and low-attendance alerts)
``material_service``   - :class:`StudyMaterialService` (course-wide and per-batch resources)
"""
from academics.services.attendance_service import (
    LOW_ATTENDANCE_THRESHOLD,
    AttendanceService,
    LectureService,
)
from academics.services.batch_service import BatchService
from academics.services.course_service import CourseService, SubjectService
from academics.services.enrolment_service import EnrolmentService
from academics.services.material_service import StudyMaterialService
from academics.services.timetable_service import TimetableService

__all__ = [
    "AttendanceService",
    "BatchService",
    "CourseService",
    "EnrolmentService",
    "LOW_ATTENDANCE_THRESHOLD",
    "LectureService",
    "StudyMaterialService",
    "SubjectService",
    "TimetableService",
]
