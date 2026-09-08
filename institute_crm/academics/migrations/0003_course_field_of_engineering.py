# Generated for field_of_engineering on Course model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("academics", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="field_of_engineering",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Mechanical CAD/CAM/CAE", "Mechanical CAD/CAM/CAE"),
                    ("Civil CAD", "Civil CAD"),
                    ("Electrical CAD", "Electrical CAD"),
                    ("Design & BIM", "Design & BIM"),
                    ("Data Science & AI/ML", "Data Science & AI/ML"),
                    ("IT & Software Development", "IT & Software Development"),
                    ("Cloud Computing", "Cloud Computing"),
                ],
                max_length=50,
                null=True,
            ),
        ),
    ]
