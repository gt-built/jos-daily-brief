import unittest
from datetime import date
from unittest.mock import patch

from daily_brief.__main__ import _is_paused


class PauseTests(unittest.TestCase):
    def test_no_pause_configured_never_pauses(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(_is_paused(date(2026, 7, 25)))

    @patch.dict(
        "os.environ",
        {"DAILY_BRIEF_PAUSE_FROM": "2026-07-19", "DAILY_BRIEF_PAUSE_UNTIL": "2026-08-08"},
    )
    def test_pauses_within_range_inclusive(self) -> None:
        self.assertTrue(_is_paused(date(2026, 7, 19)))
        self.assertTrue(_is_paused(date(2026, 7, 25)))
        self.assertTrue(_is_paused(date(2026, 8, 8)))

    @patch.dict(
        "os.environ",
        {"DAILY_BRIEF_PAUSE_FROM": "2026-07-19", "DAILY_BRIEF_PAUSE_UNTIL": "2026-08-08"},
    )
    def test_does_not_pause_outside_range(self) -> None:
        self.assertFalse(_is_paused(date(2026, 7, 18)))
        self.assertFalse(_is_paused(date(2026, 8, 9)))
