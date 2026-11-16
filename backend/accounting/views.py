from django.shortcuts import render
from datetime import date
from decimal import Decimal
from django.http import HttpResponse
from .services.reports import generate_remittance_pdf
from django.views.decorators.http import require_POST
from .models import Client
from .services.remittance import save_remittance_report
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST, require_GET
from .models import Client, Remittance
from django.http import JsonResponse
import json
from decimal import InvalidOperation
from django.db import IntegrityError
from django.db.models import Sum
from .models import Payment, Cost
from accounting.services.calculations import (calculate_cost_ceiling,calculate_billable_costs,calculate_monthly_remittance,)

@require_GET
def client_list_data(request):
    """Return database clients for the frontend."""

    # Read clients alphabetically from MySQL.
    clients = Client.objects.order_by("client_name", "client_id")

    
    #An unset commission rate stays None and becomes null in JSON
    data = [
        {
            "id": client.client_id,
            "name": client.client_name,
            "rate": (
                str(client.commission_rate)
                if client.commission_rate is not None
                else None
            ),
            "created": (
                client.date_created.isoformat()
                if client.date_created
                else None
            ),
        }
        for client in clients
    ]

    #send client data without changing db records
    return JsonResponse({"clients": data})


def home(request):
    return render(request, "home.html")



def sample_remittance_download(request):

    #Tell the browser that the response contains a PDF
    response = HttpResponse(pdf_data, content_type="application/pdf")

    #Request a download and provide a filename
    response["Content-Disposition"] = (
        'attachment; filename="john_doe_sample_remittance.pdf"'
    )

    return response

# Create your views here!

@require_POST
def remittance_download(request, client_id):
    #Generate, save, and download a clients monthly report

    # Read the reporting year and month submitted by the frontend
    try:
        year = int(request.POST.get("year", ""))
        month = int(request.POST.get("month", ""))

        # validate the reporting period before generating the report
        #December needs a following January for the date filter
        if not 1 <= year <= 9998:
            raise ValueError("Invalid year.")

        date(year, month, 1)

    except (TypeError, ValueError):
        return HttpResponse(
            "Provide a valid reporting year and month.",
            status=400,
            content_type="text/plain",
        )

    #save the Pdf and totalsand mark its included costs as billed
    try:
        report = save_remittance_report(client_id, year, month)

    except Client.DoesNotExist:
        return HttpResponse("The selected client was not found.",status=404,content_type="text/plain",)

    except ValueError as error:
        #show the services explanation
        # rate or an existing report for this client and month
        return HttpResponse(str(error),status=400,content_type="text/plain",)

    #return the saved PDF as a browser download
    response = HttpResponse(bytes(report.pdf_file),content_type="application/pdf",)

    #Useclient ID and reporting period for filename
    filename = f"remittance_{client_id}_{year:04d}_{month:02d}.pdf"
    response["Content-Disposition"] = (f'attachment; filename="{filename}"')

    return response

@require_GET
def saved_remittance_download(request, report_id):
    """Download the original PDF stored for an existing report."""



    #find saved report by ID
    # if report does not exit return 404
    report = get_object_or_404(Remittance, pk=report_id)

    #if records exist without a pdf
    if not report.pdf_file:
        return HttpResponse("This report does not have a saved PDF.",status=404,content_type="text/plain",)


    
    response = HttpResponse(bytes(report.pdf_file),content_type="application/pdf",)

    
    filename = (f"remittance_{report.client_id}_"f"{report.report_period:%Y_%m}.pdf")
    response["Content-Disposition"] = (f'attachment; filename="{filename}"')
    return response

from django.shortcuts import render

def client_page(request):
    return render(request, "client.html")

