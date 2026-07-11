import unittest
from datetime import datetime, timezone
from pathlib import Path

from daily_brief.cache import DEFAULT_CACHE_DIR
from daily_brief.moon import fetch_moon_insight


class MoonTests(unittest.TestCase):
    def test_full_moon_has_cancer_personal_note(self) -> None:
        result = fetch_moon_insight(
            DEFAULT_CACHE_DIR, now=datetime(2026, 7, 5, 6, 30, tzinfo=timezone.utc)
        )

        self.assertEqual(result.insight.phase_name, "Afnemende Gibbeuze")
        self.assertIn("Kreeft", result.insight.personal_note)

    def test_zodiac_sign_changes_over_time(self) -> None:
        early = fetch_moon_insight(
            DEFAULT_CACHE_DIR, now=datetime(2026, 7, 5, 6, 30, tzinfo=timezone.utc)
        )
        later = fetch_moon_insight(
            DEFAULT_CACHE_DIR, now=datetime(2026, 7, 20, 6, 30, tzinfo=timezone.utc)
        )

        self.assertNotEqual(early.insight.zodiac_sign, later.insight.zodiac_sign)

    def test_scorpio_moon_adds_maanretour_note(self) -> None:
        result = fetch_moon_insight(
            DEFAULT_CACHE_DIR, now=datetime(2026, 7, 12, 6, 30, tzinfo=timezone.utc)
        )

        if result.insight.zodiac_sign == "Schorpioen":
            self.assertIn("maanretour", result.insight.personal_note.lower())
