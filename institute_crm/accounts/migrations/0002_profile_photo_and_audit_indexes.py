"""Profile photo uploads, password-rotation tracking, and query indexes.

Adds:
  * ``User.profile_photo``       - ImageField for avatars uploaded through the profile page.
  * ``User.password_changed_at`` - audit stamp for self-service password changes.
  * Composite indexes for the two hottest queries: branch/role user listings and
    "history of this record" audit lookups.

``User.profile_picture`` is kept (now documented as the external/mirrored URL) so existing
seeded avatars keep working; ``User.profile_photo_url`` resolves the two.

Backwards compatible: every added column is nullable, so this applies cleanly to a
populated database with no data migration.
"""
import accounts.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="profile_photo",
            field=models.ImageField(
                blank=True,
                help_text="Uploaded avatar. Takes precedence over profile_picture.",
                max_length=500,
                null=True,
                upload_to=accounts.models.profile_photo_upload_path,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="password_changed_at",
            field=models.DateTimeField(
                blank=True,
                help_text=(
                    "Last successful self-service password change; used for audit and "
                    "to prompt rotation of seeded temporary passwords."
                ),
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="profile_picture",
            field=models.URLField(
                blank=True,
                help_text="Externally hosted avatar URL (S3 mirror or identity-provider avatar).",
                max_length=500,
                null=True,
            ),
        ),
        migrations.AlterModelOptions(
            name="user",
            options={
                "ordering": ["first_name", "last_name", "username"],
                "verbose_name": "user",
                "verbose_name_plural": "users",
            },
        ),
        migrations.AlterModelOptions(
            name="branch",
            options={"ordering": ["name"], "verbose_name_plural": "Branches"},
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="action",
            field=models.CharField(db_index=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="model_name",
            field=models.CharField(db_index=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="auditlog",
            name="target_id",
            field=models.CharField(db_index=True, max_length=128),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["is_deleted", "branch", "role"], name="user_scope_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(
                fields=["model_name", "target_id", "-timestamp"],
                name="auditlog_target_idx",
            ),
        ),
    ]