@require_POST
def update_client(request, client_id):
    """Update an existing client's name and commission rate."""

    client = Client.objects.filter(pk=client_id).first()

    if client is None:
        return JsonResponse({"error": "Client not found."}, status=404)

    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON."}, status=400)

    if not isinstance(data, dict):
        return JsonResponse({"error": "Invalid request."}, status=400)

    name = data.get("name")
    raw_rate = data.get("rate")

    if not isinstance(name, str) or not name.strip():
        return JsonResponse({"error": "Client name is required."}, status=400)

    name = " ".join(name.split())

    if len(name) > 150:
        return JsonResponse({"error": "Client name is too long."}, status=400)

    try:
        rate = None if raw_rate is None or raw_rate == "" else Decimal(str(raw_rate))

        if rate is not None and (
            not rate.is_finite()
            or rate < 0
            or rate > Decimal("99.99")
            or rate != rate.quantize(Decimal("0.01"))
        ):
            raise ValueError()

    except (InvalidOperation, ValueError):
        return JsonResponse({"error": "Invalid commission rate."}, status=400)

    client.client_name = name
    client.commission_rate = rate

    try:
        client.save(update_fields=["client_name", "commission_rate"])
    except IntegrityError:
        return JsonResponse({"error": "Client name already exists."}, status=409)

    return JsonResponse({
        "id": client.client_id,
        "name": client.client_name,
        "rate": str(client.commission_rate) if client.commission_rate is not None else None
    })

@require_GET
def client_report_history(request, client_id):

    #verify that client exists
    if not Client.objects.filter(pk=client_id).exists():
        return JsonResponse({"error": "Client not found."},status=404)

    #get saved reports from db newest first
    reports = Remittance.objects.filter(client_id=client_id).order_by("-report_period", "-remittance_id")

    # Return report information without loading pdf files
    data = [
        {
            "id": report["remittance_id"],
            "period": report["report_period"].isoformat(),
            "download_url": (
                f"/reports/history/{report['remittance_id']}/download/"
            ),
        }
        for report in reports.values(
            "remittance_id",
            "report_period"
        )
    ]
    return JsonResponse({"reports": data})
@require_POST
def create_client(request):
    """Create a new client in MySQL."""

    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Invalid JSON."},
            status=400
        )

    if not isinstance(data, dict):
        return JsonResponse(
            {"error": "Invalid request."},
            status=400
        )

    name = data.get("name")
    raw_rate = data.get("rate")

    # Validate client name
    if not isinstance(name, str) or not name.strip():
        return JsonResponse(
            {"error": "Client name is required."},
            status=400
        )

    name = " ".join(name.split())

    if len(name) > 150:
        return JsonResponse(
            {"error": "Client name is too long."},
            status=400
        )

    # Commission rate is optional
    try:
        rate = (
            None if raw_rate is None or raw_rate == ""
            else Decimal(str(raw_rate))
        )

        if rate is not None and (
            not rate.is_finite()
            or rate < 0
            or rate > Decimal("99.99")
            or rate != rate.quantize(Decimal("0.01"))
        ):
            raise ValueError()

    except (InvalidOperation, ValueError):
        return JsonResponse(
            {"error": "Invalid commission rate."},
            status=400
        )

    # Save the client in MySQL
    try:
        client = Client.objects.create(
            client_name=name,
            commission_rate=rate
        )

    except IntegrityError:
        return JsonResponse(
            {"error": "Client name already exists or could not be saved."},
            status=409
        )

    # Return the newly created client
    return JsonResponse({
        "id": client.client_id,
        "name": client.client_name,
        "rate": (
            str(client.commission_rate)
            if client.commission_rate is not None
            else None
        ),
        "created": client.date_created.isoformat()
    }, status=201)


