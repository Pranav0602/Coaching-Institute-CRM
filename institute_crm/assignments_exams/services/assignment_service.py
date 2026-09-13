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
        branch_id: str | None = None,
    ) -> QuerySet[Assignment]:
        from django.db.models import Q
        from institute_crm.scoping import is_global

        qs = Assignment.objects.filter(is_deleted=False).select_related(
            'subject', 'batch', 'batch__branch', 'created_by'
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
                qs = qs.filter(
                    Q(batch__timetables__teacher=actor) | Q(batch__teachers=actor)
                ).distinct()
            elif role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST] and actor.branch:
                qs = qs.filter(batch__branch=actor.branch)
            if is_global(actor) and branch_id:
                qs = qs.filter(batch__branch_id=branch_id)

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
        batch_id: str | None = None,
        branch_id: str | None = None,
    ) -> QuerySet[Submission]:
        from django.db.models import Q
        from institute_crm.scoping import is_global

        qs = Submission.objects.filter(is_deleted=False).select_related(
            'assignment', 'assignment__batch', 'student', 'evaluated_by'
        )

        if assignment_id:
            qs = qs.filter(assignment_id=assignment_id)
        if student_id:
            qs = qs.filter(student_id=student_id)
        if batch_id:
            qs = qs.filter(assignment__batch_id=batch_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code == Role.TEACHER:
                qs = qs.filter(
                    Q(assignment__batch__timetables__teacher=actor)
                    | Q(assignment__batch__teachers=actor)
                ).distinct()
            elif role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST] and actor.branch:
                qs = qs.filter(assignment__batch__branch=actor.branch)
            if is_global(actor) and branch_id:
                qs = qs.filter(assignment__batch__branch_id=branch_id)

        return qs.order_by('-submitted_at')

    @staticmethod
    def batch_assignment_report(actor: User, batch_id: str) -> dict:
        """All assignments in a batch plus per-student submission breakdown."""
        from academics.models import CourseEnrolment
        from institute_crm.scoping import assert_same_branch, is_global
        from institute_crm.utils import active

        assignments = list(AssignmentService.filter_assignments(actor, batch_id=batch_id))
        if not assignments:
            # Still enforce branch scoping: verify the batch itself is visible.
            from academics.models import Batch as _Batch
            try:
                batch = _Batch.objects.get(pk=batch_id, is_deleted=False)
            except _Batch.DoesNotExist:
                from institute_crm.exceptions import NotFoundError as _NotFound
                raise _NotFound("Batch not found.")
            if not is_global(actor):
                assert_same_branch(actor, batch.branch_id, message="That batch belongs to another branch.")
            batch_name, batch_code = batch.name, batch.code
        else:
            batch = assignments[0].batch
            batch_name, batch_code = batch.name, batch.code
            if not is_global(actor):
                assert_same_branch(actor, batch.branch_id, message="That batch belongs to another branch.")

        enrolments = list(
            active(CourseEnrolment).filter(batch_id=batch_id, status="ACTIVE").select_related("student")
        )
        submissions = list(AssignmentService.filter_submissions(actor, batch_id=batch_id).select_related("assignment", "student", "evaluated_by"))
        sub_lookup: dict[tuple[str, str], Submission] = {
            (str(s.assignment_id), str(s.student_id)): s for s in submissions
        }

        assignment_cards = []
        total_received = 0
        expected = 0
        evaluated_scores: list[float] = []
        pending_total = 0
        for assignment in assignments:
            subs = [s for s in submissions if str(s.assignment_id) == str(assignment.id)]
            total_received += len(subs)
            expected += len(enrolments)
            pending = sum(1 for s in subs if s.marks_obtained is None)
            pending_total += pending
            for s in subs:
                if s.marks_obtained is not None and assignment.total_marks:
                    evaluated_scores.append(float(s.marks_obtained) / float(assignment.total_marks) * 100)
            rows = []
            for enr in enrolments:
                sub = sub_lookup.get((str(assignment.id), str(enr.student_id)))
                if sub is None:
                    status_label = "NOT_SUBMITTED"
                elif sub.submitted_at and assignment.due_date and sub.submitted_at > assignment.due_date:
                    status_label = "LATE"
                else:
                    status_label = "ON_TIME"
                rows.append(
                    {
                        "student_id": str(enr.student_id),
                        "student_name": enr.student.get_full_name() or enr.student.username,
                        "status": "SUBMITTED" if sub else "NOT_SUBMITTED",
                        "timeliness": status_label if sub else "NOT_SUBMITTED",
                        "file_url": sub.file_url if sub else None,
                        "submitted_at": sub.submitted_at.isoformat() if sub and sub.submitted_at else None,
                        "marks_obtained": float(sub.marks_obtained) if sub and sub.marks_obtained is not None else None,
                        "feedback": sub.feedback if sub else "",
                        "evaluated_by": (sub.evaluated_by.get_full_name() or sub.evaluated_by.username) if sub and sub.evaluated_by else None,
                    }
                )
            assignment_cards.append(
                {
                    "id": str(assignment.id),
                    "title": assignment.title,
                    "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                    "total_marks": assignment.total_marks,
                    "received": len(subs),
                    "expected": len(enrolments),
                    "submission_rate_pct": round((len(subs) / len(enrolments)) * 100, 2) if enrolments else 0,
                    "pending_evaluations": pending,
                    "students": rows,
                }
            )

        return {
            "batch_id": str(batch_id),
            "batch_name": batch_name,
            "batch_code": batch_code,
            "total_assignments": len(assignments),
            "submissions_received": total_received,
            "expected_submissions": expected,
            "submission_rate_pct": round((total_received / expected) * 100, 2) if expected else 0,
            "pending_evaluations": pending_total,
            "average_score_pct": round(sum(evaluated_scores) / len(evaluated_scores), 2) if evaluated_scores else None,
            "assignments": assignment_cards,
        }

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
