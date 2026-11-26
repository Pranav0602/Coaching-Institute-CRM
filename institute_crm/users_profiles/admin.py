from django.contrib import admin

from users_profiles.models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['reg_no', 'user', 'batch', 'secondary_phone', 'agreed_fee']
    search_fields = [
        'reg_no',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__phone',
        'secondary_phone',
    ]
    list_filter = ['gender', 'batch']
