import json
import re
from html import unescape
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache


TELETEKST_URL = "https://teletekst-data.nos.nl/json/101-01"
HEADLINE_PATTERN = re.compile(
    r'<span class="cyan[^"]*">\s*(.*?)</span>\s*'
    r'<span class="yellow[^"]*">\s*<a[^>]*href="#(\d+)">(?:\d+)</a>',
    re.DOTALL,
)


@dataclass
class TeletekstResult:
    headlines: List[str]
    stale: bool = False


def _strings(value) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _clean(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" -\u00a0")


def _is_headline(line: str) -> bool:
    lowered = line.lower()
    if len(line) < 12:
        return False
    if "teletekst" in lowered or "nos.nl" in lowered:
        return False
    if re.fullmatch(r"\d{3}.*", line):
        return False
    return any(character.isalpha() for character in line)


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", "", value)


def _teletekst_headline(value: str) -> str:
    value = _clean(unescape(_strip_tags(value)))
    value = re.sub(r"\.{2,}$", "", value).strip()
    return value


def _parse_content(content: str, limit: int) -> List[str]:
    headlines: List[str] = []
    seen = set()
    for match in HEADLINE_PATTERN.finditer(content):
        title = _teletekst_headline(match.group(1))
        page = match.group(2)
        if not _is_headline(title) or title in seen:
            continue
        seen.add(title)
        headlines.append(f"{title} {page}")
        if len(headlines) == limit:
            break
    return headlines


def _parse(payload: Dict, limit: int) -> List[str]:
    content = payload.get("content")
    if isinstance(content, str):
        headlines = _parse_content(content, limit)
        if headlines:
            return headlines

    headlines: List[str] = []
    seen = set()
    for raw in _strings(payload):
        line = _clean(raw)
        if not _is_headline(line) or line in seen:
            continue
        seen.add(line)
        headlines.append(line)
        if len(headlines) == limit:
            break
    return headlines


def fetch_teletekst_headlines(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
    limit: int = 5,
) -> TeletekstResult:
    def load() -> Dict:
        request = Request(TELETEKST_URL, headers={"Accept": "application/json"})
        with opener(request, timeout=10) as response:
            return {"headlines": _parse(json.load(response), limit)}

    cached = load_with_cache(
        "teletekst-101",
        load,
        fresh_for=timedelta(minutes=15),
        stale_for=timedelta(hours=6),
        cache_dir=cache_dir,
        now=now,
    )
    return TeletekstResult(cached.payload.get("headlines", [])[:limit], cached.stale)
