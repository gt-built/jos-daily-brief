import unittest

from daily_brief.brief import build_daily_brief
from daily_brief.models import MoonInsight


def unavailable():
    raise OSError("offline")


def unavailable_with_arg(_insight):
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
            moon_relationship_fetcher=unavailable_with_arg,
            extra_tasks_fetcher=unavailable,
            teletekst_fetcher=unavailable,
        )

        self.assertEqual(brief.agenda, [])
        self.assertEqual(brief.tasks, [])
        self.assertEqual(brief.news, [])
        self.assertFalse(brief.synology_status.reachable)
        self.assertEqual(brief.moon_relationship, "")
        self.assertEqual(len(brief.source_notes), 9)

    def test_moon_relationship_uses_available_moon_insight(self) -> None:
        moon_insight = MoonInsight("Volle Maan", "Kreeft", "Piek.", "Vier het.")
        received = {}

        def moon_fetcher():
            return type("Result", (), {"insight": moon_insight, "stale": False})()

        def moon_relationship_fetcher(insight):
            received["insight"] = insight
            return type("Result", (), {"text": "Een lopende analyse.", "stale": False})()

        brief = build_daily_brief(
            weather_fetcher=unavailable,
            brainjos_fetcher=unavailable,
            agenda_fetcher=unavailable,
            news_fetcher=unavailable,
            synology_fetcher=unavailable,
            formula_one_fetcher=unavailable,
            birthday_fetcher=unavailable,
            moon_fetcher=moon_fetcher,
            moon_relationship_fetcher=moon_relationship_fetcher,
            extra_tasks_fetcher=unavailable,
            teletekst_fetcher=unavailable,
        )

        self.assertEqual(brief.moon_relationship, "Een lopende analyse.")
        self.assertIs(received["insight"], moon_insight)

    def test_moon_relationship_unavailable_when_fetcher_fails(self) -> None:
        moon_insight = MoonInsight("Volle Maan", "Kreeft", "Piek.", "Vier het.")

        def moon_fetcher():
            return type("Result", (), {"insight": moon_insight, "stale": False})()

        brief = build_daily_brief(
            weather_fetcher=unavailable,
            brainjos_fetcher=unavailable,
            agenda_fetcher=unavailable,
            news_fetcher=unavailable,
            synology_fetcher=unavailable,
            formula_one_fetcher=unavailable,
            birthday_fetcher=unavailable,
            moon_fetcher=moon_fetcher,
            moon_relationship_fetcher=unavailable_with_arg,
            extra_tasks_fetcher=unavailable,
            teletekst_fetcher=unavailable,
        )

        self.assertEqual(brief.moon_relationship, "")
        self.assertIn("Maan-relatie: niet beschikbaar", brief.source_notes)

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
