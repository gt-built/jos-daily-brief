import json
import os
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import AgendaItem, Task


TIMEZONE = ZoneInfo("Europe/Amsterdam")


def _period() -> Tuple[datetime, datetime]:
    now = datetime.now(TIMEZONE)
    start = datetime.combine(now.date(), time.min, TIMEZONE)
    return start, start + timedelta(days=1)


def _agenda_item(event: Dict) -> AgendaItem:
    starts_at = datetime.fromisoformat(event["start"].replace("Z", "+00:00"))
    item_time = "hele dag" if event.get("isAllDay") else starts_at.astimezone(TIMEZONE).strftime("%H:%M")
    return AgendaItem(
        time=item_time,
        title=event["title"],
        location=event.get("location", ""),
    )


def _items(value) -> Iterable[Dict]:
    if isinstance(value, dict):
        if "title" in value:
            yield value
        for child in value.values():
            yield from _items(child)
    elif isinstance(value, list):
        for child in value:
            yield from _items(child)


def _quadrant(item: Dict) -> str:
    for key in ("coveyQuadrant", "quadrant", "covey_quadrant"):
        if item.get(key):
            return str(item[key]).upper()
    return ""


def _q1_items(payload: Dict) -> List[Dict]:
    direct_items = payload.get("priorities", []) + payload.get("dueTasks", [])
    if direct_items:
        return [item for item in direct_items if _quadrant(item) == "Q1"]

    covey = payload.get("covey") or payload.get("quadrants") or payload.get("matrix")
    if isinstance(covey, dict):
        q1 = covey.get("Q1") or covey.get("q1")
        if isinstance(q1, list):
            return q1

    return [item for item in _items(payload) if _quadrant(item) == "Q1"]


def _tasks(payload: Dict) -> List[Task]:
    result = []
    seen = set()
    for item in _q1_items(payload):
        key = item.get("id") or item.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(Task(item["title"], important=True))
    return result


@dataclass
class BrainJosResult:
    agenda: List[AgendaItem]
    tasks: List[Task]
    stale: bool = False


def fetch_brainjos_with_status(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> BrainJosResult:
    api_url = os.environ["BRAINJOS_API_URL"]
    token = os.environ["BRAINJOS_API_TOKEN"]
    local_now = now or datetime.now(TIMEZONE)
    start = datetime.combine(local_now.date(), time.min, TIMEZONE)
    end = start + timedelta(days=1)

    def load() -> Dict:
        query = urlencode({"from": start.isoformat(), "to": end.isoformat()})
        request = Request(
            f"{api_url}?{query}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        with opener(request, timeout=10) as response:
            return json.load(response)

    cached = load_with_cache(
        f"brainjos-{local_now.date().isoformat()}",
        load,
        fresh_for=timedelta(minutes=15),
        stale_for=timedelta(days=1),
        cache_dir=cache_dir,
        now=local_now,
    )
    agenda = [_agenda_item(event) for event in cached.payload.get("calendarEvents", [])]
    return BrainJosResult(agenda, _tasks(cached.payload), cached.stale)


def fetch_brainjos(opener: Callable = urlopen) -> Tuple[List[AgendaItem], List[Task]]:
    result = fetch_brainjos_with_status(opener)
    return result.agenda, result.tasks
