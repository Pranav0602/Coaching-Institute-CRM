from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users_profiles", "0003_studentprofile_guardian_and_course"),
    ]

    operations = [
        migrations.AlterField(
            model_name="studentprofile",
            name="reg_no",
            field=models.CharField(
                db_index=True, max_length=50, unique=True, verbose_name="REG NO"
            ),
        ),
    ]
