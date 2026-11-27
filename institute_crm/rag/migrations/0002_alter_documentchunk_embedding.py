from django.db import migrations
import pgvector.django


class Migration(migrations.Migration):

    dependencies = [
        ("rag", "0001_initial"),
    ]

    operations = [
        # RAG's initial migration used JSONField. The current model uses pgvector,
        # so install the extension before changing the underlying column type.
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        # Convert the existing JSON arrays through their textual representation;
        # this preserves valid 1536-element embeddings and keeps SQL/JSON nulls null.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        'ALTER TABLE "rag_documentchunk" '
                        'ALTER COLUMN "embedding" TYPE vector(1536) '
                        'USING CASE '
                        'WHEN "embedding" IS NULL OR "embedding" = \'null\'::jsonb '
                        'THEN NULL '
                        'ELSE "embedding"::text::vector(1536) END;'
                    ),
                    reverse_sql=(
                        'ALTER TABLE "rag_documentchunk" '
                        'ALTER COLUMN "embedding" TYPE jsonb '
                        'USING CASE WHEN "embedding" IS NULL THEN NULL '
                        'ELSE "embedding"::text::jsonb END;'
                    ),
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="documentchunk",
                    name="embedding",
                    field=pgvector.django.VectorField(
                        blank=True,
                        dimensions=1536,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
