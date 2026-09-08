from django.db import models
from institute_crm.utils import BaseModel
from accounts.models import User, Branch

class Lead(BaseModel):
    STAGE_NEW = 'New'
    STAGE_CONTACTED = 'Contacted'
    STAGE_INTERESTED = 'Interested'
    STAGE_DEMO_SCHEDULED = 'Demo Scheduled'
    STAGE_DEMO_ATTENDED = 'Demo Attended'
    STAGE_ADMISSION_PENDING = 'Admission Pending'
    STAGE_ADMITTED = 'Admitted'
    STAGE_LOST = 'Lost'

    STAGE_CHOICES = [
        (STAGE_NEW, 'New'),
        (STAGE_CONTACTED, 'Contacted'),
        (STAGE_INTERESTED, 'Interested'),
        (STAGE_DEMO_SCHEDULED, 'Demo Scheduled'),
        (STAGE_DEMO_ATTENDED, 'Demo Attended'),
        (STAGE_ADMISSION_PENDING, 'Admission Pending'),
        (STAGE_ADMITTED, 'Admitted'),
        (STAGE_LOST, 'Lost'),
    ]

    SOURCE_CHOICES = [
        ('WEBSITE', 'Website'),
        ('WALK_IN', 'Walk In'),
        ('REFERRAL', 'Referral'),
        ('SOCIAL_MEDIA', 'Social Media'),
        ('CAMPAIGN', 'Campaign'),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, db_index=True)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='leads')
    course = models.ForeignKey('academics.Course', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    batch = models.ForeignKey('academics.Batch', on_delete=models.SET_NULL, null=True, blank=True, related_name='leads')
    target_course = models.CharField(max_length=150, blank=True, null=True)
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='WALK_IN')
    stage = models.CharField(max_length=50, choices=STAGE_CHOICES, default=STAGE_NEW, db_index=True)
    lead_owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_leads')
    notes = models.TextField(blank=True, null=True)
    demo_schedule_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Lead: {self.name} [{self.stage}] - {self.branch.name}"


class FollowUp(BaseModel):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='follow_ups')
    counselor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='counselor_followups')
    scheduled_date = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"FollowUp for {self.lead.name} on {self.scheduled_date}"


class CounsellingNote(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='counselling_notes')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.TextField()

    def __str__(self):
        return f"Note by {self.author.username} on {self.lead.name}"


class Admission(BaseModel):
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='admissions')
    student_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admissions')
    course = models.ForeignKey('academics.Course', on_delete=models.CASCADE)
    batch = models.ForeignKey('academics.Batch', on_delete=models.CASCADE)
    admission_date = models.DateField(auto_now_add=True)
    agreed_fee = models.DecimalField(max_digits=10, decimal_places=2)
    admission_number = models.CharField(max_length=50, unique=True, db_index=True)

    def __str__(self):
        return f"Admission: {self.admission_number} - {self.student_user.get_full_name()}"


class Visitor(BaseModel):
    visitor_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    purpose = models.CharField(max_length=200)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    host_staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    check_in = models.DateTimeField(auto_now_add=True)
    check_out = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Visitor: {self.visitor_name} ({self.purpose})"
