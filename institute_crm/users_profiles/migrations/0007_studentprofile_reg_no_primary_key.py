from django.db import migrations, models
import django.db.models.deletion
from django.db.migrations.exceptions import IrreversibleError


def copy_parent_student_registration_numbers(apps, schema_editor):
    connection = schema_editor.connection
    quote = schema_editor.quote_name
    profile_table = quote("users_profiles_studentprofile")
    link_table = quote("users_profiles_studentparent")

    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {link_table} AS link "
            f"SET student_reg_no = profile.reg_no "
            f"FROM {profile_table} AS profile "
            f"WHERE link.student_id = profile.id"
        )
        cursor.execute(
            f"SELECT COUNT(*) FROM {link_table} WHERE student_reg_no IS NULL"
        )
        missing = cursor.fetchone()[0]
    if missing:
        raise RuntimeError(
            f"Cannot switch StudentProfile keys: {missing} parent links could not be mapped."
        )


def switch_student_profile_primary_key(apps, schema_editor):
    connection = schema_editor.connection
    if connection.vendor != "postgresql":
        raise RuntimeError("This primary-key migration requires PostgreSQL.")

    profile_model = apps.get_model("users_profiles", "StudentProfile")
    profile_table_name = profile_model._meta.db_table
    profile_table = schema_editor.quote_name(profile_table_name)
    quote = schema_editor.quote_name

    with connection.cursor() as cursor:
        cursor.execute(
            f"SELECT COUNT(*) FROM {profile_table} "
            "WHERE reg_no IS NULL OR BTRIM(reg_no) = ''"
        )
        invalid_registration_numbers = cursor.fetchone()[0]
        if invalid_registration_numbers:
            raise RuntimeError(
                "Cannot use reg_no as the primary key while blank registration numbers exist."
            )

        # Don't remove the UUID key if a database relation still references it.
        for table_name in connection.introspection.table_names(cursor):
            for constraint in connection.introspection.get_constraints(cursor, table_name).values():
                if constraint.get("foreign_key") == (profile_table_name, "id"):
                    raise RuntimeError(
                        f"Cannot drop StudentProfile.id; {table_name} still references it."
                    )

        constraints = connection.introspection.get_constraints(cursor, profile_table_name)
        primary_keys = [
            name for name, info in constraints.items() if info.get("primary_key")
        ]
        if len(primary_keys) != 1:
            raise RuntimeError("Could not identify the existing StudentProfile primary key.")

        cursor.execute(
            f"ALTER TABLE {profile_table} DROP CONSTRAINT {quote(primary_keys[0])}"
        )
        cursor.execute(f"ALTER TABLE {profile_table} DROP COLUMN {quote('id')}")
        cursor.execute(
            f"ALTER TABLE {profile_table} ADD PRIMARY KEY ({quote('reg_no')})"
        )


def prevent_reverse(apps, schema_editor):
    raise IrreversibleError(
        "StudentProfile UUID primary-key values are removed by this migration. "
        "Restore a pre-migration database backup to reverse it."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("users_profiles", "0006_studentprofile_academic_branch_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="studentparent",
            name="student_reg_no",
            field=models.ForeignKey(
                blank=True,
                db_column="student_reg_no",
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="+",
                to="users_profiles.studentprofile",
                to_field="reg_no",
            ),
        ),
        migrations.RunPython(copy_parent_student_registration_numbers),
        migrations.RemoveField(
            model_name="studentparent",
            name="student",
        ),
        migrations.RenameField(
            model_name="studentparent",
            old_name="student_reg_no",
            new_name="student",
        ),
        migrations.AlterField(
            model_name="studentparent",
            name="student",
            field=models.ForeignKey(
                db_column=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="parent_links",
                to="users_profiles.studentprofile",
                to_field="reg_no",
            ),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    switch_student_profile_primary_key,
                    prevent_reverse,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name="studentprofile",
                    name="id",
                ),
                migrations.AlterField(
                    model_name="studentprofile",
                    name="reg_no",
                    field=models.CharField(
                        max_length=50,
                        primary_key=True,
                        serialize=False,
                        verbose_name="REG NO",
                    ),
                ),
                migrations.AlterField(
                    model_name="studentparent",
                    name="student",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="parent_links",
                        to="users_profiles.studentprofile",
                    ),
                ),
                migrations.AlterModelOptions(
                    name="studentprofile",
                    options={"ordering": ["reg_no"]},
                ),
            ],
        ),
    ]
