import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import FormulaOneResult


RESULTS_URL = "https://api.jolpi.ca/ergast/f1/current/last/results.json"


@dataclass
class FormulaOneFetchResult:
    result: Optional[FormulaOneResult]
    stale: bool = False


def fetch_formula_one_result(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    today: Optional[date] = None,
) -> FormulaOneFetchResult:
    current_day = today or date.today()

    def load():
        request = Request(RESULTS_URL, headers={"Accept": "application/json"})
        with opener(request, timeout=10) as response:
            return json.load(response)

    cached = load_with_cache(
        "formula-one-latest-result",
        load,
        fresh_for=timedelta(hours=2),
        stale_for=timedelta(days=3),
        cache_dir=cache_dir,
        now=datetime.combine(current_day, time.min, timezone.utc),
    )
    races = cached.payload["MRData"]["RaceTable"].get("Races", [])
    if not races:
        return FormulaOneFetchResult(None, cached.stale)
    race = races[0]
    days_ago = (current_day - date.fromisoformat(race["date"])).days
    if days_ago < 0 or days_ago > 2:
        return FormulaOneFetchResult(None, cached.stale)

    results = race.get("Results", [])
    top_three = [
        f"{item['position']}. {item['Driver']['givenName']} {item['Driver']['familyName']}"
        for item in results[:3]
    ]
    max_entry = next(
        (item for item in results if item["Driver"].get("driverId") == "max_verstappen"),
        None,
    )
    if max_entry:
        position = max_entry.get("positionText", max_entry.get("position", "?"))
        max_result = f"Max Verstappen: P{position}"
        if position == "R":
            max_result = f"Max Verstappen: uitgevallen ({max_entry.get('status', 'DNF')})"
    else:
        max_result = "Max Verstappen: geen uitslag"
    return FormulaOneFetchResult(
        FormulaOneResult(race["raceName"], top_three, max_result),
        cached.stale,
    )
