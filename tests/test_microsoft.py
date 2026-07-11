import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from daily_brief.microsoft import TIMEZONE, fetch_microsoft_agenda


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class MicrosoftTests(unittest.TestCase):
    def test_fetches_todays_calendar_in_amsterdam_time(self) -> None:
        payload = {
            "value": [
                {
                    "id": "one",
                    "subject": "Overleg",
                    "start": {"dateTime": "2026-07-02T09:30:00"},
                    "end": {"dateTime": "2026-07-02T10:00:00"},
                    "isAllDay": False,
                    "location": {"displayName": "Teams"},
                }
            ]
        }

        def opener(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "Bearer token")
            self.assertIn("calendarView", request.full_url)
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_microsoft_agenda(
                opener,
                Path(directory),
                datetime(2026, 7, 2, 8, tzinfo=TIMEZONE),
                "token",
            )

        self.assertEqual(result.agenda[0].time, "09:30")
        self.assertEqual(result.agenda[0].location, "Teams")
