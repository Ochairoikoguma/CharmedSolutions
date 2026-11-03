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


def prepare_rollover(proposal):
    """Prepare billing and due-date updates without saving."""

    updates = []

    for cost in proposal["billed_costs"]:
        updates.append({
            "CostID": cost["CostID"],
            "Billed": True,
            "DueDate": cost["DueDate"]
        })

    for cost in proposal["rollover_costs"]:
        updates.append({
            "CostID": cost["CostID"],
            "Billed": False,
            "DueDate": next_month(cost["DueDate"])
        })

    return updates