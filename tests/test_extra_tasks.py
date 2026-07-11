import tempfile
import unittest
from pathlib import Path

from daily_brief.extra_tasks import fetch_extra_tasks


class ExtraTasksTests(unittest.TestCase):
    def test_missing_file_returns_no_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra-taken.txt"
            self.assertEqual(fetch_extra_tasks(path), [])

    def test_reads_one_task_per_line_and_skips_blanks_and_comments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "extra-taken.txt"
            path.write_text(
                "Marcel Buurman bellen\n"
                "\n"
                "# dit is een opmerking\n"
                "Ingeborg bellen\n",
                encoding="utf-8",
            )

            tasks = fetch_extra_tasks(path)

        self.assertEqual(
            [task.title for task in tasks],
            ["Marcel Buurman bellen", "Ingeborg bellen"],
        )
