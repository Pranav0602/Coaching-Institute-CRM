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
        branch_id: str | None = None,
    ) -> QuerySet[Exam]:
        from django.db.models import Q
        from institute_crm.scoping import is_global

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
                qs = qs.filter(
                    Q(batch__timetables__teacher=actor) | Q(batch__teachers=actor)
                ).distinct()
            elif role_code in [Role.BRANCH_ADMIN, Role.RECEPTIONIST] and actor.branch:
                qs = qs.filter(batch__branch=actor.branch)
            if is_global(actor) and branch_id:
                qs = qs.filter(batch__branch_id=branch_id)

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
        batch_id: str | None = None,
        branch_id: str | None = None,
    ) -> QuerySet[Result]:
        from django.db.models import Q
        from institute_crm.scoping import is_global

        qs = Result.objects.filter(is_deleted=False).select_related(
            'exam', 'exam__subject', 'exam__batch', 'student'
        )

        if exam_id:
            qs = qs.filter(exam_id=exam_id)
        if student_id:
            qs = qs.filter(student_id=student_id)
        if batch_id:
            qs = qs.filter(exam__batch_id=batch_id)

        if actor and actor.is_authenticated and actor.role:
            role_code = actor.role.code
            if role_code == Role.STUDENT:
                qs = qs.filter(student=actor)
            elif role_code == Role.PARENT:
                qs = qs.filter(student__student_profile__parent_links__parent__user=actor)
            elif role_code == Role.TEACHER:
                qs = qs.filter(
                    Q(exam__batch__timetables__teacher=actor)
                    | Q(exam__batch__teachers=actor)
                ).distinct()
            elif role_code in [Role.BRANCH_ADMIN] and actor.branch:
                qs = qs.filter(exam__batch__branch=actor.branch)
            if is_global(actor) and branch_id:
                qs = qs.filter(exam__batch__branch_id=branch_id)

        return qs.order_by('-created_at')

    @staticmethod
    def _grade_for_pct(pct: float) -> str:
        if pct >= 90:
            return 'A+'
        if pct >= 80:
            return 'A'
        if pct >= 70:
            return 'B'
        if pct >= 60:
            return 'C'
        if pct >= 40:
            return 'D'
        return 'F'

    @staticmethod
    def batch_exam_report(actor: User, batch_id: str) -> dict:
        """All exams in a batch plus per-student results and batch aggregates."""
        from academics.models import CourseEnrolment
        from institute_crm.scoping import assert_same_branch, is_global
        from institute_crm.utils import active

        exams = list(ExamService.filter_exams(actor, batch_id=batch_id))
        if not exams:
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
            batch = exams[0].batch
            batch_name, batch_code = batch.name, batch.code
            if not is_global(actor):
                assert_same_branch(actor, batch.branch_id, message="That batch belongs to another branch.")

        enrolments = list(
            active(CourseEnrolment).filter(batch_id=batch_id, status="ACTIVE").select_related("student")
        )
        results = list(ExamService.filter_results(actor, batch_id=batch_id).select_related("exam", "student"))
        res_lookup: dict[tuple[str, str], Result] = {
            (str(r.exam_id), str(r.student_id)): r for r in results
        }

        exam_cards = []
        all_scores: list[float] = []
        passed_total = 0
        grade_dist = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for exam in exams:
            exam_results = [r for r in results if str(r.exam_id) == str(exam.id)]
            scores = []
            passed = 0
            for r in exam_results:
                total = float(exam.total_marks) if exam.total_marks else 0
                pct = (float(r.marks_obtained or 0) / total * 100) if total else 0
                scores.append(pct)
                all_scores.append(pct)
                if float(r.marks_obtained or 0) >= float(exam.passing_marks or 0):
                    passed += 1
                    passed_total += 1
                grade = (r.grade or "").strip() or ExamService._grade_for_pct(pct)
                if grade in grade_dist:
                    grade_dist[grade] += 1
            rows = []
            for enr in enrolments:
                res = res_lookup.get((str(exam.id), str(enr.student_id)))
                if res is None:
                    rows.append(
                        {
                            "student_id": str(enr.student_id),
                            "student_name": enr.student.get_full_name() or enr.student.username,
                            "status": "ABSENT",
                            "marks_obtained": None,
                            "percentage": None,
                            "grade": None,
                            "passed": None,
                            "remarks": "",
                        }
                    )
                    continue
                total = float(exam.total_marks) if exam.total_marks else 0
                pct = (float(res.marks_obtained or 0) / total * 100) if total else 0
                grade = (res.grade or "").strip() or ExamService._grade_for_pct(pct)
                rows.append(
                    {
                        "student_id": str(enr.student_id),
                        "student_name": enr.student.get_full_name() or enr.student.username,
                        "status": "PRESENT",
                        "marks_obtained": float(res.marks_obtained),
                        "percentage": round(pct, 2),
                        "grade": grade,
                        "passed": float(res.marks_obtained or 0) >= float(exam.passing_marks or 0),
                        "remarks": res.remarks or "",
                    }
                )
            exam_cards.append(
                {
                    "id": str(exam.id),
                    "title": exam.title,
                    "exam_date": exam.exam_date.isoformat() if exam.exam_date else None,
                    "total_marks": exam.total_marks,
                    "passing_marks": exam.passing_marks,
                    "results_count": len(exam_results),
                    "pass_rate_pct": round((passed / len(exam_results)) * 100, 2) if exam_results else None,
                    "average_score_pct": round(sum(scores) / len(scores), 2) if scores else None,
                    "students": rows,
                }
            )

        return {
            "batch_id": str(batch_id),
            "batch_name": batch_name,
            "batch_code": batch_code,
            "total_exams": len(exams),
            "results_published": len(results),
            "pass_rate_pct": round((passed_total / len(results)) * 100, 2) if results else None,
            "average_score_pct": round(sum(all_scores) / len(all_scores), 2) if all_scores else None,
            "top_score_pct": round(max(all_scores), 2) if all_scores else None,
            "lowest_score_pct": round(min(all_scores), 2) if all_scores else None,
            "grade_distribution": grade_dist,
            "exams": exam_cards,
        }

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
