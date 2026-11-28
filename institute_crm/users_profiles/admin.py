from django.contrib import admin

from users_profiles.models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['reg_no', 'user', 'get_branch', 'course', 'batch', 'admission_status', 'get_phone', 'secondary_phone', 'agreed_fee']
    search_fields = [
        'reg_no',
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__phone',
        'secondary_phone',
        'guardian_name',
        'guardian_phone',
    ]
    list_filter = ['gender', 'batch', 'course', 'admission_status', 'is_deleted']

    @admin.display(description="Branch")
    def get_branch(self, obj):
        branch = getattr(obj.user, 'branch', None) or (obj.batch.branch if obj.batch else None)
        return getattr(branch, 'name', None)

    @admin.display(description="Phone")
    def get_phone(self, obj):
        return obj.user.phone
