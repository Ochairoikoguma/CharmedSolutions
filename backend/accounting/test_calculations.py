from datetime import date
from decimal import Decimal
from accounting.services.calculations import (
    calculate_cost_ceiling,
    calculate_billable_costs
)
from accounting.services.rollovers import prepare_rollover
from accounting.services.calculations import calculate_monthly_remittance
costs = [
    {
        "CostID": 1,
        "CostDate": date(2026, 10, 1),
        "CostAmount": Decimal("800.00"),
        "Billed": False,
        "DueDate": date(2026, 10, 1)
    },
    {
        "CostID": 2,
        "CostDate": date(2026, 10, 5),
        "CostAmount": Decimal("700.00"),
        "Billed": False,
        "DueDate": date(2026, 10, 5)
    },
    {
        "CostID": 3,
        "CostDate": date(2026, 10, 10),
        "CostAmount": Decimal("600.00"),
        "Billed": False,
        "DueDate": date(2026, 10, 10)
    }
]

ceiling = calculate_cost_ceiling(10000)
proposal = calculate_billable_costs(costs, ceiling)
updates = prepare_rollover(proposal)

assert ceiling == Decimal("2000.00")
assert proposal["total_billed"] == Decimal("1500.00")
assert [c["CostID"] for c in proposal["rollover_costs"]] == [3]
assert updates[-1]["DueDate"] == date(2026, 11, 10)

print("Cost ceiling:", ceiling)
print("Total billed:", proposal["total_billed"])
print("Rollover updates:", updates)
print("All tests passed!")



def test_monthly_remittance():
    result = calculate_monthly_remittance(
        gross_recoveries=10000,
        applied_costs=1500,
        commission_rate=20
    )

    assert result["gross_recoveries"] == Decimal("10000")
    assert result["applied_costs"] == Decimal("1500")
    assert result["net_recoveries"] == Decimal("8500")
    assert result["commission"] == Decimal("2000")
    assert result["net_remittance"] == Decimal("6500")

    print("Monthly remittance test passed!")


test_monthly_remittance()
