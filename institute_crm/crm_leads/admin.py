from django.contrib import admin
from crm_leads.models import Lead, FollowUp, CounsellingNote, Admission, Visitor

@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'phone', 'stage', 'branch', 'source']
    list_filter = ['stage', 'branch', 'source']
    search_fields = ['name', 'email', 'phone']

@admin.register(FollowUp)
class FollowUpAdmin(admin.ModelAdmin):
    list_display = ['lead', 'counselor', 'scheduled_date', 'status']

@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'student_user', 'course', 'batch', 'admission_date']

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    list_display = ['visitor_name', 'phone', 'purpose', 'branch', 'check_in']
