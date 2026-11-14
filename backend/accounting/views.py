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


    #Temp sample until real data is connected
    payments = [
        {
            "debtor": "Sample Business Alpha",
            "claim_number": "TEST-001",
            "date": date(2026, 10, 5),
            "description": "Payment",
            "amount": Decimal("1500.00"),
            "attorney_share": Decimal("375.00"),
            "client_share": Decimal("1125.00"),
        },
        {
            "debtor": "Sample Business Beta",
            "claim_number": "TEST-002",
            "date": date(2026, 10, 14),
            "description": "Payment",
            "amount": Decimal("2500.00"),
            "attorney_share": Decimal("625.00"),
            "client_share": Decimal("1875.00"),
        },
    ]

    costs = [
        {
            "debtor": "Sample Business Alpha",
            "claim_number": "TEST-001",
            "date": date(2026, 10, 3),
            "description": "Filing fee",
            "amount": Decimal("300.00"),
        },
        {
            "debtor": "Sample Business Beta",
            "claim_number": "TEST-002",
            "date": date(2026, 10, 8),
            "description": "Service of process",
            "amount": Decimal("150.00"),
        },
    ]

    #Ask the report service to build the PDF in memory
    pdf_data = generate_remittance_pdf(
        client_name="John Doe",
        reporting_month="October 2026",
        gross_recoveries=Decimal("4000.00"),
        commission=Decimal("1000.00"),
        applied_costs=Decimal("450.00"),
        net_remittance=Decimal("2550.00"),
        net_recoveries=Decimal("3550.00"),
        commission_rate=Decimal("0.25"),
        report_date=date(2026, 11, 1),
        payments=payments,
        costs=costs,
        payment_client_total=Decimal("3000.00"),
    )

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