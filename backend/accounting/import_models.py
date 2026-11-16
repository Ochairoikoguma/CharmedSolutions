"""Import audit tables; created explicitly by setup_import_tables."""
from django.db import models


class ImportBatch(models.Model):
    batch_id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=255)
    reporting_month = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    row_count = models.PositiveIntegerField()

    class Meta:
        db_table = "ImportBatch"
        managed = False


class ImportRow(models.Model):
    row_id = models.AutoField(primary_key=True)
    batch = models.ForeignKey(ImportBatch, on_delete=models.PROTECT, related_name="rows")
    source_row = models.PositiveIntegerField()
    # Retain source values even if a client/account is subsequently renamed.
    source = models.JSONField()
    # IDs refer to existing unmanaged tables, without changing their schemas.
    payment_id = models.PositiveIntegerField(null=True)
    cost_id = models.PositiveIntegerField(null=True)

    class Meta:
        db_table = "ImportRow"
        managed = False
        unique_together = (("batch", "source_row"),)
