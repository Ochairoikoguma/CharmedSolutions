from django.shortcuts import render
from datetime import date
from decimal import Decimal
from django.http import HttpResponse
from .services.reports import generate_remittance_pdf


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
