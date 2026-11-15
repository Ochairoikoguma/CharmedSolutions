from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

def calculate_cost_ceiling(total_recoveries, max_percentage=20):
    """Calculate the maximum costs allowed for the month."""

    recoveries = Decimal(str(total_recoveries))
    percentage = Decimal(str(max_percentage))

    if recoveries < 0:
        raise ValueError("Total recoveries cannot be negative.")

    if not 0 <= percentage <= 20:
        raise ValueError("Cost percentage must be between 0 and 20.")

    # Round the cost ceiling down to whole cents
    return (
        recoveries * percentage / Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_DOWN)


def calculate_billable_costs(costs, ceiling):
    """Select whole costs oldest first, continuing past costs that do not fit."""

    # Process unbilled costs by date, then numeric cost ID.
    costs = sorted(
        [cost for cost in costs if not cost["Billed"]],
        key=lambda cost: (cost["CostDate"], int(cost["CostID"]))
    )

    billed_costs = []
    rollover_costs = []
    total_billed = Decimal("0.00")
    ceiling = Decimal(str(ceiling))

    for cost in costs:
        amount = Decimal(str(cost["CostAmount"]))

        if amount < 0:
            raise ValueError("Cost amounts cannot be negative.")

        # Include the entire cost only when it fits.
        if total_billed + amount <= ceiling:
            billed_costs.append(cost)
            total_billed += amount
        else:
            # Defer this cost, but keep checking later costs.
            rollover_costs.append(cost)

    return {
        "ceiling": ceiling,
        "total_billed": total_billed,
        "billed_costs": billed_costs,
        "rollover_costs": rollover_costs,
    }

    
def calculate_monthly_remittance(
    gross_recoveries,
    applied_costs,
    commission_rate,
    payment_amounts=None,
):
    """Calculate remittance using commissions rounded per payment."""

    gross = Decimal(str(gross_recoveries))
    costs = Decimal(str(applied_costs))
    rate = Decimal(str(commission_rate))

    if not gross.is_finite() or gross < 0:
        raise ValueError("Gross recoveries must be a nonnegative amount.")

    if not costs.is_finite() or costs < 0:
        raise ValueError("Applied costs must be a nonnegative amount.")

    if not rate.is_finite() or not 0 <= rate <= 100:
        raise ValueError("Commission rate must be 0 to 100.")

    # A single-payment calculation can use gross directly.
    # Monthly callers must supply the individual payment amounts.
    amounts = (
        [gross]
        if payment_amounts is None
        else [Decimal(str(amount)) for amount in payment_amounts]
    )

    if any(not amount.is_finite() or amount < 0 for amount in amounts):
        raise ValueError("Payment amounts must be nonnegative.")

    if sum(amounts, Decimal("0.00")) != gross:
        raise ValueError("Payment amounts do not match gross recoveries.")

    # Proposed rounding rule: round each payment's commission,
    # then sum those rounded amounts for the monthly total.
    commission = sum(
        (
            (amount * rate / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            for amount in amounts
        ),
        Decimal("0.00"),
    )

    net_recoveries = gross - costs
    net_remittance = net_recoveries - commission

    return {
        "gross_recoveries": gross,
        "applied_costs": costs,
        "net_recoveries": net_recoveries,
        "commission": commission,
        "net_remittance": net_remittance,
    }
