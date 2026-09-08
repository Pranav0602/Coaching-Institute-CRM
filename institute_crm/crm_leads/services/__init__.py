"""
Business logic for the ``crm_leads`` app.

Layering contract, identical across every app in this project (``accounts`` is the reference
implementation):

1. **One ``XxxService`` class per concern, containing only ``@staticmethod``s.** There is no
   instance state to hold, and a flat namespace keeps call sites readable
   (``LeadService.convert_lead_to_student(...)``).
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

Why this app needed the most attention
--------------------------------------
A lead row holds a prospective student's name, email and phone before any relationship
exists - it is the most sensitive personal data in the system and the least protected by
convention. The previous ``LeadViewSet`` applied ``stage``, ``branch_id`` and ``course_id``
as optional filters and applied *no* branch scoping at all, so any authenticated account -
including a STUDENT or a PARENT - could enumerate every prospect in every branch. The four
sibling viewsets (follow-ups, counselling notes, admissions, visitors) had no scoping
whatsoever.

Scoping now lives in :meth:`LeadService.visible_leads` and the ``visible_*`` helper of each
sibling service, and every ``get_queryset`` in the HTTP layer routes through one of them. So
list, retrieve and every ``get_object()`` inside a custom action share a single
implementation, and roles with no business reason to read the pipeline get an empty
queryset rather than the whole table.

Module map:

``lead_service``     - :class:`LeadService` (pipeline, assignment, bulk import, public
                       enquiry, and the atomic lead-to-student conversion)
``counselor_service`` - :class:`FollowUpService`, :class:`CounsellingNoteService`,
                       :class:`VisitorService`, :class:`AdmissionService`,
                       :class:`CounselorService` (pipeline and performance analytics)
"""
from crm_leads.services.lead_service import LeadService

__all__ = [
    "LeadService",
]

