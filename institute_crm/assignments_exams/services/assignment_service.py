"""
Service layer for assignments and submissions in assignments_exams app.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from accounts.models import Role, User
from assignments_exams.models import Assignment, Submission

logger = logging.getLogger('institute_crm.assignments')


class AssignmentService:
    @staticmethod
    def filter_assignments(
        actor: User,
        *,
        batch_id: str | None = None,
        subject_id: str | None = None,
    ) -> QuerySet[Assignment]:
        qs = Assignment.objects.filter(is_deleted=False).select_related(
            'subject', 'batch', 'created_by'
        )

        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if subject_id:
            qs = qs.filter(subject_id=subject_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(batch__students__user=actor)
            elif role_code == Role.TEACHER:
                qs = qs.filter(batch__timetables__teacher=actor).distinct()
            elif role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST] and actor.branch:
                qs = qs.filter(batch__branch=actor.branch)

        return qs.order_by('-due_date')

    @staticmethod
    @transaction.atomic
    def create_assignment(actor: User, data: dict[str, Any]) -> Assignment:
        assignment = Assignment.objects.create(
            created_by=actor,
            **data
        )
        logger.info(f"Assignment {assignment.id} '{assignment.title}' created by user {actor.id}")
        return assignment

    @staticmethod
    def filter_submissions(
        actor: User,
        *,
        assignment_id: str | None = None,
        student_id: str | None = None,
    ) -> QuerySet[Submission]:
        qs = Submission.objects.filter(is_deleted=False).select_related(
            'assignment', 'student', 'evaluated_by'
        )

        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        if student_id:
            qs = qs.filter(student_id=student_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code == Role.TEACHER:
                qs = qs.filter(assignment__batch__timetables__teacher=actor).distinct()

        return qs.order_by('-submitted_at')

    @staticmethod
    @transaction.atomic
    def submit_assignment(
        student: User,
        assignment_id: str,
        file_url: str,
    ) -> Submission:
        assignment = Assignment.objects.get(id=assignment_id, is_deleted=False)
        submission, created = Submission.objects.update_or_create(
            assignment=assignment,
            student=student,
            defaults={
                'file_url': file_url,
            }
        )
        logger.info(f"Submission recorded for student {student.id} on assignment {assignment_id}")
        return submission

    @staticmethod
    @transaction.atomic
    def evaluate_submission(
        evaluator: User,
        submission_id: str,
        marks_obtained: float,
        feedback: str = "",
    ) -> Submission:
        submission = Submission.objects.get(id=submission_id, is_deleted=False)
        if marks_obtained > submission.assignment.total_marks:
            raise ValidationError(f"Marks obtained ({marks_obtained}) cannot exceed total marks ({submission.assignment.total_marks}).")

        submission.marks_obtained = marks_obtained
        submission.feedback = feedback
        submission.evaluated_by = evaluator
        submission.save()
        logger.info(f"Submission {submission_id} evaluated by user {evaluator.id}")
        return submission
