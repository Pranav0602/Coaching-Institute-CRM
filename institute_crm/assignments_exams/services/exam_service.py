"""
Service layer for exams, question papers, and results in assignments_exams app.
"""
from __future__ import annotations

import logging
from typing import Any
from django.db import transaction
from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

from accounts.models import Role, User
from assignments_exams.models import Exam, ExamQuestionPaper, Result

logger = logging.getLogger('institute_crm.exams')


class ExamService:
    @staticmethod
    def filter_exams(
        actor: User,
        *,
        batch_id: str | None = None,
        subject_id: str | None = None,
    ) -> QuerySet[Exam]:
        qs = Exam.objects.filter(is_deleted=False).select_related(
            'subject', 'batch', 'batch__course', 'batch__branch'
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

        return qs.order_by('-exam_date')

    @staticmethod
    @transaction.atomic
    def create_exam(actor: User, data: dict[str, Any]) -> Exam:
        exam = Exam.objects.create(**data)
        logger.info(f"Exam {exam.id} '{exam.title}' created by user {actor.id}")
        return exam

    @staticmethod
    def filter_results(
        actor: User,
        *,
        exam_id: str | None = None,
        student_id: str | None = None,
    ) -> QuerySet[Result]:
        qs = Result.objects.filter(is_deleted=False).select_related(
            'exam', 'exam__subject', 'exam__batch', 'student'
        )

        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        if student_id:
            qs = qs.filter(student_id=student_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code in [Role.BRANCH_ADMIN] and actor.branch:
                qs = qs.filter(exam__batch__branch=actor.branch)

        return qs.order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def publish_exam_results(
        actor: User,
        exam_id: str,
        results_data: list[dict[str, Any]],
    ) -> list[Result]:
        exam = Exam.objects.get(id=exam_id, is_deleted=False)
        created_results = []

        for item in results_data:
            student_id = item.get('student_id')
            marks_obtained = item.get('marks_obtained')
            grade = item.get('grade')
            remarks = item.get('remarks', '')

            # Auto calculate grade if not explicitly supplied
            if not grade and marks_obtained is not None:
                pct = (float(marks_obtained) / float(exam.total_marks)) * 100 if exam.total_marks > 0 else 0
                if pct >= 90:
                    grade = 'A+'
                elif pct >= 80:
                    grade = 'A'
                elif pct >= 70:
                    grade = 'B'
                elif pct >= 60:
                    grade = 'C'
                elif pct >= 40:
                    grade = 'D'
                else:
                    grade = 'F'

            res, _ = Result.objects.update_or_create(
                exam=exam,
                student_id=student_id,
                defaults={
                    'marks_obtained': marks_obtained,
                    'grade': grade,
                    'remarks': remarks,
                }
            )
            created_results.append(res)

        logger.info(f"Published {len(created_results)} results for exam {exam_id} by user {actor.id}")
        return created_results

    @staticmethod
    @transaction.atomic
    def attach_question_paper(
        actor: User,
        exam_id: str,
        title: str,
        paper_url: str,
    ) -> ExamQuestionPaper:
        exam = Exam.objects.get(id=exam_id, is_deleted=False)
        paper = ExamQuestionPaper.objects.create(
            exam=exam,
            title=title,
            paper_url=paper_url,
            created_by=actor
        )
        return paper