@require_GET
def dashboard_data(request):
    """Return read-only monthly financial previews."""

    try:
        year = int(request.GET.get("year", ""))
        month = int(request.GET.get("month", ""))

        if not 1 <= year <= 9998:
            raise ValueError()

        period_start = date(year, month, 1)

        if month == 12:
            period_end = date(year + 1, 1, 1)
        else:
            period_end = date(year, month + 1, 1)

    except (ValueError, TypeError):
        return JsonResponse(
            {"error": "Invalid reporting period."},
            status=400
        )

        # Keep individual payment amounts for per-payment rounding.
    payments_by_client = {}

    payment_rows = Payment.objects.filter(
        payment_date__gte=period_start,
        payment_date__lt=period_end,
    ).values("account__client_id", "payment_amount")

    for row in payment_rows:
        client_id = row["account__client_id"]
        payments_by_client.setdefault(client_id, []).append(row["payment_amount"])

    # Calculate each client's total monthly recoveries.
    payment_totals = {client_id: sum(amounts, Decimal("0.00"))for client_id, amounts in payments_by_client.items()}
    # Get outstanding costs and group them by client.
    costs_by_client = {}

    cost_rows = Cost.objects.filter(
        billed=False,
        # Include older outstanding costs, but never future costs.
        due_date__lt=period_end
    ).values(
        "account__client_id",
        "cost_id",
        "cost_date",
        "cost_amount",
        "billed",
    )

    for row in cost_rows:
        client_id = row["account__client_id"]

        costs_by_client.setdefault(client_id, []).append({
            "CostID": row["cost_id"],
            "CostDate": row["cost_date"],
            "CostAmount": row["cost_amount"],
            "Billed": row["billed"],
        })

    #Identify clients with an existing report for this month

    
    # Load saved financial snapshots for this reporting month.
    saved_reports = {
        report.client_id: report
        for report in Remittance.objects.filter(
            report_period=period_start
        )
    }

    existing_report_ids = set(saved_reports)

    clients = []

    for client in Client.objects.order_by("client_name"):

        recoveries = payment_totals.get(
            client.client_id, Decimal("0.00")
        )

        costs = costs_by_client.get(client.client_id, [])

        pending_costs = sum(
            (cost["CostAmount"] for cost in costs),
            Decimal("0.00")
        )

        # Apply Michael's existing 20% cap calculation.
        ceiling = calculate_cost_ceiling(recoveries)

        proposal = calculate_billable_costs(
            costs,
            ceiling
        )

        applied_costs = proposal["total_billed"]
        deferred_costs = pending_costs - applied_costs

        # Commission and net remittance require a rate.
        commission = None
        net_remittance = None

        if client.commission_rate is not None:

            totals = calculate_monthly_remittance(
                gross_recoveries=recoveries,
                applied_costs=applied_costs,
                commission_rate=client.commission_rate,
                payment_amounts=payments_by_client.get(
                    client.client_id, []
                ),
            )

            commission = totals["commission"]
            net_remittance = totals["net_remittance"]

        # Existing reports must display their saved financial totals,
        # not recalculate from costs that are now marked billed.
        saved_report = saved_reports.get(client.client_id)

        if saved_report is not None:
            recoveries = saved_report.gross_recoveries
            applied_costs = saved_report.total_cost
            commission = saved_report.total_commission
            net_remittance = saved_report.net_remittance

            # Deferred costs were not stored in the report snapshot.
            deferred_costs = None

        clients.append({
            "id": client.client_id,
            "name": client.client_name,
            "rate": (
                str(client.commission_rate)
                if client.commission_rate is not None
                else None
            ),
            "report_exists": client.client_id in existing_report_ids,
            "recoveries": str(recoveries),
            "pending_costs": str(pending_costs),
            "cost_ceiling": str(ceiling),
            "applied_costs": str(applied_costs),
            "deferred_costs": (
                str(deferred_costs)
                if deferred_costs is not None else None
            ),
            "commission": (
                str(commission)
                if commission is not None else None
            ),
            "net_remittance": (
                str(net_remittance)
                if net_remittance is not None else None
            )
        })

    return JsonResponse({
        "year": year,
        "month": month,
        "preview": True,
        "clients": clients
    })

