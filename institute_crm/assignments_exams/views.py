"""
HTTP controller layer for the assignments_exams app.
Thin views that validate requests and delegate business logic to AssignmentService and ExamService.
"""
from __future__ import annotations

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from assignments_exams.models import Assignment, Submission, Exam, ExamQuestionPaper, Result
from assignments_exams.serializers import (
    AssignmentSerializer, SubmissionSerializer, ExamSerializer, 
    ExamQuestionPaperSerializer, ResultSerializer
)
from assignments_exams.services import AssignmentService, ExamService


class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AssignmentService.filter_assignments(
            self.request.user,
            batch_id=self.request.query_params.get('batch_id'),
            subject_id=self.request.query_params.get('subject_id'),
            branch_id=self.request.query_params.get('branch_id'),
        )

    @action(detail=False, methods=['get'], url_path='batch-report')
    def batch_report(self, request):
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response({"detail": "batch_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(AssignmentService.batch_assignment_report(request.user, str(batch_id)))

    def perform_create(self, serializer):
        AssignmentService.create_assignment(
            actor=self.request.user,
            data=serializer.validated_data,
        )


class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AssignmentService.filter_submissions(
            self.request.user,
            assignment_id=self.request.query_params.get('assignment_id'),
            student_id=self.request.query_params.get('student_id'),
            batch_id=self.request.query_params.get('batch_id'),
            branch_id=self.request.query_params.get('branch_id'),
        )

    def perform_create(self, serializer):
        AssignmentService.submit_assignment(
            student=self.request.user,
            assignment_id=serializer.validated_data['assignment'].id,
            file_url=serializer.validated_data['file_url'],
        )

    @action(detail=True, methods=['post'], url_path='evaluate')
    def evaluate(self, request, pk=None):
        marks = request.data.get('marks_obtained')
        feedback = request.data.get('feedback', '')
        if marks is None:
            return Response({"detail": "marks_obtained is required."}, status=status.HTTP_400_BAD_REQUEST)

        submission = AssignmentService.evaluate_submission(
            evaluator=request.user,
            submission_id=pk,
            marks_obtained=float(marks),
            feedback=feedback,
        )
        return Response(SubmissionSerializer(submission).data)


class ExamViewSet(viewsets.ModelViewSet):
    serializer_class = ExamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamService.filter_exams(
            self.request.user,
            batch_id=self.request.query_params.get('batch_id'),
            subject_id=self.request.query_params.get('subject_id'),
            branch_id=self.request.query_params.get('branch_id'),
        )

    @action(detail=False, methods=['get'], url_path='batch-report')
    def batch_report(self, request):
        batch_id = request.query_params.get('batch_id')
        if not batch_id:
            return Response({"detail": "batch_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ExamService.batch_exam_report(request.user, str(batch_id)))

    def perform_create(self, serializer):
        ExamService.create_exam(
            actor=self.request.user,
            data=serializer.validated_data,
        )

    @action(detail=True, methods=['post'], url_path='publish-results')
    def publish_results(self, request, pk=None):
        results_data = request.data.get('results', [])
        results = ExamService.publish_exam_results(
            actor=request.user,
            exam_id=pk,
            results_data=results_data,
        )
        return Response({
            "count": len(results),
            "results": ResultSerializer(results, many=True).data
        })


class ExamQuestionPaperViewSet(viewsets.ModelViewSet):
    queryset = ExamQuestionPaper.objects.filter(is_deleted=False).select_related('exam')
    serializer_class = ExamQuestionPaperSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        ExamService.attach_question_paper(
            actor=self.request.user,
            exam_id=serializer.validated_data['exam'].id,
            title=serializer.validated_data['title'],
            paper_url=serializer.validated_data['paper_url'],
        )


class ResultViewSet(viewsets.ModelViewSet):
    serializer_class = ResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ExamService.filter_results(
            self.request.user,
            exam_id=self.request.query_params.get('exam_id'),
            student_id=self.request.query_params.get('student_id'),
            batch_id=self.request.query_params.get('batch_id'),
            branch_id=self.request.query_params.get('branch_id'),
        )
