"""
Study material distribution.

Materials hang off a subject and, optionally, a specific batch. That optional batch is what
makes the scoping non-obvious: a material with ``batch=None`` is course-wide and visible to
every branch running that course, while a material with a batch set is private to that
cohort. Both cases have to be expressed in one queryset, which is why
:meth:`StudyMaterialService.visible_materials` uses a ``Q`` union rather than a simple
branch filter.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Q

from academics.models import Batch, StudyMaterial, Subject
from accounts.models import Role, User
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import (
    assert_role,
    assert_same_branch,
    child_student_user_ids,
    is_global,
    narrow,
)
from institute_crm.utils import active

#: Roles that may publish material.
MATERIAL_PUBLISHERS = (Role.SUPER_ADMIN, Role.BRANCH_ADMIN, Role.TEACHER)

_LINK_TYPES = {"LINK", "VIDEO"}


class StudyMaterialService:
    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_materials(actor: User):
        queryset = (
            active(StudyMaterial)
            .select_related("subject", "subject__course", "batch", "batch__branch", "uploaded_by")
            .order_by("-created_at")
        )

        if is_global(actor):
            return queryset

        branch_id = getattr(actor, "branch_id", None)
        role = getattr(actor, "role_code", None)

        if role == Role.STUDENT:
            # A student sees material for the batches they are enrolled in, plus course-wide
            # material for the courses those batches run.
            enrolled = active(Batch).filter(
                enrolments__student_id=actor.pk,
                enrolments__is_deleted=False,
                enrolments__status="ACTIVE",
            )
            return queryset.filter(
                Q(batch__in=enrolled)
                | Q(batch__isnull=True, subject__course__batches__in=enrolled)
            ).distinct()

        if role == Role.PARENT:
            child_ids = child_student_user_ids(actor)
            enrolled = active(Batch).filter(
                enrolments__student_id__in=child_ids,
                enrolments__is_deleted=False,
                enrolments__status="ACTIVE",
            )
            return queryset.filter(
                Q(batch__in=enrolled)
                | Q(batch__isnull=True, subject__course__batches__in=enrolled)
            ).distinct()

        if not branch_id:
            # Fail closed, consistent with scope_to_branch.
            return queryset.none()

        if role == Role.TEACHER:
            taught = active(Batch).filter(
                timetables__teacher_id=actor.pk, timetables__is_deleted=False
            )
            return queryset.filter(
                Q(batch__in=taught) | Q(batch__isnull=True) | Q(uploaded_by_id=actor.pk)
            ).distinct()

        # Branch staff: their own branch's cohort material plus all course-wide material.
        return queryset.filter(
            Q(batch__branch_id=branch_id) | Q(batch__isnull=True)
        ).distinct()

    @staticmethod
    def filter_materials(
        actor: User,
        *,
        subject_id=None,
        batch_id=None,
        material_type: str | None = None,
        search: str | None = None,
    ):
        queryset = narrow(
            StudyMaterialService.visible_materials(actor),
            {
                "subject_id": subject_id,
                "batch_id": batch_id,
                "material_type": material_type.upper() if material_type else None,
            },
        )
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(subject__title__icontains=search)
            )
        return queryset

    @staticmethod
    def get_material_for_actor(actor: User, material_id) -> StudyMaterial:
        try:
            return StudyMaterialService.visible_materials(actor).get(pk=material_id)
        except StudyMaterial.DoesNotExist as exc:
            raise NotFoundError("Study material not found.") from exc

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def publish_material(
        *, actor: User, data: dict, ip_address: str | None = None
    ) -> StudyMaterial:
        assert_role(
            actor,
            MATERIAL_PUBLISHERS,
            message="Only teachers and administrators can publish study material.",
        )

        payload = dict(data)
        # Authorship is taken from the session, never from the request body. The previous
        # implementation set it on create but left it writable on update.
        payload["uploaded_by"] = actor
        StudyMaterialService._validate(payload)
        StudyMaterialService._assert_may_publish(actor, payload)

        material = StudyMaterial.objects.create(**payload)
        audit.record_audit(
            actor=actor,
            action=audit.CREATE,
            instance=material,
            changes={
                "title": material.title,
                "subject": str(material.subject_id),
                "batch": str(material.batch_id) if material.batch_id else None,
                "type": material.material_type,
            },
            ip_address=ip_address,
        )
        return material

    @staticmethod
    @transaction.atomic
    def update_material(
        *, actor: User, material: StudyMaterial, data: dict, ip_address: str | None = None
    ) -> StudyMaterial:
        assert_role(
            actor,
            MATERIAL_PUBLISHERS,
            message="Only teachers and administrators can edit study material.",
        )
        StudyMaterialService._assert_may_edit(actor, material)

        payload = dict(data)
        payload.pop("uploaded_by", None)  # authorship is immutable

        merged = {
            "subject": payload.get("subject", material.subject),
            "batch": payload.get("batch", material.batch),
            "title": payload.get("title", material.title),
            "material_type": (
                payload.get("material_type", material.material_type) or ""
            ).upper(),
            "file_url": payload.get("file_url", material.file_url),
            "external_link": payload.get("external_link", material.external_link),
        }
        StudyMaterialService._validate(merged)
        StudyMaterialService._assert_may_publish(actor, merged)

        changes = audit.diff_fields(material, merged)
        for field, value in merged.items():
            setattr(material, field, value)
        material.save()

        audit.record_audit(
            actor=actor,
            action=audit.UPDATE,
            instance=material,
            changes=changes,
            ip_address=ip_address,
        )
        return material

    @staticmethod
    @transaction.atomic
    def soft_delete_material(
        *, actor: User, material: StudyMaterial, ip_address: str | None = None
    ) -> None:
        assert_role(
            actor,
            MATERIAL_PUBLISHERS,
            message="Only teachers and administrators can remove study material.",
        )
        StudyMaterialService._assert_may_edit(actor, material)

        material.soft_delete()
        audit.record_audit(
            actor=actor,
            action=audit.DELETE,
            instance=material,
            changes={"soft_delete": True, "title": material.title},
            ip_address=ip_address,
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _validate(payload: dict) -> None:
        subject: Subject | None = payload.get("subject")
        batch: Batch | None = payload.get("batch")
        material_type = (payload.get("material_type") or "PDF").upper()
        payload["material_type"] = material_type

        if subject is None:
            raise ValidationFailed(
                "Choose the subject this material belongs to.",
                field_errors={"subject": ["This field is required."]},
            )
        if not (payload.get("title") or "").strip():
            raise ValidationFailed(
                "Give the material a title.",
                field_errors={"title": ["This field is required."]},
            )

        valid_types = {code for code, _ in StudyMaterial.TYPE_CHOICES}
        if material_type not in valid_types:
            raise ValidationFailed(
                f"Unknown material type '{material_type}'.",
                field_errors={
                    "material_type": [f"Choose one of: {', '.join(sorted(valid_types))}."]
                },
            )

        # A material with neither a file nor a link is a dead entry in the student's list.
        file_url = payload.get("file_url")
        external_link = payload.get("external_link")
        if not file_url and not external_link:
            field = "external_link" if material_type in _LINK_TYPES else "file_url"
            raise ValidationFailed(
                "Attach a file or provide a link.",
                field_errors={field: ["Provide either an uploaded file URL or a link."]},
            )

        if batch is not None and batch.course_id != subject.course_id:
            raise ValidationFailed(
                f"'{subject.title}' is not part of the course batch '{batch.name}' runs.",
                field_errors={"subject": ["Choose a subject from the batch's course."]},
            )

    @staticmethod
    def _assert_may_publish(actor: User, payload: dict) -> None:
        batch: Batch | None = payload.get("batch")
        if batch is not None:
            assert_same_branch(
                actor,
                batch.branch_id,
                message="You can only publish material to batches in your own branch.",
            )
            if actor.role_code == Role.TEACHER:
                teaches = active(batch.timetables).filter(teacher_id=actor.pk).exists()
                if not teaches:
                    from institute_crm.exceptions import PermissionDeniedError

                    raise PermissionDeniedError(
                        "You can only publish material to batches you teach.",
                        code="not_your_batch",
                    )
            return

        # Course-wide material reaches every branch, so it is an administrator's decision.
        if actor.role_code == Role.TEACHER:
            raise ConflictError(
                "Teachers publish material to a specific batch. Choose a batch, or ask an "
                "administrator to publish it course-wide.",
                code="batch_required_for_teacher",
            )

    @staticmethod
    def _assert_may_edit(actor: User, material: StudyMaterial) -> None:
        if is_global(actor) or actor.role_code == Role.BRANCH_ADMIN:
            if material.batch_id:
                assert_same_branch(
                    actor,
                    material.batch.branch_id,
                    message="That material belongs to another branch.",
                )
            return
        if material.uploaded_by_id != actor.pk:
            from institute_crm.exceptions import PermissionDeniedError

            raise PermissionDeniedError(
                "You can only edit material you uploaded.", code="not_your_material"
            )
