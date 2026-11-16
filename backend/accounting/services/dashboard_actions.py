"""Database actions behind dashboard rollover and visible-page report downloads."""
import io
import zipfile
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from accounting.models import Client, Cost, Payment, Remittance
from accounting.services.calculations import calculate_billable_costs, calculate_cost_ceiling
from accounting.services.rollovers import prepare_rollover
from accounting.services.remittance import save_remittance_report


def period_bounds(year, month):
    if type(year) is not int or type(month) is not int or not 1 <= year <= 9998:
        raise ValueError("Invalid reporting month.")
    start = date(year, month, 1)
    end = date(year + (month == 12), 1 if month == 12 else month + 1, 1)
    return start, end


@transaction.atomic
def rollover_clients(year, month, client_ids=None):
    """Move only excess unbilled costs; billing occurs when a report is saved."""
    start, end = period_bounds(year, month)
    query = Client.objects.select_for_update().order_by("pk")
    if client_ids is not None:
        query = query.filter(pk__in=client_ids)
    clients = list(query)
    if client_ids is not None and len(clients) != len(client_ids):
        raise ValueError("One or more selected clients no longer exist.")
    finalized = set(Remittance.objects.filter(
        client_id__in=[client.pk for client in clients], report_period=start
    ).values_list("client_id", flat=True))
    changed_clients = changed_costs = 0
    for client in clients:
        if client.pk in finalized:
            continue
        recoveries = Payment.objects.filter(
            account__client=client, payment_date__gte=start, payment_date__lt=end
        ).aggregate(total=Sum("payment_amount"))["total"] or Decimal("0.00")
        # Include overdue costs from earlier periods, but never future costs.
        costs = list(Cost.objects.select_for_update().filter(
            account__client=client, billed=False, due_date__lt=end
        ).order_by("cost_date", "cost_id"))
        ceiling = calculate_cost_ceiling(recoveries)
        if sum((cost.cost_amount for cost in costs), Decimal("0.00")) <= ceiling:
            continue
        proposal = calculate_billable_costs([
            {"CostID": cost.pk, "CostDate": cost.cost_date,
             "CostAmount": cost.cost_amount, "Billed": cost.billed,
             "DueDate": cost.due_date}
            for cost in costs
        ], ceiling)
        # Michael's helper validates duplicate IDs and moves deferred costs to
        # the month AFTER the reporting period, even for older overdue costs.
        updates = prepare_rollover(proposal, report_period=start)
        deferred_dates = {
            item["CostID"]: item["DueDate"] for item in updates if not item["Billed"]
        }
        deferred = [cost for cost in costs if cost.pk in deferred_dates]
        for cost in deferred:
            cost.due_date = deferred_dates[cost.pk]
        if deferred:
            Cost.objects.bulk_update(deferred, ["due_date"])
            changed_clients += 1
            changed_costs += len(deferred)
    return {"clients_rolled": changed_clients, "costs_rolled": changed_costs}


@transaction.atomic
def reports_for_clients(year, month, client_ids):
    """Return a ZIP of distinct PDFs, preserving reports already generated."""
    start, _ = period_bounds(year, month)
    # Lock in ID order, matching the other report/import actions.
    clients = list(Client.objects.select_for_update().filter(pk__in=client_ids).order_by("pk"))
    if len(clients) != len(client_ids):
        raise ValueError("One or more clients on this page no longer exist.")
    existing = {
        report.client_id: report for report in Remittance.objects.filter(
            client_id__in=client_ids, report_period=start
        )
    }
    missing_rates = [client.client_name for client in clients
                     if client.pk not in existing and client.commission_rate is None]
    if missing_rates:
        raise ValueError("Set a commission rate before generating reports for: " + ", ".join(missing_rates))
    if any(not report.pdf_file for report in existing.values()):
        raise ValueError("A saved report on this page is missing its PDF. No new reports were generated.")

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for client_id in client_ids:
            report = existing.get(client_id)
            if report is None:
                report = save_remittance_report(client_id, year, month)
            archive.writestr(
                f"remittance_{client_id}_{year:04d}_{month:02d}.pdf",
                bytes(report.pdf_file),
            )
    # ZIP construction completes inside the transaction. Any failure rolls back
    # every newly created report, billed cost, and due-date change in this batch.
    return output.getvalue()
