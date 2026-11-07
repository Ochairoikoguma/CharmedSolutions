from datetime import date
from decimal import Decimal

from django.db import transaction

from accounting.models import Client, Payment, Cost, Remittance
from accounting.services.calculations import calculate_monthly_remittance
from accounting.services.reports import generate_remittance_pdf


#Read clients monthly records and calculate report totals
def prepare_remittance_data(client_id, year, month):
    #Date boundairies are first day of this month and first day of next month
    period_start = date(year, month, 1)

    if month == 12:
        period_end = date(year + 1, 1, 1)
    else:
        period_end = date(year, month + 1, 1)

    #Using db ID find client
    client = Client.objects.get(pk=client_id)

    if client.commission_rate is None:
        raise ValueError("Enter a commission rate for this client first.")

    payments = list(Payment.objects.select_related("account")
        .filter(account__client=client, payment_date__gte=period_start,payment_date__lt=period_end,).order_by("payment_date", "payment_id"))

    costs = list(Cost.objects.select_related("account")
        .filter(account__client=client,billed=False,due_date__gte=period_start,due_date__lt=period_end,).order_by("cost_date", "cost_id"))

    gross_recoveries = sum((payment.payment_amount for payment in payments),Decimal("0.00"),)
    applied_costs = sum((cost.cost_amount for cost in costs),Decimal("0.00"),)

    totals = calculate_monthly_remittance(gross_recoveries=gross_recoveries,applied_costs=applied_costs,commission_rate=client.commission_rate,)

    return {"client": client,"report_period": period_start,"payments": payments,"costs": costs,"totals": totals,}

def build_remittance_pdf(data):
    #Build a PDF from the client's records and calculated totals

    client = data["client"]
    totals = data["totals"]

    #convert payment records into the dictionaries used by reportspy
    payment_rows = []

    for payment in data["payments"]:
        
        #costs appear separately in the report, so use zero costs here.
        payment_totals = calculate_monthly_remittance(gross_recoveries=payment.payment_amount,applied_costs=Decimal("0.00"),commission_rate=client.commission_rate,)

        payment_rows.append(
            {
                "debtor": payment.account.debtor_name,
                "claim_number": payment.account.account_number,
                "date": payment.payment_date,
                "description": "Payment",
                "amount": payment.payment_amount,
                "attorney_share": payment_totals["commission"],
                "client_share": payment_totals["net_remittance"],
            }
        )

    # convert cost records into the dictionaries used by reportspy
    cost_rows = []

    for cost in data["costs"]:
        cost_rows.append(
            {
                "debtor": cost.account.debtor_name,
                "claim_number": cost.account.account_number,
                "date": cost.cost_date,
                "description": cost.cost_description or "",
                "amount": cost.cost_amount,
            }
        )

    #payment table shows the clients share before deducting costs
    payment_client_total = (totals["gross_recoveries"] - totals["commission"])



    #db stores 25% as 25.00.
    # pdfs percentage formatting expects 0.25
    pdf_commission_rate = client.commission_rate / Decimal("100")

    # Pass db info and calculated totals to pdf service
    return generate_remittance_pdf(
        client_name=client.client_name,
        reporting_month=data["report_period"].strftime("%B %Y"),
        gross_recoveries=totals["gross_recoveries"],
        commission=totals["commission"],
        applied_costs=totals["applied_costs"],
        net_remittance=totals["net_remittance"],
        net_recoveries=totals["net_recoveries"],
        commission_rate=pdf_commission_rate,
        report_date=date.today(),
        payments=payment_rows,
        costs=cost_rows,
        payment_client_total=payment_client_total,
    )

@transaction.atomic
def save_remittance_report(client_id, year, month):
    #Save a monthly pdf and totals, then mark its included costs as billed
    report_period = date(year, month, 1)

    #lock this client while saving so two calls to this function
    # cannot generate the same clients report at the same time
    client = Client.objects.select_for_update().get(pk=client_id)


    # Preserve the existing report if this month was already generated
    if Remittance.objects.filter(client=client,report_period=report_period,).exists():
        raise ValueError("A report already exists for this client and reporting month.")


    # read the monthly records and ask the calculation service for totals
    data = prepare_remittance_data(client.pk, year, month)

    #Build the pdf before saving the report or marking costs as billed
    pdf_data = build_remittance_pdf(data)
    totals = data["totals"]



    #store the pdf and a snapshot of the totals used in this report.
    report = Remittance.objects.create(
        client=client,
        report_period=report_period,
        gross_recoveries=totals["gross_recoveries"],
        total_cost=totals["applied_costs"],
        commission_rate=client.commission_rate,
        total_commission=totals["commission"],
        net_remittance=totals["net_remittance"],
        pdf_file=pdf_data,
    )



    # Mark only the costs included in this report as billed
    included_cost_ids = [cost.pk for cost in data["costs"]]

    Cost.objects.filter(pk__in=included_cost_ids).update(billed=True)
    #If an exception occurs, neither change is committed
    return report