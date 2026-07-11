import unittest
from datetime import date

from daily_brief.quotes import TAOIST_QUOTES, taoist_quote


class QuoteTests(unittest.TestCase):
    def test_quote_is_stable_for_the_day(self) -> None:
        day = date(2026, 7, 2)
        self.assertEqual(taoist_quote(day), taoist_quote(day))
        self.assertIn(taoist_quote(day), TAOIST_QUOTES)


if __name__ == "__main__":
    unittest.main()
