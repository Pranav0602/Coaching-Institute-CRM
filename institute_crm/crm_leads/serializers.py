from rest_framework import serializers
from crm_leads.models import Lead, FollowUp, CounsellingNote, Admission, Visitor
from accounts.serializers import BranchSerializer, UserSerializer

class LeadSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    lead_owner_name = serializers.CharField(source='lead_owner.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)
    batch_code = serializers.CharField(source='batch.code', read_only=True)

    class Meta:
        model = Lead
        fields = [
            'id', 'name', 'email', 'phone', 'branch', 'branch_name',
            'course', 'course_title', 'course_code',
            'batch', 'batch_name', 'batch_code',
            'target_course', 'source', 'stage', 'lead_owner', 'lead_owner_name',
            'notes', 'demo_schedule_date', 'created_at', 'updated_at'
        ]


class FollowUpSerializer(serializers.ModelSerializer):
    counselor_name = serializers.CharField(source='counselor.get_full_name', read_only=True)

    class Meta:
        model = FollowUp
        fields = ['id', 'lead', 'counselor', 'counselor_name', 'scheduled_date', 'status', 'remarks', 'created_at']


class CounsellingNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = CounsellingNote
        fields = ['id', 'lead', 'author', 'author_name', 'note', 'created_at']


class AdmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student_user.get_full_name', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)

    class Meta:
        model = Admission
        fields = [
            'id', 'lead', 'student_user', 'student_name', 'course', 
            'course_title', 'batch', 'batch_name', 'admission_date', 
            'agreed_fee', 'admission_number'
        ]


class VisitorSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    host_staff_name = serializers.CharField(source='host_staff.get_full_name', read_only=True)

    class Meta:
        model = Visitor
        fields = [
            'id', 'visitor_name', 'phone', 'purpose', 'branch', 
            'branch_name', 'host_staff', 'host_staff_name', 
            'check_in', 'check_out'
        ]


class LeadConvertSerializer(serializers.Serializer):
    course_id = serializers.UUIDField()
    batch_id = serializers.UUIDField()
    agreed_fee = serializers.DecimalField(max_digits=10, decimal_places=2)
