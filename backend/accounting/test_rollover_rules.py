
import unittest
from datetime import date

from accounting.services.rollovers import prepare_rollover


class RolloverRuleTests(unittest.TestCase):

    def setUp(self):
        self.proposal = {
            "billed_costs": [],
            "rollover_costs": [
                {
                    "CostID": 100,
                    "Billed": False,
                    "DueDate": date(2026, 9, 1),
                }
            ],
        }

    # T38: Older deferred costs move after reporting month
    def test_multiple_month_rollover(self):
        result = prepare_rollover(
            self.proposal,
            report_period=date(2026, 11, 1),
        )
        self.assertEqual(
            result[0]["DueDate"], date(2026, 12, 1)
        )

    # T39: December rollover moves to January next year
    def test_year_end_rollover(self):
        result = prepare_rollover(
            self.proposal,
            report_period=date(2026, 12, 1),
        )
        self.assertEqual(
            result[0]["DueDate"], date(2027, 1, 1)
        )

    # T40: Reject duplicate transaction IDs
    def test_duplicate_cost_ids(self):
        self.proposal["billed_costs"] = [
            {
                "CostID": 100,
                "Billed": False,
                "DueDate": date(2026, 11, 1),
            }
        ]

        with self.assertRaises(ValueError):
            prepare_rollover(
                self.proposal,
                report_period=date(2026, 11, 1),
            )

    # T41: Preparing updates does not modify originals
    def test_original_due_date_preserved(self):
        original_date = self.proposal["rollover_costs"][0]["DueDate"]

        prepare_rollover(
            self.proposal,
            report_period=date(2026, 11, 1),
        )

        self.assertEqual(
            self.proposal["rollover_costs"][0]["DueDate"],
            original_date,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
