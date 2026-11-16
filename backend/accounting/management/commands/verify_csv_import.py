"""Exercise imports and PDF generation using temporary records, then roll back."""
import csv
import io
import json
import uuid
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, transaction
from django.test import RequestFactory

from accounting.models import Client, CollectionAccount, Payment, Cost, Remittance
from accounting.import_models import ImportBatch, ImportRow
from accounting.import_views import import_csv, reporting_period
from accounting.views import dashboard_data
from accounting.services.csv_import import COLUMNS, active_reporting_period, parse_simplicity_export, persist_simplicity_export
from accounting.services.remittance import save_remittance_report


class Command(BaseCommand):
    help = "Test the import/report workflow with synthetic data; always roll back."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError("Connect to MySQL first.")
        models = (Client, CollectionAccount, Payment, Cost, Remittance, ImportBatch, ImportRow)
        counts_before = [model.objects.count() for model in models]
        period_before = active_reporting_period()
        name = "CSV TEST " + uuid.uuid4().hex
        number = "CSV-" + uuid.uuid4().hex[:16]
        stream = io.StringIO(newline="")
        stream.write("simplicity_export\n")
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        writer.writerow([name, number, "D" * 250, "TRUE", "10/10/2026", "100.00", "Payment"])
        writer.writerow([name, number, "D" * 250, "FALSE", "10/5/2026", "5.00", "Mail"])
        writer.writerow([name.lower(), number, "D" * 250, "FALSE", "10/5/2026", "5.00", "Mail"])
        payload = stream.getvalue().encode()
        parsed = parse_simplicity_export(payload)
        assert len(parsed["rows"]) == 3
        factory = RequestFactory()

        for bad in (payload.replace(b"100.00", b"NaN"), payload.replace(b"TRUE", b"MAYBE"),
                    payload.replace(b"10/10/2026", b"11/10/2026")):
            try:
                parse_simplicity_export(bad)
            except ValueError:
                pass
            else:
                raise AssertionError("Invalid CSV accepted.")
        self.stdout.write("PASS: Invalid amounts, flags, and mixed months rejected.")

        with transaction.atomic():
            try:
                response = import_csv(factory.post("/api/import-csv/", {
                    "file": SimpleUploadedFile("test.csv", payload, content_type="text/csv")
                }))
                assert response.status_code == 201, response.content
                result = json.loads(response.content)
                assert (result["clients"], result["accounts"], result["payments"], result["costs"]) == (1, 1, 1, 2)
                client = Client.objects.get(client_name__iexact=name)
                assert client.commission_rate is None
                account = CollectionAccount.objects.get(account_number=number)
                assert len(account.debtor_name) == 250
                costs = Cost.objects.filter(account=account)
                assert costs.count() == 2
                assert all(not cost.billed and cost.due_date == date(2026, 10, 1) for cost in costs)
                audit = ImportRow.objects.filter(batch_id=result["batch_id"])
                assert audit.count() == 3
                assert set(audit.exclude(cost_id=None).values_list("cost_id", flat=True)) == set(costs.values_list("pk", flat=True))
                assert audit.exclude(payment_id=None).get().payment_id == Payment.objects.get(account=account).pk
                self.stdout.write("PASS: CSV saved, matching rows preserved, client matching and audit links correct.")

                period = json.loads(reporting_period(factory.get("/api/reporting-period/")).content)
                assert period == {"year": 2026, "month": 10}
                self.stdout.write("PASS: Reporting month follows the imported CSV.")

                client.commission_rate = Decimal("25.00")
                client.save(update_fields=["commission_rate"])
                response = dashboard_data(factory.get("/api/dashboard/", {"year": 2026, "month": 10}))
                row = next(row for row in json.loads(response.content)["clients"] if row["id"] == client.pk)
                assert Decimal(row["recoveries"]) == Decimal("100.00")
                assert Decimal(row["applied_costs"]) == Decimal("10.00")
                assert Decimal(row["net_remittance"]) == Decimal("65.00")
                report = save_remittance_report(client.pk, 2026, 10)
                assert bytes(report.pdf_file).startswith(b"%PDF")
                assert report.net_remittance == Decimal("65.00")
                assert costs.filter(billed=True).count() == 2
                self.stdout.write("PASS: Dashboard, saved PDF totals, and cost billing agree.")

                before_reject = [model.objects.count() for model in models]
                try:
                    persist_simplicity_export(parsed, "blocked.csv")
                except ValueError:
                    pass
                else:
                    raise AssertionError("Import changed a finalized reporting period.")
                assert before_reject == [model.objects.count() for model in models]
                self.stdout.write("PASS: Import cannot change a client/month with a saved report.")
            finally:
                transaction.set_rollback(True)

        assert counts_before == [model.objects.count() for model in models]
        assert period_before == active_reporting_period()
        self.stdout.write(self.style.SUCCESS("PASS: All test records rolled back; reporting month restored."))
