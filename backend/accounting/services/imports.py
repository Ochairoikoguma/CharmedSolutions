
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation


def read_transactions(csv_file):
    # Read the CSV file from Simplicity
    reader = csv.DictReader(csv_file)

    # Check that the required columns exist
    required_columns = [
        "Case Number",
        "Transaction Description",
        "Transaction Amount",
        "Transaction Date",
        "Transaction Type",
    ]

    if reader.fieldnames is None:
        raise ValueError("CSV file is empty or missing headers")

    missing_columns = [
        column for column in required_columns
        if column not in reader.fieldnames
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: " + ", ".join(missing_columns)
        )

    transactions = []
    seen_transactions = set()

    # Go through each transaction in the CSV
    for row_number, row in enumerate(reader, start=2):

        # Check that the row has the correct number of columns
        if None in row or any(value is None for value in row.values()):
            raise ValueError(
                f"Incorrect number of columns on row {row_number}"
            )

        # Check the case number and description
        case_number = (row["Case Number"] or "").strip()
        description = (row["Transaction Description"] or "").strip()

        if not case_number or not description:
            raise ValueError(
                f"Missing case number or description on row {row_number}"
            )

        # Validate the transaction amount
        try:
            amount = Decimal(row["Transaction Amount"].strip())

            if not amount.is_finite() or amount < 0:
                raise ValueError("Invalid transaction amount")

        except (InvalidOperation, ValueError, AttributeError):
            raise ValueError(
                f"Invalid transaction amount on row {row_number}"
            )

        # Validate the transaction date
        try:
            transaction_date = datetime.strptime(
                row["Transaction Date"].strip(), "%m/%d/%Y"
            ).date()

        except (ValueError, AttributeError):
            raise ValueError(
                f"Invalid transaction date on row {row_number}"
            )

        # Identify payments and costs
        transaction_type = (row["Transaction Type"] or "").strip().lower()

        if transaction_type not in ["payment", "cost"]:
            raise ValueError(
                f"Invalid transaction type on row {row_number}"
            )

        # Check for possible duplicates in this CSV
        transaction_key = (
            case_number,
            description,
            amount,
            transaction_date,
            transaction_type,
        )

        if transaction_key in seen_transactions:
            raise ValueError(
                f"Possible duplicate transaction on row {row_number}"
            )

        seen_transactions.add(transaction_key)

        # Store the validated information
        row["Case Number"] = case_number
        row["Transaction Description"] = description
        row["Transaction Amount"] = amount
        row["Transaction Date"] = transaction_date
        row["Transaction Type"] = transaction_type

        transactions.append(row)

    # Return the validated transactions
    return transactions


def generate_import_preview(transactions):
    # Prepare the import summary
    preview = {
        "total_transactions": len(transactions),
        "payment_count": 0,
        "cost_count": 0,
        "total_payments": Decimal("0.00"),
        "total_costs": Decimal("0.00"),
    }

    # Calculate payment and cost totals
    for transaction in transactions:
        transaction_type = transaction["Transaction Type"]
        amount = transaction["Transaction Amount"]

        if transaction_type == "payment":
            preview["payment_count"] += 1
            preview["total_payments"] += amount

        elif transaction_type == "cost":
            preview["cost_count"] += 1
            preview["total_costs"] += amount

    # Return the summary before database import
    return preview


def generate_import_report(csv_file):
    # Prepare the import report
    report = {
        "status": "success",
        "transactions": [],
        "preview": None,
        "errors": [],
    }

    # Read and validate the CSV file
    try:
        transactions = read_transactions(csv_file)

        # Generate the preview
        preview = generate_import_preview(transactions)

        report["transactions"] = transactions
        report["preview"] = preview

    except (ValueError, csv.Error) as error:
        # Record validation errors
        report["status"] = "failed"
        report["errors"].append(str(error))

    # Return the results without saving to the database
    return report
