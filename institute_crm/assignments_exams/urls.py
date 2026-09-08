from django.urls import path, include
from rest_framework.routers import DefaultRouter
from assignments_exams.views import (
    AssignmentViewSet, SubmissionViewSet, ExamViewSet, 
    ExamQuestionPaperViewSet, ResultViewSet
)

router = DefaultRouter()
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', SubmissionViewSet, basename='submission')
router.register(r'exams', ExamViewSet, basename='exam')
router.register(r'question-papers', ExamQuestionPaperViewSet, basename='questionpaper')
router.register(r'results', ResultViewSet, basename='result')

urlpatterns = [
    path('', include(router.urls)),
]
