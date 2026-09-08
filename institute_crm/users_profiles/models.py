from django.db import models
import uuid
from institute_crm.utils import BaseModel
from accounts.models import User

class StudentProfile(BaseModel):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    enrollment_number = models.CharField(max_length=50, unique=True, db_index=True)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='MALE')
    blood_group = models.CharField(max_length=10, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    emergency_contact = models.CharField(max_length=20, blank=True, null=True)
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    documents_url = models.JSONField(default=list, blank=True) # AWS S3 stored document URLs

    def __str__(self):
        return f"StudentProfile: {self.user.get_full_name()} ({self.enrollment_number})"


class TeacherProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=50, unique=True, db_index=True)
    qualification = models.CharField(max_length=200, blank=True, null=True)
    specialization = models.CharField(max_length=200, blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"TeacherProfile: {self.user.get_full_name()} ({self.employee_id})"


class ParentProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parent_profile')
    occupation = models.CharField(max_length=100, blank=True, null=True)
    relationship_type = models.CharField(max_length=50, default='FATHER') # FATHER, MOTHER, GUARDIAN

    def __str__(self):
        return f"ParentProfile: {self.user.get_full_name()}"


class StudentParent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='parent_links')
    parent = models.ForeignKey(ParentProfile, on_delete=models.CASCADE, related_name='student_links')
    is_primary = models.BooleanField(default=True)

    class Meta:
        unique_together = ('student', 'parent')

    def __str__(self):
        return f"{self.student.user.username} <-> {self.parent.user.username}"
