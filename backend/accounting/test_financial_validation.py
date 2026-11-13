
import unittest
from datetime import date
from decimal import Decimal

from accounting.services.calculations import (
    calculate_cost_ceiling,
    calculate_billable_costs,
    calculate_monthly_remittance,
)
from accounting.services.rollovers import next_month


def make_cost(cost_id, amount, cost_date, billed=False,
              account_id=1):
    return {
        "CostID": cost_id,
        "CostAmount": Decimal(str(amount)),
        "CostDate": cost_date,
        "DueDate": cost_date,
        "Billed": billed,
        "AccountID": account_id,
    }


class FinancialValidationTests(unittest.TestCase):

    # T17: Negative collections should be rejected
    def test_negative_recoveries(self):
        with self.assertRaises(ValueError):
            calculate_cost_ceiling(-1000)

    # T18: Attorney cannot exceed the 20% maximum
    def test_attorney_above_twenty_percent(self):
        with self.assertRaises(ValueError):
            calculate_cost_ceiling(10000, 25)

    # T19: Invalid commission rates
    def test_commission_above_100(self):
        with self.assertRaises(ValueError):
            calculate_monthly_remittance(10000, 500, 110)

    # T20: Negative remittance calculation
    def test_negative_net_remittance(self):
        result = calculate_monthly_remittance(
            gross_recoveries=1000,
            applied_costs=1200,
            commission_rate=20,
        )

        self.assertEqual(
            result["net_recoveries"],
            Decimal("-200")
        )
        self.assertEqual(
            result["net_remittance"],
            Decimal("-400")
        )

    # T21: Preserve decimal calculation precision
    def test_fractional_cent_commission(self):
        result = calculate_monthly_remittance(
            gross_recoveries="100.01",
            applied_costs="0.00",
            commission_rate="15",
        )

        self.assertEqual(
            result["commission"],
            Decimal("15.0015")
        )

    # T22: Previously billed costs are excluded
    def test_exclude_billed_costs(self):
        costs = [
            make_cost(1, 500, date(2026, 10, 1), True),
            make_cost(2, 700, date(2026, 10, 2)),
        ]

        result = calculate_billable_costs(
            costs, Decimal("2000")
        )

        self.assertEqual(
            [c["CostID"] for c in result["billed_costs"]],
            [2]
        )
        self.assertEqual(result["total_billed"], 700)

    # T23: A transaction can fill the ceiling exactly
    def test_exact_remaining_capacity(self):
        costs = [
            make_cost(1, 1200, date(2026, 10, 1)),
            make_cost(2, 800, date(2026, 10, 2)),
        ]

        result = calculate_billable_costs(
            costs, Decimal("2000")
        )

        self.assertEqual(result["total_billed"], 2000)
        self.assertEqual(len(result["rollover_costs"]), 0)

    # T24: Leap-year date calculation
    def test_leap_year_rollover(self):
        result = next_month(date(2028, 2, 29))
        self.assertEqual(result, date(2028, 3, 29))

    # T25: Costs across accounts are processed together
    def test_multiple_collection_accounts(self):
        costs = [
            make_cost(3, 600, date(2026, 10, 3),
                      account_id=20),
            make_cost(1, 800, date(2026, 10, 1),
                      account_id=10),
            make_cost(2, 700, date(2026, 10, 2),
                      account_id=20),
        ]

        result = calculate_billable_costs(
            costs, Decimal("2000")
        )

        self.assertEqual(
            [c["CostID"] for c in result["billed_costs"]],
            [1, 2]
        )
        self.assertEqual(
            [c["CostID"] for c in result["rollover_costs"]],
            [3]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
