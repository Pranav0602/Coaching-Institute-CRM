from django.contrib import admin
from academics.models import Course, Subject, Batch, CourseEnrolment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'field_of_engineering', 'duration_months', 'total_fee']
    search_fields = ['code', 'title']
    list_filter = ['field_of_engineering']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'title', 'course']
    search_fields = ['code', 'title', 'course__title', 'course__code']
    list_filter = ['course']


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'course', 'branch', 'start_date', 'end_date', 'max_capacity']
    search_fields = ['code', 'name', 'course__title', 'branch__name']
    list_filter = ['branch', 'course']


@admin.register(CourseEnrolment)
class CourseEnrolmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'get_reg_no', 'course', 'batch', 'get_softwares', 'status', 'enrolled_at']
    search_fields = [
        'student__username',
        'student__first_name',
        'student__last_name',
        'student__student_profile__reg_no',
        'course__title',
        'course__code',
        'batch__name',
    ]
    list_filter = ['status', 'course', 'batch__branch']

    @admin.display(description="REG NO")
    def get_reg_no(self, obj):
        profile = getattr(obj.student, 'student_profile', None)
        return getattr(profile, 'reg_no', None)

    @admin.display(description="Softwares")
    def get_softwares(self, obj):
        return ", ".join(obj.softwares) if obj.softwares else "—"
