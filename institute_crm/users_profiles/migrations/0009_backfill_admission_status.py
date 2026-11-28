"""Backfill admission_status for existing student records (safe, no destructive change)."""
from django.db import migrations


def backfill(apps, schema_editor):
    StudentProfile = apps.get_model("users_profiles", "StudentProfile")
    CourseEnrolment = apps.get_model("academics", "CourseEnrolment")
    for profile in StudentProfile.objects.filter(is_deleted=False, admission_status="PENDING"):
        enrolled = CourseEnrolment.objects.filter(
            student_id=profile.user_id, is_deleted=False, status="ACTIVE",
        ).exists() or profile.batch_id
        profile.admission_status = "ENROLLED" if enrolled else "ACTIVE"
        profile.save(update_fields=["admission_status"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [("users_profiles", "0008_studentprofile_admission_status_and_more")]
    operations = [migrations.RunPython(backfill, noop)]
