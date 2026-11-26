from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0005_courseenrolment_softwares"),
        ("users_profiles", "0002_rename_enrollment_number_studentprofile_reg_no_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentprofile",
            name="course",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="direct_students",
                to="academics.course",
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="guardian_name",
            field=models.CharField(blank=True, max_length=150, null=True),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="guardian_phone",
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="guardian_relationship",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
