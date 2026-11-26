"""
Transition the legacy ``ADMISSION_COUNSELOR`` role to ``RECEPTIONIST``.

Existing user rows are re-pointed at the Receptionist role so nobody loses access when
the role is renamed. The old Role row is kept (renamed "Legacy") rather than deleted:
foreign keys, audit trails and older clients may still reference its code, and keeping
it makes the migration reversible in principle.
"""
from django.db import migrations


def forwards(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    User = apps.get_model("accounts", "User")

    receptionist, _ = Role.objects.get_or_create(
        code="RECEPTIONIST",
        defaults={
            "name": "Receptionist",
            "description": (
                "Front desk: lead pipeline, counselling follow-ups, direct student "
                "onboarding and full student profiles."
            ),
        },
    )

    legacy = Role.objects.filter(code="ADMISSION_COUNSELOR").first()
    if legacy is None:
        return

    User.objects.filter(role=legacy).update(role=receptionist)

    legacy.name = "Admission Counselor (Legacy)"
    legacy.description = (
        "Deprecated alias for RECEPTIONIST; retained for backward compatibility."
    )
    legacy.save(update_fields=["name", "description"])


def backwards(apps, schema_editor):
    """No-op: original per-user counselor assignments cannot be reconstructed."""


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_alter_user_options"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
