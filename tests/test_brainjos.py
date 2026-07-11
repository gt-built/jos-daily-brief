import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from daily_brief.brainjos import TIMEZONE, fetch_brainjos_with_status


PAYLOAD = {
    "priorities": [
        {"id": "one", "title": "Move Beyond notes van Sander", "coveyQuadrant": "Q1"},
        {"id": "three", "title": "[Braintoss] Doelen stellen plannen", "coveyQuadrant": "Q1"},
        {"id": "two", "title": "Voorbereiden", "coveyQuadrant": "Q2"},
    ],
    "dueTasks": [
        {"id": "one", "title": "Move Beyond notes van Sander", "coveyQuadrant": "Q1"},
    ],
    "calendarEvents": [
        {
            "id": "event",
            "title": "Afspraak",
            "start": "2026-07-02T08:00:00.000Z",
            "end": "2026-07-02T09:00:00.000Z",
            "isAllDay": False,
            "location": "Drunen",
        }
    ],
}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class BrainJosTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "BRAINJOS_API_URL": "https://brainjos.nl/api/daily-brief",
            "BRAINJOS_API_TOKEN": "secret",
        },
    )
    def test_fetches_agenda_and_only_q1_priorities(self) -> None:
        def opener(request, timeout):
            self.assertEqual(request.get_header("Authorization"), "Bearer secret")
            self.assertIn("from=", request.full_url)
            self.assertEqual(timeout, 10)
            return Response(json.dumps(PAYLOAD).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_brainjos_with_status(
                opener,
                Path(directory),
                datetime(2026, 7, 2, 8, tzinfo=TIMEZONE),
            )

        self.assertEqual(result.agenda[0].time, "10:00")
        self.assertEqual(result.agenda[0].location, "Drunen")
        self.assertEqual(
            [task.title for task in result.tasks],
            ["Move Beyond notes van Sander", "[Braintoss] Doelen stellen plannen"],
        )
        self.assertTrue(result.tasks[0].important)

    @patch.dict(
        os.environ,
        {
            "BRAINJOS_API_URL": "https://brainjos.nl/api/daily-brief",
            "BRAINJOS_API_TOKEN": "secret",
        },
    )
    def test_fetches_q1_items_from_covey_shape(self) -> None:
        payload = {
            "covey": {
                "Q1": [
                    {"title": "Move Beyond notes van Sander"},
                    {"title": "[Braintoss] Doelen stellen plannen"},
                ],
                "Q2": [{"title": "Later"}],
            }
        }

        def opener(request, timeout):
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_brainjos_with_status(
                opener,
                Path(directory),
                datetime(2026, 7, 9, 8, tzinfo=TIMEZONE),
            )

        self.assertEqual(
            [task.title for task in result.tasks],
            ["Move Beyond notes van Sander", "[Braintoss] Doelen stellen plannen"],
        )


if __name__ == "__main__":
    unittest.main()
