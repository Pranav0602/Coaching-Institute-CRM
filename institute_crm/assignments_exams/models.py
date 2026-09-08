from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User
from academics.models import Subject, Batch

class Assignment(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='assignments')
    title = models.CharField(max_length=200)
    description = models.TextField()
    total_marks = models.PositiveIntegerField(default=100)
    due_date = models.DateTimeField(db_index=True)
    file_url = models.URLField(max_length=500, blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_assignments')

    def __str__(self):
        return f"Assignment: {self.title} [{self.batch.name}]"


class Submission(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assignment_submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    file_url = models.URLField(max_length=500)
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    feedback = models.TextField(blank=True, null=True)
    evaluated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluated_submissions')

    class Meta:
        unique_together = ('assignment', 'student')

    def __str__(self):
        return f"Submission: {self.student.username} for {self.assignment.title}"


class Exam(BaseModel):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='exams')
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='exams')
    title = models.CharField(max_length=200)
    total_marks = models.PositiveIntegerField(default=100)
    passing_marks = models.PositiveIntegerField(default=40)
    exam_date = models.DateTimeField(db_index=True)

    def __str__(self):
        return f"Exam: {self.title} ({self.batch.name})"


class ExamQuestionPaper(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='question_papers')
    title = models.CharField(max_length=200)
    paper_url = models.URLField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Paper: {self.title} for {self.exam.title}"


class Result(BaseModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='results')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='exam_results')
    marks_obtained = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=5, blank=True, null=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('exam', 'student')

    def __str__(self):
        return f"Result: {self.student.username} - {self.marks_obtained}/{self.exam.total_marks}"
