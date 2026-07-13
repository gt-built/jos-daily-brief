from typing import Callable

from .brainjos import fetch_brainjos_with_status
from .extra_tasks import fetch_extra_tasks
from .formula_one import fetch_formula_one_result
from .google_contacts import fetch_google_birthdays
from .microsoft import fetch_microsoft_agenda
from .models import SynologyStatus
from .moon import fetch_moon_insight
from .reddit_news import fetch_reddit_news
from .sample_data import make_sample_brief
from .synology import fetch_synology_status
from .teletekst import fetch_teletekst_headlines
from .weather import fetch_weather_with_status


def build_daily_brief(
    weather_fetcher: Callable = fetch_weather_with_status,
    brainjos_fetcher: Callable = fetch_brainjos_with_status,
    agenda_fetcher: Callable = fetch_microsoft_agenda,
    news_fetcher: Callable = fetch_reddit_news,
    synology_fetcher: Callable = fetch_synology_status,
    formula_one_fetcher: Callable = fetch_formula_one_result,
    birthday_fetcher: Callable = fetch_google_birthdays,
    moon_fetcher: Callable = fetch_moon_insight,
    extra_tasks_fetcher: Callable = fetch_extra_tasks,
    teletekst_fetcher: Callable = fetch_teletekst_headlines,
):
    brief = make_sample_brief()
    brief.agenda = []
    brief.tasks = []
    brief.news = []

    try:
        result = weather_fetcher()
        brief.weather = result.weather
        if result.stale:
            brief.source_notes.append("Weer: laatste stand")
    except Exception:
        brief.source_notes.append("Weer: testverwachting")

    try:
        result = agenda_fetcher()
        brief.agenda = result.agenda
        if result.stale:
            brief.source_notes.append("Agenda: laatste stand")
    except Exception:
        brief.source_notes.append("Agenda: niet beschikbaar")

    try:
        result = birthday_fetcher()
        brief.birthdays = result.birthdays
        if result.stale:
            brief.source_notes.append("Verjaardagen: laatste stand")
    except Exception:
        brief.source_notes.append("Verjaardagen: niet beschikbaar")

    try:
        result = formula_one_fetcher()
        brief.formula_one = result.result
        if result.stale:
            brief.source_notes.append("Formule 1: laatste stand")
    except Exception:
        brief.source_notes.append("Formule 1: niet beschikbaar")

    try:
        result = moon_fetcher()
        brief.moon = result.insight
        if result.stale:
            brief.source_notes.append("Maan: laatste stand")
    except Exception:
        brief.source_notes.append("Maan: niet beschikbaar")

    try:
        result = brainjos_fetcher()
        brief.tasks = result.tasks
        if result.stale:
            brief.source_notes.append("BrainJos: laatste stand")
    except Exception:
        brief.source_notes.append("BrainJos: niet beschikbaar")

    try:
        result = teletekst_fetcher()
        brief.teletekst = result.headlines
        if result.stale:
            brief.source_notes.append("Teletekst: laatste stand")
    except Exception:
        brief.source_notes.append("Teletekst: niet beschikbaar")

    try:
        result = news_fetcher()
        brief.news = result.items
        if result.stale:
            brief.source_notes.append("Nieuws: laatste stand")
        elif result.unavailable_sources:
            brief.source_notes.append(
                f"Nieuws: {', '.join(result.unavailable_sources)} niet bereikbaar"
            )
    except Exception:
        brief.source_notes.append("Nieuws: niet beschikbaar")

    try:
        brief.synology_status = synology_fetcher()
        if brief.synology_status.stale:
            brief.source_notes.append("NAS: laatste stand")
    except Exception:
        brief.synology_status = SynologyStatus(reachable=False)
        brief.source_notes.append("NAS: niet beschikbaar")

    return brief
