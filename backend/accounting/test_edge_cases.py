
import unittest
from datetime import date
from decimal import Decimal

from accounting.services.calculations import (
    calculate_cost_ceiling,
    calculate_billable_costs,
)
from accounting.services.rollovers import (
    next_month,
    prepare_rollover,
)


def make_cost(cost_id, amount, cost_date, due_date=None):
    return {
        "CostID": cost_id,
        "CostAmount": Decimal(str(amount)),
        "CostDate": cost_date,
        "DueDate": due_date or cost_date,
        "Billed": False,
    }


class EdgeCaseTests(unittest.TestCase):

    # T05: Attorney sets a lower cost ceiling
    def test_lower_attorney_limit(self):
        ceiling = calculate_cost_ceiling(10000, 15)
        self.assertEqual(ceiling, Decimal("1500"))

    # T06: December rolls over into January
    def test_year_change(self):
        result = next_month(date(2026, 12, 15))
        self.assertEqual(result, date(2027, 1, 15))

    # T07: No collections means no costs billed
    def test_zero_recoveries(self):
        costs = [
            make_cost(1, 500, date(2026, 10, 1))
        ]
        ceiling = calculate_cost_ceiling(0)
        result = calculate_billable_costs(costs, ceiling)

        self.assertEqual(result["total_billed"], 0)
        self.assertEqual(len(result["rollover_costs"]), 1)

    # T08: Cost exceeds ceiling by one cent
    def test_slightly_above_ceiling(self):
        costs = [
            make_cost(1, 1000, date(2026, 10, 1)),
            make_cost(2, 1000.01, date(2026, 10, 2))
        ]

        result = calculate_billable_costs(
            costs, Decimal("2000")
        )

        self.assertEqual(
            result["total_billed"], Decimal("1000")
        )
        self.assertEqual(
            result["rollover_costs"][0]["CostID"], 2
        )

    # T09: Previously deferred cost comes first
    def test_previous_rollover_priority(self):
        costs = [
            make_cost(2, 700, date(2026, 11, 5)),
            make_cost(
                1, 800, date(2026, 10, 5),
                date(2026, 11, 5)
            )
        ]

        result = calculate_billable_costs(
            costs, Decimal("1000")
        )

        self.assertEqual(
            result["billed_costs"][0]["CostID"], 1
        )

    # T10: Preview must not change original data
    def test_preview_no_database_changes(self):
        costs = [
            make_cost(1, 2500, date(2026, 10, 1))
        ]

        proposal = calculate_billable_costs(
            costs, Decimal("2000")
        )
        updates = prepare_rollover(proposal)

        self.assertEqual(
            updates[0]["DueDate"], date(2026, 11, 1)
        )
        self.assertFalse(costs[0]["Billed"])
        self.assertEqual(
            costs[0]["DueDate"], date(2026, 10, 1)
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
