"""Read Simplicity exports and save each import as one transaction."""
import csv
import io
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.db import connection, transaction
from django.db.models import Max

from accounting.models import Client, CollectionAccount, Payment, Cost, Remittance
from accounting.import_models import ImportBatch, ImportRow


COLUMNS = (
    "Client Full Name", "Account Number", "Debtor First/Company Name",
    "Trans. Is Payment", "Trans. Date", "Trans. Amount",
    "Trans. Description Name",
)
MAX_UPLOAD = 5 * 1024 * 1024


def parse_simplicity_export(file_bytes):
    if len(file_bytes) > MAX_UPLOAD:
        raise ValueError("CSV must be 5 MB or smaller.")
    try:
        stream = io.StringIO(file_bytes.decode("utf-8-sig"), newline="")
    except UnicodeDecodeError as error:
        raise ValueError("Save the CSV using UTF-8 encoding.") from error
    if stream.readline().strip() != "simplicity_export":
        stream.seek(0)
    rows, periods, identities = [], set(), {}
    try:
        reader = csv.DictReader(stream, strict=True)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("CSV contains repeated column headers.")
        missing = [name for name in COLUMNS if name not in headers]
        if missing:
            raise ValueError("Missing CSV columns: " + ", ".join(missing))
        for position, raw in enumerate(reader, 1):
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"Wrong number of fields in transaction {position}.")
            source = {name: raw[name].strip() for name in COLUMNS}
            client, account, debtor, flag, day, amount_text, description = (
                source[name] for name in COLUMNS
            )
            if not client or not account or not debtor:
                raise ValueError(f"Missing client, account, or debtor in transaction {position}.")
            if any(len(value) > limit for value, limit in (
                (client, 150), (account, 20), (debtor, 255), (description, 255)
            )):
                raise ValueError(f"Field too long in transaction {position}.")
            if flag.upper() not in {"TRUE", "FALSE"}:
                raise ValueError(f"Invalid payment flag in transaction {position}.")
            try:
                day = datetime.strptime(day, "%m/%d/%Y").date()
            except ValueError as error:
                raise ValueError(f"Invalid date in transaction {position}.") from error
            if not 1 <= day.year <= 9998:
                raise ValueError("Reporting year must be between 1 and 9998.")
            try:
                amount = Decimal(amount_text)
                if not amount.is_finite() or not 0 <= amount <= Decimal("9999999999.99"):
                    raise ValueError()
                if amount != amount.quantize(Decimal("0.01")):
                    raise ValueError()
            except (InvalidOperation, ValueError) as error:
                raise ValueError(f"Invalid amount in transaction {position}.") from error
            key = account.casefold()
            identity = (client.casefold(), debtor.casefold())
            if key in identities and identities[key] != identity:
                raise ValueError(f"Conflicting client or debtor for account {account}.")
            identities[key] = identity
            periods.add(date(day.year, day.month, 1))
            rows.append({
                "client": client, "account": account, "debtor": debtor,
                "is_payment": flag.upper() == "TRUE", "date": day,
                "amount": amount, "description": description,
                "source": source, "source_row": position,
            })
    except csv.Error as error:
        raise ValueError(f"Invalid CSV formatting: {error}") from error
    if not rows:
        raise ValueError("CSV contains no transactions.")
    if len(periods) != 1:
        raise ValueError("CSV must contain one reporting month.")
    return {"rows": rows, "period": periods.pop()}


def active_reporting_period():
    # The latest successful upload controls the period, including after restart.
    latest = ImportBatch.objects.order_by("-batch_id").values_list("reporting_month", flat=True).first()
    if latest:
        return latest
    # Support the data already imported manually before batch tracking existed.
    dates = [
        Payment.objects.aggregate(value=Max("payment_date"))["value"],
        Cost.objects.aggregate(value=Max("cost_date"))["value"],
    ]
    dates = [value for value in dates if value]
    if not dates:
        return None
    latest = max(dates)
    return date(latest.year, latest.month, 1)


@contextmanager
def import_lock():
    # Serialize imports on MySQL; report creation also locks each affected client.
    acquired = False
    if connection.vendor == "mysql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT GET_LOCK(%s, 10)", ["charmed_csv_import"])
            acquired = cursor.fetchone()[0] == 1
        if not acquired:
            raise ValueError("Another import is running. Try again shortly.")
    try:
        yield
    finally:
        if acquired:
            with connection.cursor() as cursor:
                cursor.execute("SELECT RELEASE_LOCK(%s)", ["charmed_csv_import"])


def persist_simplicity_export(parsed, filename):
    with import_lock(), transaction.atomic():
        rows, period = parsed["rows"], parsed["period"]
        batch = ImportBatch.objects.create(
            filename=filename[:255], reporting_month=period, row_count=len(rows)
        )
        clients, accounts = {}, {}
        # Resolve names case-insensitively and lock clients before any transactions.
        for name in sorted({row["client"] for row in rows}, key=str.casefold):
            key = name.casefold()
            if key in clients:
                continue
            client = Client.objects.filter(client_name__iexact=name).first()
            if client is None:
                client = Client.objects.create(client_name=name, commission_rate=None)
            clients[key] = client
        client_ids = sorted({client.pk for client in clients.values()})
        list(Client.objects.select_for_update().filter(pk__in=client_ids).order_by("pk"))
        if Remittance.objects.filter(client_id__in=client_ids, report_period=period).exists():
            raise ValueError("A report already exists for an affected client in this month. Import cannot change that report's source data.")
        for row in rows:
            key = row["account"].casefold()
            if key in accounts:
                continue
            client = clients[row["client"].casefold()]
            account = CollectionAccount.objects.filter(account_number__iexact=row["account"]).first()
            if account is None:
                account = CollectionAccount.objects.create(
                    account_number=row["account"], client=client, debtor_name=row["debtor"]
                )
            elif account.client_id != client.pk or account.debtor_name.casefold() != row["debtor"].casefold():
                raise ValueError(f"Account {row['account']} has a different client or debtor in the database.")
            accounts[key] = account

        payments = costs = 0
        audit = []
        # Individual creates return stable MySQL IDs for each source row's audit link.
        # Matching rows within a file remain distinct transactions.
        for row in rows:
            account = accounts[row["account"].casefold()]
            payment_id = cost_id = None
            if row["is_payment"]:
                record = Payment.objects.create(account=account, payment_date=row["date"], payment_amount=row["amount"])
                payment_id = record.pk
                payments += 1
            else:
                record = Cost.objects.create(
                    account=account, cost_date=row["date"], cost_amount=row["amount"],
                    cost_description=row["description"], billed=False, due_date=period
                )
                cost_id = record.pk
                costs += 1
            audit.append(ImportRow(
                batch=batch, source_row=row["source_row"], source=row["source"],
                payment_id=payment_id, cost_id=cost_id
            ))
        ImportRow.objects.bulk_create(audit)
        return {
            "batch_id": batch.pk, "year": period.year, "month": period.month,
            "clients": len(set(client_ids)), "accounts": len(accounts),
            "payments": payments, "costs": costs, "transactions": len(rows),
        }
