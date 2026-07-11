import io
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from daily_brief.formula_one import fetch_formula_one_result


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FormulaOneTests(unittest.TestCase):
    def test_shows_recent_top_three_and_max(self) -> None:
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "raceName": "Dutch Grand Prix",
                            "date": "2026-07-05",
                            "Results": [
                                {
                                    "position": "1",
                                    "positionText": "1",
                                    "Driver": {
                                        "driverId": "norris",
                                        "givenName": "Lando",
                                        "familyName": "Norris",
                                    },
                                },
                                {
                                    "position": "2",
                                    "positionText": "2",
                                    "Driver": {
                                        "driverId": "max_verstappen",
                                        "givenName": "Max",
                                        "familyName": "Verstappen",
                                    },
                                },
                                {
                                    "position": "3",
                                    "positionText": "3",
                                    "Driver": {
                                        "driverId": "piastri",
                                        "givenName": "Oscar",
                                        "familyName": "Piastri",
                                    },
                                },
                            ],
                        }
                    ]
                }
            }
        }

        def opener(request, timeout):
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_formula_one_result(
                opener, Path(directory), date(2026, 7, 6)
            )

        self.assertEqual(result.result.top_three[0], "1. Lando Norris")
        self.assertEqual(result.result.max_result, "Max Verstappen: P2")

    def test_hides_old_race(self) -> None:
        payload = {
            "MRData": {
                "RaceTable": {
                    "Races": [
                        {
                            "raceName": "Old Grand Prix",
                            "date": "2026-06-28",
                            "Results": [],
                        }
                    ]
                }
            }
        }

        def opener(request, timeout):
            return Response(json.dumps(payload).encode())

        with tempfile.TemporaryDirectory() as directory:
            result = fetch_formula_one_result(
                opener, Path(directory), date(2026, 7, 6)
            )

        self.assertIsNone(result.result)
