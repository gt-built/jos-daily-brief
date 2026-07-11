import unittest
from datetime import date

from daily_brief.google_contacts import _birthdays_for_day


class GoogleContactsTests(unittest.TestCase):
    def test_selects_and_sorts_birthdays_for_today(self) -> None:
        people = [
            {
                "names": [{"displayName": "Zoë"}],
                "birthdays": [{"date": {"month": 7, "day": 6}}],
            },
            {
                "names": [{"displayName": "Anna"}],
                "birthdays": [{"date": {"year": 1980, "month": 7, "day": 6}}],
            },
            {
                "names": [{"displayName": "Morgen"}],
                "birthdays": [{"date": {"month": 7, "day": 7}}],
            },
        ]

        result = _birthdays_for_day(people, date(2026, 7, 6))

        self.assertEqual(result, ["Anna", "Zoë"])
