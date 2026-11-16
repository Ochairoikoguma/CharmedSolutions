"""Exercise dashboard actions with temporary records and roll everything back."""
import io
import json
import uuid
import zipfile
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import RequestFactory

from accounting.models import Client, CollectionAccount, Payment, Cost, Remittance
from accounting.import_models import ImportBatch, ImportRow
from accounting.dashboard_action_views import rollover_dashboard, download_page_reports
from accounting.services.csv_import import active_reporting_period
from accounting.services.dashboard_actions import reports_for_clients
from accounting.services.remittance import build_remittance_pdf
from accounting.views import dashboard_data


class Command(BaseCommand):
    help = "Verify rollover and bulk PDF actions; all synthetic records roll back."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError("Connect to MySQL first.")
        models = (Client, CollectionAccount, Payment, Cost, Remittance, ImportBatch, ImportRow)
        counts_before = [model.objects.count() for model in models]
        period_before = active_reporting_period()
        # Old dates keep existing imported transactions outside this test period.
        period, following = date(1900, 11, 1), date(1900, 12, 1)
        token = uuid.uuid4().hex[:12]
        factory = RequestFactory()

        def post(view, **data):
            return view(factory.post("/", json.dumps({"year": 1900, "month": 11, **data}), content_type="application/json"))

        with transaction.atomic():
            try:
                ImportBatch.objects.create(filename="TEMP action verification", reporting_month=period, row_count=0)

                def make_client(suffix, rate="25.00", payment="100.00"):
                    client = Client.objects.create(client_name=f"ACTION TEST {token} {suffix}", commission_rate=rate)
                    account = CollectionAccount.objects.create(account_number=f"T{token}{suffix}", client=client, debtor_name="Temporary debtor")
                    if payment is not None:
                        Payment.objects.create(account=account, payment_date=date(1900, 11, 5), payment_amount=payment)
                    return client, account

                def make_cost(account, amount, day=1, due=period, billed=False):
                    return Cost.objects.create(account=account, cost_date=date(1900, 10, day),
                        cost_amount=amount, cost_description="Temporary cost", billed=billed, due_date=due)

                a, aa = make_client("A")
                b, ba = make_client("B")
                c, ca = make_client("C", rate=None, payment=None)
                d, da = make_client("D", rate=None)
                oldest = make_cost(aa, "18.00", 1, date(1900, 9, 1))
                oversized = make_cost(aa, "9.00", 2, date(1900, 10, 1))
                fitting = make_cost(aa, "2.00", 3)
                billed = make_cost(aa, "99.00", 4, billed=True)
                future = make_cost(aa, "999.00", 5, following)
                below_cap = make_cost(ba, "5.00")
                zero_recovery = make_cost(ca, "7.00")

                assert rollover_dashboard(factory.get("/")).status_code == 405
                assert download_page_reports(factory.get("/")).status_code == 405
                assert post(rollover_dashboard, mode="selected", client_ids=[True]).status_code == 400
                assert post(download_page_reports, client_ids=[a.pk, a.pk]).status_code == 400
                assert post(download_page_reports, client_ids=list(range(1, 12))).status_code == 400
                stale = download_page_reports(factory.post("/", json.dumps({"year": 1900, "month": 10, "client_ids": [a.pk]}), content_type="application/json"))
                assert stale.status_code == 400
                self.stdout.write("PASS: GET, invalid IDs, oversized pages, and stale months rejected.")

                response = post(rollover_dashboard, mode="selected", client_ids=[a.pk, b.pk])
                assert response.status_code == 200, response.content
                assert json.loads(response.content) == {"clients_rolled": 1, "costs_rolled": 1}
                for cost in (oldest, oversized, fitting, billed, future, below_cap, zero_recovery):
                    cost.refresh_from_db()
                assert oversized.due_date == following and not oversized.billed
                assert oldest.due_date == date(1900, 9, 1) and not oldest.billed
                assert fitting.due_date == period and not fitting.billed
                assert billed.billed and billed.due_date == period
                assert future.due_date == following and not future.billed
                assert below_cap.due_date == period and not below_cap.billed
                assert zero_recovery.due_date == period
                assert oversized.cost_date == date(1900, 10, 2)
                repeat = post(rollover_dashboard, mode="selected", client_ids=[a.pk])
                assert json.loads(repeat.content)["costs_rolled"] == 0
                self.stdout.write("PASS: Selected rollover preserves billing, original dates, fitting, unselected, and future costs.")

                response = post(rollover_dashboard, mode="all")
                assert response.status_code == 200, response.content
                zero_recovery.refresh_from_db()
                assert zero_recovery.due_date == following and not zero_recovery.billed
                self.stdout.write("PASS: Roll Over All handles zero recoveries without requiring a commission rate.")

                response = dashboard_data(factory.get("/api/dashboard/", {"year": 1900, "month": 11}))
                row = next(row for row in json.loads(response.content)["clients"] if row["id"] == a.pk)
                assert Decimal(row["applied_costs"]) == Decimal("20.00")
                assert Decimal(row["deferred_costs"]) == Decimal("0.00")
                self.stdout.write("PASS: Dashboard clears the excess-cost flag and includes older retained costs.")

                report_count = Remittance.objects.count()
                response = post(download_page_reports, client_ids=[a.pk, d.pk])
                assert response.status_code == 400
                assert Remittance.objects.count() == report_count
                oldest.refresh_from_db()
                assert not oldest.billed
                self.stdout.write("PASS: Missing rates block the whole page before billing or report creation.")

                # Fail the second PDF to verify the outer transaction rolls back
                # the first report and its costs as well.
                calls = 0
                def fail_second(data):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        raise ValueError("Synthetic second-PDF failure")
                    return build_remittance_pdf(data)
                with patch("accounting.services.remittance.build_remittance_pdf", side_effect=fail_second):
                    response = post(download_page_reports, client_ids=[a.pk, b.pk])
                    assert response.status_code == 400
                assert Remittance.objects.count() == report_count
                oldest.refresh_from_db()
                below_cap.refresh_from_db()
                assert not oldest.billed and not below_cap.billed
                self.stdout.write("PASS: A failed batch rolls back earlier PDFs and billing changes.")

                response = post(download_page_reports, client_ids=[a.pk, b.pk])
                assert response.status_code == 200, response.content
                assert response["Content-Type"] == "application/zip"
                with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                    assert set(archive.namelist()) == {f"remittance_{a.pk}_1900_11.pdf", f"remittance_{b.pk}_1900_11.pdf"}
                    originals = {name: archive.read(name) for name in archive.namelist()}
                    assert all(content.startswith(b"%PDF") for content in originals.values())
                assert Remittance.objects.get(client=a, report_period=period).net_remittance == Decimal("55.00")
                assert Remittance.objects.get(client=b, report_period=period).net_remittance == Decimal("70.00")
                assert not Remittance.objects.filter(client__in=[c, d], report_period=period).exists()
                for cost in (oldest, fitting, below_cap, oversized, future):
                    cost.refresh_from_db()
                assert oldest.billed and fitting.billed and below_cap.billed
                assert not oversized.billed and not future.billed
                self.stdout.write("PASS: ZIP contains only requested clients; saved PDF totals and billed costs agree.")

                a.commission_rate = Decimal("30.00")
                a.save(update_fields=["commission_rate"])
                again = reports_for_clients(1900, 11, [a.pk, b.pk])
                with zipfile.ZipFile(io.BytesIO(again)) as archive:
                    assert {name: archive.read(name) for name in archive.namelist()} == originals
                assert Remittance.objects.count() == report_count + 2
                assert json.loads(post(rollover_dashboard, mode="selected", client_ids=[a.pk]).content)["costs_rolled"] == 0
                self.stdout.write("PASS: Repeated downloads reuse original PDFs; finalized reports remain unchanged.")
            finally:
                transaction.set_rollback(True)

        assert counts_before == [model.objects.count() for model in models]
        assert active_reporting_period() == period_before
        self.stdout.write(self.style.SUCCESS("PASS: Test records rolled back; active reporting month restored."))
