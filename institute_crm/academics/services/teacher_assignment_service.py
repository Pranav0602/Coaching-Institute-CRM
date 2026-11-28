"""
Teacher assignment management.

A :class:`TeacherAssignment` binds a teacher (user with the TEACHER role) to a
branch and one course they teach. Branch Admins manage assignments within their
own branch; Super Admins have system-wide access. Every rule is enforced here so
it holds for any caller, not just HTTP requests.

Rules
-----
* Only administrators assign/remove; a teacher cannot self-assign.
* The teacher must be an active, non-deleted TEACHER and must not belong to a
  different branch. A teacher with no branch is moved into the assignment branch.
* The branch must be active; the assignment is created inside the caller's
  branch scope (cross-branch denied).
* Selected courses must belong to that branch (active course offered by an
  active batch in that branch).
* No duplicate (teacher, branch, course): rejected with a conflict; enforced
  both in code and by a partial unique constraint.
* Removal is a soft delete; history is retained; audit entries are written.
* Everything still works when a teacher has no assignments at all.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Q

from accounts.models import Branch, Role, User
from academics.models import Batch, Course, TeacherAssignment, Timetable
from institute_crm import audit
from institute_crm.exceptions import ConflictError, NotFoundError, ValidationFailed
from institute_crm.scoping import assert_role, assert_same_branch, is_global
from institute_crm.utils import active

#: Roles allowed to manage teacher assignments.
ASSIGNMENT_ADMINS = Role.ADMIN_ROLES


class TeacherAssignmentService:
    # ------------------------------------------------------------------ reads

    @staticmethod
    def visible_assignments(actor: User):
        queryset = (
            active(TeacherAssignment)
            .select_related("teacher", "branch", "course", "assigned_by")
            .order_by("branch__name", "course__title", "teacher__username")
        )
        if not (actor and actor.is_authenticated):
            return queryset.none()

        role_code = getattr(actor, "role_code", None)
        if is_global(actor):
            return queryset
        if role_code in ASSIGNMENT_ADMINS:
            if actor.branch_id:
                return queryset.filter(branch_id=actor.branch_id)
            return queryset.none()
        if role_code == Role.TEACHER:
            return queryset.filter(teacher_id=actor.pk)
        return queryset.none()

    @staticmethod
    def list_assignments(
        actor: User,
        *,
        teacher_id=None,
        branch_id=None,
        course_id=None,
    ):
        queryset = TeacherAssignmentService.visible_assignments(actor)
        # Optional narrowing only; can never widen scope.
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
        if branch_id:
            queryset = queryset.filter(branch_id=branch_id)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    @staticmethod
    def courses_for_branch(branch) -> list:
        """Active courses offered at ``branch`` (an active batch pins it)."""
        if branch is None:
            return []
        return list(
            active(Course)
            .filter(Q(batches__branch_id=branch.pk, batches__is_deleted=False))
            .distinct()
            .order_by("title")
        )

    @staticmethod
    def course_belongs_to_branch(course, branch) -> bool:
        """A selected course must be offered at that branch."""
        if course is None or branch is None or course.is_deleted:
            return False
        return (
            active(Batch)
            .filter(course_id=course.pk, branch_id=branch.pk)
            .exists()
        )

    @staticmethod
    def assigned_scope(teacher) -> dict:
        """Union of teacher-relevant ids from explicit assignments + existing links.

        Returns ``{'course_ids': set, 'branch_ids': set, 'batch_ids': set}``.
        Safe when a teacher has no assignments: empty sets.
        """
        course_ids: set = set()
        branch_ids: set = set()
        batch_ids: set = set()

        if teacher is None or not getattr(teacher, "pk", None):
            return {"course_ids": course_ids, "branch_ids": branch_ids, "batch_ids": batch_ids}

        rows = (
            active(TeacherAssignment)
            .filter(teacher_id=teacher.pk)
            .values_list("course_id", "branch_id")
        )
        for course_id, branch_id in rows:
            course_ids.add(course_id)
            if branch_id:
                branch_ids.add(branch_id)

        assigned_batches = active(Batch).filter(teachers=teacher)
        batch_ids |= set(assigned_batches.values_list("pk", flat=True))
        batch_ids |= set(
            active(Timetable).filter(teacher_id=teacher.pk).values_list("batch_id", flat=True)
        )
        if batch_ids:
            course_ids |= set(
                active(Batch).filter(pk__in=batch_ids).values_list("course_id", flat=True)
            )
        course_ids.discard(None)
        branch_ids.discard(None)
        return {"course_ids": course_ids, "branch_ids": branch_ids, "batch_ids": batch_ids}

    # ----------------------------------------------------------------- writes

    @staticmethod
    @transaction.atomic
    def assign(
        *,
        actor: User,
        teacher,
        branch,
        course_ids=None,
        course=None,
        notes: str | None = None,
        ip_address: str | None = None,
    ) -> list:
        """Assign ``teacher`` to ``branch`` and one or more courses.

        Accepts ``course`` (single) and/or ``course_ids`` (list). Validates every
        course belongs to the branch and rejects duplicates. Returns created rows.
        """
        assert_role(actor, ASSIGNMENT_ADMINS, message="Only administrators can assign teachers.")

        teacher = TeacherAssignmentService._resolve_teacher(teacher)
        branch = TeacherAssignmentService._resolve_branch(branch)

        # Cross-branch denied; non-global callers stay in their own branch.
        assert_same_branch(
            actor, branch.pk, message="You can only assign teachers in your own branch."
        )

        selected: list = []
        raw_ids = list(course_ids or [])
        if course is not None:
            raw_ids.append(course)
        if not raw_ids:
            raise ValidationFailed(
                "Select at least one course for this teacher.",
                field_errors={"course_ids": ["Select at least one course."]},
                code="course_required",
            )

        # De-duplicate the request payload itself (a repeated id is not a new assignment).
        seen: set = set()
        for raw in raw_ids:
            key = str(getattr(raw, "pk", raw)).strip()
            if not key or key in seen:
                continue
            seen.add(key)
            selected.append(raw)

        resolved_courses = [TeacherAssignmentService._resolve_course(c) for c in selected]

        # Teacher-branch consistency: a teacher cannot belong to a different branch.
        if teacher.branch_id and teacher.branch_id != branch.pk:
            raise ValidationFailed(
                f"{teacher.username} belongs to a different branch.",
                field_errors={"teacher": ["Teacher and branch must match."]},
                code="teacher_branch_mismatch",
            )

        # Course must belong to the chosen branch.
        invalid = [
            c.title for c in resolved_courses
            if not TeacherAssignmentService.course_belongs_to_branch(c, branch)
        ]
        if invalid:
            raise ValidationFailed(
                "Selected course(s) do not belong to this branch.",
                field_errors={"course_ids": [f"Not offered at this branch: {', '.join(invalid)}"]},
                code="course_not_in_branch",
            )

        # Duplicate check (existing active rows).
        for c in resolved_courses:
            existing = active(TeacherAssignment).filter(
                teacher_id=teacher.pk, branch_id=branch.pk, course_id=c.pk
            ).exists()
            if existing:
                raise ConflictError(
                    f"{teacher.username} is already assigned to {c.title} at {branch.name}.",
                    field_errors={"course_ids": [f"Duplicate assignment: {c.title}"]},
                    code="duplicate_assignment",
                )

        # Move an unassigned teacher into this branch (assign teacher to branch).
        if not teacher.branch_id:
            teacher.branch = branch
            teacher.save(update_fields=["branch"])
            audit.record_audit(
                actor=actor, action=audit.UPDATE, instance=teacher,
                changes={"branch": str(branch.pk)}, ip_address=ip_address,
            )

        created = []
        try:
            for c in resolved_courses:
                assignment = TeacherAssignment.objects.create(
                    teacher=teacher, branch=branch, course=c,
                    assigned_by=actor if getattr(actor, "pk", None) else None,
                    notes=(notes or None),
                )
                created.append(assignment)
                audit.record_audit(
                    actor=actor, action=audit.CREATE, instance=assignment,
                    changes={
                        "teacher": str(teacher.pk), "branch": str(branch.pk),
                        "course": str(c.pk), "course_code": c.code,
                    },
                    ip_address=ip_address,
                )
        except IntegrityError as exc:
            raise ConflictError(
                "Duplicate assignment.", code="duplicate_assignment",
                field_errors={"course_ids": ["Duplicate assignment."]},
            ) from exc

        return created

    @staticmethod
    @transaction.atomic
    def update_assignment(
        *,
        actor: User,
        assignment: TeacherAssignment,
        course=None,
        branch=None,
        teacher=None,
        notes=None,
        ip_address: str | None = None,
    ) -> TeacherAssignment:
        assert_role(actor, ASSIGNMENT_ADMINS, message="Only administrators can change teacher assignments.")
        assert_same_branch(actor, assignment.branch_id, message="That assignment belongs to another branch.")

        new_teacher = TeacherAssignmentService._resolve_teacher(teacher) if teacher is not None else assignment.teacher
        new_branch = TeacherAssignmentService._resolve_branch(branch) if branch is not None else assignment.branch
        new_course = TeacherAssignmentService._resolve_course(course) if course is not None else assignment.course

        assert_same_branch(actor, new_branch.pk, message="You can only assign teachers in your own branch.")

        if new_teacher.branch_id and new_teacher.branch_id != new_branch.pk:
            raise ValidationFailed(
                f"{new_teacher.username} belongs to a different branch.",
                field_errors={"teacher": ["Teacher and branch must match."]},
                code="teacher_branch_mismatch",
            )
        if not TeacherAssignmentService.course_belongs_to_branch(new_course, new_branch):
            raise ValidationFailed(
                "Selected course does not belong to this branch.",
                field_errors={"course": ["Choose a course offered at this branch."]},
                code="course_not_in_branch",
            )

        clash = active(TeacherAssignment).filter(
            teacher_id=new_teacher.pk, branch_id=new_branch.pk, course_id=new_course.pk,
        ).exclude(pk=assignment.pk).exists()
        if clash:
            raise ConflictError(
                "Duplicate assignment.", code="duplicate_assignment",
                field_errors={"course": ["Duplicate assignment."]},
            )

        changes = audit.diff_fields(assignment, {
            "teacher": new_teacher, "branch": new_branch, "course": new_course,
        })
        assignment.teacher = new_teacher
        assignment.branch = new_branch
        assignment.course = new_course
        if notes is not None:
            changes["notes"] = {"from": assignment.notes, "to": notes}
            assignment.notes = notes
        try:
            assignment.save()
        except IntegrityError as exc:
            raise ConflictError("Duplicate assignment.", code="duplicate_assignment") from exc

        audit.record_audit(
            actor=actor, action=audit.UPDATE, instance=assignment,
            changes=changes, ip_address=ip_address,
        )
        return assignment

    @staticmethod
    @transaction.atomic
    def remove_assignment(
        *, actor: User, assignment: TeacherAssignment, ip_address: str | None = None
    ) -> None:
        assert_role(actor, ASSIGNMENT_ADMINS, message="Only administrators can remove teacher assignments.")
        assert_same_branch(actor, assignment.branch_id, message="That assignment belongs to another branch.")
        assignment.soft_delete()
        audit.record_audit(
            actor=actor, action=audit.DELETE, instance=assignment,
            changes={
                "soft_delete": True, "teacher": str(assignment.teacher_id),
                "branch": str(assignment.branch_id), "course": str(assignment.course_id),
            },
            ip_address=ip_address,
        )

    # -------------------------------------------------------------- internals

    @staticmethod
    def _resolve_teacher(teacher) -> User:
        if teacher is None:
            raise ValidationFailed(
                "A teacher is required.", field_errors={"teacher": ["This field is required."]}
            )
        if isinstance(teacher, User):
            obj = teacher
        else:
            obj = active(User).filter(pk=teacher).first()
        if obj is None or getattr(obj, "is_deleted", False):
            raise NotFoundError("Teacher not found.", code="teacher_not_found")
        if not obj.is_active:
            raise ValidationFailed(
                "That teacher account is inactive.",
                field_errors={"teacher": ["Account is inactive."]}, code="teacher_inactive",
            )
        if obj.role_code != Role.TEACHER:
            raise ValidationFailed(
                "Only users with the Teacher role can be assigned.",
                field_errors={"teacher": ["This account is not a teacher."]}, code="not_a_teacher",
            )
        return obj

    @staticmethod
    def _resolve_branch(branch) -> Branch:
        if branch is None:
            raise ValidationFailed(
                "A branch is required.", field_errors={"branch": ["This field is required."]}
            )
        obj = branch if isinstance(branch, Branch) else active(Branch).filter(pk=branch).first()
        if obj is None or getattr(obj, "is_deleted", False):
            raise NotFoundError("Branch not found.", code="branch_not_found")
        return obj

    @staticmethod
    def _resolve_course(course) -> Course:
        obj = course if isinstance(course, Course) else active(Course).filter(pk=course).first()
        if obj is None or getattr(obj, "is_deleted", False):
            raise ValidationFailed(
                "Unknown or retired course.",
                field_errors={"course_ids": ["Unknown course."]}, code="course_not_found",
            )
        return obj
