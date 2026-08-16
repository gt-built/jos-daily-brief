import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from daily_brief.models import MoonInsight
from daily_brief.moon_relationship import fetch_moon_relationship_insight

INSIGHT = MoonInsight("Volle Maan", "Kreeft", "Piek van intensiteit.", "Vier het.")
MALOU_CONFIG = {
    "malou": {
        "name": "Malou",
        "sun_sign": "Kreeft",
        "moon_sign": "Tweelingen",
        "birth_phase": "Afnemende Sikkel",
        "mbti": "ISTJ",
    }
}


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def _openai_response(text="Een lopende relatie-analyse van vijf zinnen."):
    payload = {
        "output": [
            {"content": [{"type": "output_text", "text": json.dumps({"analysis": text})}]}
        ]
    }
    return Response(json.dumps(payload).encode())


def _write_config(directory: str) -> Path:
    path = Path(directory) / "moon-relationship.json"
    path.write_text(json.dumps(MALOU_CONFIG), encoding="utf-8")
    return path


class MoonRelationshipTests(unittest.TestCase):
    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_combines_jos_and_malou_into_flowing_text(self) -> None:
        def opener(request, timeout):
            self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
            body = json.loads(request.data)
            sent = json.loads(body["input"])
            self.assertEqual(sent["jos"]["sun_sign"], "Kreeft")
            self.assertEqual(sent["malou"]["moon_sign"], "Tweelingen")
            self.assertEqual(sent["phase_name"], "Volle Maan")
            return _openai_response()

        with tempfile.TemporaryDirectory() as cache_dir, tempfile.TemporaryDirectory() as config_dir:
            config_path = _write_config(config_dir)
            result = fetch_moon_relationship_insight(
                INSIGHT, opener, Path(cache_dir), config_path
            )

        self.assertEqual(result.text, "Een lopende relatie-analyse van vijf zinnen.")
        self.assertNotIn("\n", result.text)
        self.assertFalse(result.stale)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_caches_within_same_local_day(self) -> None:
        calls = {"count": 0}

        def opener(request, timeout):
            calls["count"] += 1
            return _openai_response()

        with tempfile.TemporaryDirectory() as cache_dir, tempfile.TemporaryDirectory() as config_dir:
            config_path = _write_config(config_dir)
            morning = datetime(2026, 8, 15, 6, 30, tzinfo=timezone.utc)
            evening = datetime(2026, 8, 15, 20, 0, tzinfo=timezone.utc)

            fetch_moon_relationship_insight(
                INSIGHT, opener, Path(cache_dir), config_path, now=morning
            )
            fetch_moon_relationship_insight(
                INSIGHT, opener, Path(cache_dir), config_path, now=evening
            )

        self.assertEqual(calls["count"], 1)

    @patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"})
    def test_refetches_on_new_local_day(self) -> None:
        calls = {"count": 0}

        def opener(request, timeout):
            calls["count"] += 1
            return _openai_response()

        with tempfile.TemporaryDirectory() as cache_dir, tempfile.TemporaryDirectory() as config_dir:
            config_path = _write_config(config_dir)
            day_one = datetime(2026, 8, 15, 6, 30, tzinfo=timezone.utc)
            day_two = datetime(2026, 8, 16, 6, 30, tzinfo=timezone.utc)

            fetch_moon_relationship_insight(
                INSIGHT, opener, Path(cache_dir), config_path, now=day_one
            )
            fetch_moon_relationship_insight(
                INSIGHT, opener, Path(cache_dir), config_path, now=day_two
            )

        self.assertEqual(calls["count"], 2)

    def test_raises_when_config_file_missing(self) -> None:
        def opener(request, timeout):
            raise AssertionError("mag niet worden aangeroepen zonder config")

        with tempfile.TemporaryDirectory() as cache_dir, tempfile.TemporaryDirectory() as config_dir:
            missing_path = Path(config_dir) / "moon-relationship.json"
            with self.assertRaises(OSError):
                fetch_moon_relationship_insight(
                    INSIGHT, opener, Path(cache_dir), missing_path
                )


if __name__ == "__main__":
    unittest.main()
