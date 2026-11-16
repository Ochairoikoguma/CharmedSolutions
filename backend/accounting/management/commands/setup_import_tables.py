from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from accounting.import_models import ImportBatch, ImportRow


class Command(BaseCommand):
    help = "Create the two new import audit tables; leave existing tables and records intact."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError("Connect to MySQL before setting up import tables.")
        existing = set(connection.introspection.table_names())
        for model in (ImportBatch, ImportRow):
            if model._meta.db_table in existing:
                self.stdout.write(f"Already exists: {model._meta.db_table}")
                continue
            with connection.schema_editor() as editor:
                editor.create_model(model)
            self.stdout.write(self.style.SUCCESS(f"Created: {model._meta.db_table}"))
