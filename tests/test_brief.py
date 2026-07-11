import unittest

from daily_brief.brief import build_daily_brief


def unavailable():
    raise OSError("offline")


class BriefTests(unittest.TestCase):
    def test_multiple_outages_still_create_complete_brief(self) -> None:
        brief = build_daily_brief(
            weather_fetcher=unavailable,
            brainjos_fetcher=unavailable,
            agenda_fetcher=unavailable,
            news_fetcher=unavailable,
            synology_fetcher=unavailable,
            formula_one_fetcher=unavailable,
            birthday_fetcher=unavailable,
            moon_fetcher=unavailable,
            extra_tasks_fetcher=unavailable,
            teletekst_fetcher=unavailable,
        )

        self.assertEqual(brief.agenda, [])
        self.assertEqual(brief.tasks, [])
        self.assertEqual(brief.news, [])
        self.assertFalse(brief.synology_status.reachable)
        self.assertEqual(len(brief.source_notes), 9)

    def test_extra_tasks_are_not_appended_to_q1_priorities(self) -> None:
        from daily_brief.models import Task

        brief = build_daily_brief(
            weather_fetcher=unavailable,
            brainjos_fetcher=lambda: type(
                "Result", (), {"tasks": [Task("BrainJos-taak")], "stale": False}
            )(),
            agenda_fetcher=unavailable,
            news_fetcher=unavailable,
            synology_fetcher=unavailable,
            formula_one_fetcher=unavailable,
            birthday_fetcher=unavailable,
            moon_fetcher=unavailable,
            extra_tasks_fetcher=lambda: [Task("Marcel Buurman bellen")],
        )

        self.assertEqual(
            [task.title for task in brief.tasks],
            ["BrainJos-taak"],
        )
