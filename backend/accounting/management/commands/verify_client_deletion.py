"""Verify deletion with synthetic clients, then roll all changes back."""
import json
import time
import uuid
from datetime import date
from unittest.mock import patch

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction
from django.middleware.csrf import CsrfViewMiddleware
from django.test import RequestFactory

from accounting.models import Client, CollectionAccount, Payment, Cost, Remittance
from accounting.import_models import ImportBatch, ImportRow
from accounting.client_delete_views import client_delete_preview, delete_client
from accounting.services.csv_import import active_reporting_period
from accounting.services.remittance import save_remittance_report


class Command(BaseCommand):
    help = "Test confirmed client deletion without retaining database changes."

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError("Connect to MySQL first.")
        models = (Client, CollectionAccount, Payment, Cost, Remittance, ImportBatch, ImportRow)
        before = [model.objects.count() for model in models]
        old_period = active_reporting_period()
        factory = RequestFactory()
        unique = uuid.uuid4().hex[:12]

        def preview(client_id):
            response = client_delete_preview(factory.get("/"), client_id)
            assert response.status_code == 200, response.content
            return json.loads(response.content)

        def request_for(token):
            return factory.post("/", json.dumps({"confirmation": token}), content_type="application/json")

        with transaction.atomic():
            try:
                batch = ImportBatch.objects.create(filename="TEMP deletion test", reporting_month=date(1900, 11, 1), row_count=4)

                def fixture(suffix, first_row):
                    client = Client.objects.create(client_name=f"DELETE TEST {unique} {suffix}", commission_rate="25.00")
                    account = CollectionAccount.objects.create(client=client, account_number=f"D{unique}{suffix}", debtor_name="Test debtor")
                    payment = Payment.objects.create(account=account, payment_date=date(1900, 11, 2), payment_amount="100.00")
                    cost = Cost.objects.create(account=account, cost_date=date(1900, 11, 3), cost_amount="5.00", cost_description="Test cost", billed=False, due_date=date(1900, 11, 1))
                    ImportRow.objects.create(batch=batch, source_row=first_row, source={"Client Full Name": client.client_name, "Trans. Amount": "100.00"}, payment_id=payment.pk)
                    ImportRow.objects.create(batch=batch, source_row=first_row+1, source={"Client Full Name": client.client_name, "Trans. Amount": "5.00"}, cost_id=cost.pk)
                    report = save_remittance_report(client.pk, 1900, 11)
                    return client, account, payment, cost, report

                a, aa, ap, ac, ar = fixture("A", 1)
                b, ba, bp, bc, br = fixture("B", 3)
                other_pdf = bytes(br.pdf_file)
                a_id = a.pk
                info = preview(a_id)
                assert info["counts"] == {"accounts": 1, "payments": 1, "costs": 1, "reports": 1}
                assert Client.objects.filter(pk=a_id).exists()
                self.stdout.write("PASS: Preview counts include associated accounts, transactions, and saved PDFs without deleting them.")

                assert delete_client(factory.get("/"), a_id).status_code == 405
                assert client_delete_preview(factory.post("/"), a_id).status_code == 405
                assert delete_client(request_for("invalid"), a_id).status_code == 400
                assert delete_client(factory.post("/", "{}", content_type="application/json"), a_id).status_code == 400
                assert delete_client(request_for(info["confirmation"]), b.pk).status_code == 400
                with patch("django.core.signing.time.time", return_value=time.time()+301):
                    assert delete_client(request_for(info["confirmation"]), a_id).status_code == 400
                request = request_for(info["confirmation"])
                blocked = CsrfViewMiddleware(lambda request: None).process_view(request, delete_client, (a_id,), {})
                assert blocked is not None and blocked.status_code == 403
                self.stdout.write("PASS: GET, missing/invalid/expired confirmations, wrong clients, and missing CSRF tokens are blocked.")

                extra = Cost.objects.create(account=aa, cost_date=date(1900, 11, 4), cost_amount="1.00", due_date=date(1900, 11, 1), billed=False)
                assert delete_client(request_for(info["confirmation"]), a_id).status_code == 409
                assert Client.objects.filter(pk=a_id).exists()
                extra.delete()
                a.client_name += " renamed"
                a.save(update_fields=["client_name"])
                assert delete_client(request_for(info["confirmation"]), a_id).status_code == 409
                a.client_name = info["name"]
                a.save(update_fields=["client_name"])
                info = preview(a_id)
                self.stdout.write("PASS: Changed names or record counts require a fresh confirmation.")

                current_counts = [model.objects.count() for model in models]
                with patch.object(Client, "delete", side_effect=DatabaseError("Synthetic delete failure")), patch("accounting.client_delete_views.logger.exception"):
                    response = delete_client(request_for(info["confirmation"]), a_id)
                assert response.status_code == 500
                assert current_counts == [model.objects.count() for model in models]
                assert "_deletion" not in ImportRow.objects.get(batch=batch, source_row=1).source
                self.stdout.write("PASS: A database failure restores the client, transactions, PDF, and import history.")

                response = delete_client(request_for(info["confirmation"]), a_id)
                assert response.status_code == 200, response.content
                assert not Client.objects.filter(pk=a_id).exists()
                for model, pk in ((CollectionAccount, aa.pk), (Payment, ap.pk), (Cost, ac.pk), (Remittance, ar.pk)):
                    assert not model.objects.filter(pk=pk).exists()
                for model, pk in ((Client, b.pk), (CollectionAccount, ba.pk), (Payment, bp.pk), (Cost, bc.pk), (Remittance, br.pk)):
                    assert model.objects.filter(pk=pk).exists()
                br.refresh_from_db()
                assert bytes(br.pdf_file) == other_pdf
                audit = ImportRow.objects.get(batch=batch, source_row=1)
                assert audit.payment_id == ap.pk
                assert audit.source["Client Full Name"] == info["name"]
                assert audit.source["_deletion"]["client_id"] == a_id
                assert "_deletion" not in ImportRow.objects.get(batch=batch, source_row=3).source
                assert ImportRow.objects.filter(batch=batch).count() == 4
                assert delete_client(request_for(info["confirmation"]), a_id).status_code == 404
                self.stdout.write("PASS: Only the confirmed client and related accounting records are deleted; other clients and import history remain.")

                empty = Client.objects.create(client_name=f"DELETE TEST {unique} EMPTY")
                empty_id = empty.pk
                empty_info = preview(empty_id)
                assert all(count == 0 for count in empty_info["counts"].values())
                assert delete_client(request_for(empty_info["confirmation"]), empty_id).status_code == 200
                self.stdout.write("PASS: Empty clients can also be deleted.")
            finally:
                transaction.set_rollback(True)

        assert before == [model.objects.count() for model in models]
        assert old_period == active_reporting_period()
        self.stdout.write(self.style.SUCCESS("PASS: All test changes rolled back; existing clients and reporting month restored."))
