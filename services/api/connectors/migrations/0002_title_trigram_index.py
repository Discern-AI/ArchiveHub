"""A trigram index for "contains" searches over old map names (millions of rows for Great
Britain). Postgres only: SQLite skips it."""

from django.db import migrations


def forwards(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    schema_editor.execute(
        "CREATE INDEX IF NOT EXISTS connectors_datasetrow_title_trgm "
        "ON connectors_datasetrow USING gin (title_lower gin_trgm_ops)"
    )


def backwards(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP INDEX IF EXISTS connectors_datasetrow_title_trgm")


class Migration(migrations.Migration):
    dependencies = [("connectors", "0001_initial")]
    operations = [migrations.RunPython(forwards, backwards)]
