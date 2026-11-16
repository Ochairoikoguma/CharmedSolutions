
import unittest
from datetime import date
from decimal import Decimal

from accounting.services.calculations import (
    calculate_cost_ceiling,
    calculate_billable_costs,
)
from accounting.services.rollovers import prepare_rollover, next_month


def make_cost(cost_id, amount, cost_date, due_date=None):
    return {
        "CostID": cost_id,
        "CostAmount": Decimal(str(amount)),
        "CostDate": cost_date,
        "DueDate": due_date or cost_date,
        "Billed": False,
    }


class RolloverSafetyTests(unittest.TestCase):

    # T32: Preparing a proposal does not change source records
    def test_preview_does_not_modify_costs(self):
        costs = [make_cost(10, 2500, date(2026, 10, 5))]
        original = costs[0].copy()

        proposal = calculate_billable_costs(costs, Decimal("2000"))
        prepare_rollover(proposal)

        self.assertEqual(costs[0], original)

    # T33: Preserve original cost ID
    def test_preserve_cost_id(self):
        costs = [make_cost(123, 2500, date(2026, 10, 5))]
        proposal = calculate_billable_costs(costs, Decimal("2000"))
        updates = prepare_rollover(proposal)

        self.assertEqual(updates[0]["CostID"], 123)

    # T34: Preserve original transaction date in source
    def test_preserve_cost_date(self):
        costs = [make_cost(12, 2500, date(2026, 9, 15))]
        proposal = calculate_billable_costs(costs, Decimal("2000"))
        prepare_rollover(proposal)

        self.assertEqual(costs[0]["CostDate"], date(2026, 9, 15))

    # T35: Zero ceiling defers positive costs
    def test_zero_ceiling(self):
        costs = [
            make_cost(1, 200, date(2026, 10, 1)),
            make_cost(2, 300, date(2026, 10, 2)),
        ]

        ceiling = calculate_cost_ceiling(0)
        proposal = calculate_billable_costs(costs, ceiling)

        self.assertEqual(len(proposal["billed_costs"]), 0)
        self.assertEqual(len(proposal["rollover_costs"]), 2)

    # T36: Consecutive rollover date transitions
    def test_consecutive_months(self):
        first = next_month(date(2026, 10, 1))
        second = next_month(first)

        self.assertEqual(first, date(2026, 11, 1))
        self.assertEqual(second, date(2026, 12, 1))

    # T37: Reject percentages above 20%
    def test_reject_invalid_ceiling(self):
        with self.assertRaises(ValueError):
            calculate_cost_ceiling(10000, 21)


if __name__ == "__main__":
    unittest.main(verbosity=2)
