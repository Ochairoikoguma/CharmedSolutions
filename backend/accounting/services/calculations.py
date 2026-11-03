from decimal import Decimal


def calculate_cost_ceiling(total_recoveries, max_percentage=20):
    """Calculate the maximum costs allowed for the month."""

    recoveries = Decimal(str(total_recoveries))
    percentage = Decimal(str(max_percentage))

    if recoveries < 0:
        raise ValueError("Total recoveries cannot be negative.")

    if not 0 <= percentage <= 20:
        raise ValueError("Cost percentage must be between 0 and 20.")

    return recoveries * percentage / Decimal("100")


def calculate_billable_costs(costs, ceiling):
    """Select whole costs oldest first without exceeding the ceiling."""

    costs = sorted(
        [cost for cost in costs if not cost["Billed"]],
        key=lambda cost: (cost["CostDate"], str(cost["CostID"]))
    )

    billed_costs = []
    rollover_costs = []
    total_billed = Decimal("0.00")
    ceiling = Decimal(str(ceiling))
    limit_reached = False

    for cost in costs:
        amount = Decimal(str(cost["CostAmount"]))

        if amount < 0:
            raise ValueError("Cost amounts cannot be negative.")

        if not limit_reached and total_billed + amount <= ceiling:
            billed_costs.append(cost)
            total_billed += amount
        else:
            limit_reached = True
            rollover_costs.append(cost)

    return {
        "ceiling": ceiling,
        "total_billed": total_billed,
        "billed_costs": billed_costs,
        "rollover_costs": rollover_costs
    }