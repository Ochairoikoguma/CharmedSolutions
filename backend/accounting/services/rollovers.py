
from datetime import date
from calendar import monthrange


def next_month(current_date):
    """Move a date into the following month."""

    if current_date.month == 12:
        year = current_date.year + 1
        month = 1
    else:
        year = current_date.year
        month = current_date.month + 1

    day = min(
        current_date.day,
        monthrange(year, month)[1]
    )

    return date(year, month, day)


def prepare_rollover(proposal, report_period=None):
    """
    Prepare billing and rollover updates without saving.

    When report_period is provided, deferred costs move
    to the month after the reporting period.
    """

    updates = []
    processed_ids = set()

    if report_period is not None:
        if not isinstance(report_period, date):
            raise ValueError("Invalid reporting period.")

        next_due_date = next_month(
            date(report_period.year, report_period.month, 1)
        )

    for cost in proposal["billed_costs"]:
        cost_id = cost["CostID"]

        if cost_id in processed_ids:
            raise ValueError("Duplicate CostID in proposal.")

        processed_ids.add(cost_id)

        updates.append({
            "CostID": cost_id,
            "Billed": True,
            "DueDate": cost["DueDate"]
        })

    for cost in proposal["rollover_costs"]:
        cost_id = cost["CostID"]

        if cost_id in processed_ids:
            raise ValueError("Duplicate CostID in proposal.")

        processed_ids.add(cost_id)

        due_date = (
            next_due_date
            if report_period is not None
            else next_month(cost["DueDate"])
        )

        updates.append({
            "CostID": cost_id,
            "Billed": False,
            "DueDate": due_date
        })

    return updates
