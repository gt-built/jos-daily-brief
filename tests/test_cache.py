import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from daily_brief.cache import load_with_cache


class CacheTests(unittest.TestCase):
    def test_uses_fresh_cache_without_calling_loader(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            now = datetime(2026, 7, 2, tzinfo=timezone.utc)
            first = load_with_cache(
                "source",
                lambda: {"value": 1},
                timedelta(hours=1),
                timedelta(days=1),
                cache_dir,
                now,
            )
            second = load_with_cache(
                "source",
                lambda: self.fail("loader mag niet worden aangeroepen"),
                timedelta(hours=1),
                timedelta(days=1),
                cache_dir,
                now + timedelta(minutes=30),
            )

        self.assertEqual(first.payload, second.payload)
        self.assertFalse(second.stale)

    def test_uses_stale_cache_when_refresh_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            now = datetime(2026, 7, 2, tzinfo=timezone.utc)
            load_with_cache(
                "source",
                lambda: {"value": 1},
                timedelta(minutes=5),
                timedelta(hours=1),
                cache_dir,
                now,
            )
            result = load_with_cache(
                "source",
                lambda: (_ for _ in ()).throw(OSError("offline")),
                timedelta(minutes=5),
                timedelta(hours=1),
                cache_dir,
                now + timedelta(minutes=10),
            )

        self.assertTrue(result.stale)

    def test_corrupt_cache_does_not_hide_loader_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            (cache_dir / "source.json").write_text("{kapot", encoding="utf-8")
            with self.assertRaises(OSError):
                load_with_cache(
                    "source",
                    lambda: (_ for _ in ()).throw(OSError("offline")),
                    timedelta(minutes=5),
                    timedelta(hours=1),
                    cache_dir,
                )
