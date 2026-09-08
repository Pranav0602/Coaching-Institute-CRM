from rest_framework import serializers
from users_profiles.models import StudentProfile, TeacherProfile, ParentProfile, StudentParent
from accounts.serializers import UserSerializer

class StudentProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)
    batch_name = serializers.CharField(source='batch.name', read_only=True)

    class Meta:
        model = StudentProfile
        fields = [
            'id', 'user', 'user_detail', 'enrollment_number', 'dob', 
            'gender', 'blood_group', 'address', 'emergency_contact', 
            'batch', 'batch_name', 'documents_url', 'created_at'
        ]


class TeacherProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = TeacherProfile
        fields = ['id', 'user', 'user_detail', 'employee_id', 'qualification', 'specialization', 'joining_date']


class ParentProfileSerializer(serializers.ModelSerializer):
    user_detail = UserSerializer(source='user', read_only=True)

    class Meta:
        model = ParentProfile
        fields = ['id', 'user', 'user_detail', 'occupation', 'relationship_type']
