from rest_framework import serializers
from assignments_exams.models import Assignment, Submission, Exam, ExamQuestionPaper, Result

class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    evaluator_name = serializers.CharField(source='evaluated_by.get_full_name', read_only=True)

    class Meta:
        model = Submission
        fields = ['id', 'assignment', 'student', 'student_name', 'submitted_at', 'file_url', 'marks_obtained', 'feedback', 'evaluated_by', 'evaluator_name']


class AssignmentSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(source='subject.title', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    creator_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    submissions = SubmissionSerializer(many=True, read_only=True)

    class Meta:
        model = Assignment
        fields = ['id', 'subject', 'subject_title', 'batch', 'batch_name', 'title', 'description', 'total_marks', 'due_date', 'file_url', 'created_by', 'creator_name', 'submissions']


class ExamQuestionPaperSerializer(serializers.ModelSerializer):
    uploader_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = ExamQuestionPaper
        fields = ['id', 'exam', 'title', 'paper_url', 'created_by', 'uploader_name']


class ResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Result
        fields = ['id', 'exam', 'student', 'student_name', 'marks_obtained', 'grade', 'remarks']


class ExamSerializer(serializers.ModelSerializer):
    subject_title = serializers.CharField(source='subject.title', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    results = ResultSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'subject', 'subject_title', 'batch', 'batch_name', 'title', 'total_marks', 'passing_marks', 'exam_date', 'results']
