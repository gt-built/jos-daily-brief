import os
import json
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import NewsItem


DEFAULT_FEEDS = (
    ("NOS", "https://feeds.nos.nl/nosnieuwsalgemeen"),
    ("Tweakers", "https://feeds.feedburner.com/tweakers/mixed"),
)
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
OPENAI_URL = "https://api.openai.com/v1/responses"


@dataclass
class NewsResult:
    items: List[NewsItem]
    stale: bool = False
    unavailable_sources: List[str] = None

    def __post_init__(self) -> None:
        if self.unavailable_sources is None:
            self.unavailable_sources = []


class _DescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.description = ""

    def handle_starttag(self, tag, attrs) -> None:
        if tag.lower() != "meta" or self.description:
            return
        values = {key.lower(): value for key, value in attrs if value}
        if values.get("property", "").lower() == "og:description":
            self.description = values.get("content", "")
        elif values.get("name", "").lower() == "description":
            self.description = values.get("content", "")


def _article_description(opener: Callable, url: str) -> str:
    request = Request(url, headers={"User-Agent": "JosDailyBrief/1.0"})
    with opener(request, timeout=10) as response:
        payload = response.read(250_000).decode("utf-8", errors="ignore")
    parser = _DescriptionParser()
    parser.feed(payload)
    return " ".join(parser.description.split())[:1200]


def _safe_article_description(opener: Callable, url: str) -> str:
    try:
        return _article_description(opener, url)
    except Exception:
        return ""


def _response_text(payload: Dict) -> str:
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise ValueError("OpenAI-response bevat geen tekst")


def _summarize(candidates: List[Dict], opener: Callable) -> List[Dict]:
    api_key = os.environ["OPENAI_API_KEY"]
    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "lines": {
                            "type": "array",
                            "minItems": 5,
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["title", "source", "lines"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["topics"],
        "additionalProperties": False,
    }
    body = {
        "model": os.getenv("OPENAI_NEWS_MODEL", "gpt-5.4-mini"),
        "instructions": (
            "Selecteer maximaal drie wereldwijd relevante AI-onderwerpen. "
            "Gebruik uitsluitend de aangeleverde feiten. Schrijf een korte Nederlandse kop "
            "en exact vijf compacte Nederlandse samenvattingsregels per onderwerp."
        ),
        "input": json.dumps(candidates, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "daily_ai_news",
                "strict": True,
                "schema": schema,
            }
        },
    }
    request = Request(
        OPENAI_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with opener(request, timeout=45) as response:
        return json.loads(_response_text(json.load(response)))["topics"]


def _feeds() -> List[Tuple[str, str]]:
    configured = os.getenv("DAILY_BRIEF_RSS_FEEDS")
    if not configured:
        return list(DEFAULT_FEEDS)
    result = []
    for entry in configured.split(";"):
        name, separator, url = entry.partition("|")
        if separator and name.strip() and url.strip():
            result.append((name.strip(), url.strip()))
    return result or list(DEFAULT_FEEDS)


def _text(element, names: Tuple[str, ...]) -> str:
    for child in list(element):
        if child.tag.split("}")[-1] in names and child.text:
            return child.text.strip()
    return ""


def _published(element) -> datetime:
    raw = _text(element, ("pubDate", "published", "updated"))
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        value = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _parse(payload: bytes, source: str) -> List[Dict]:
    root = ET.fromstring(payload)
    entries = [
        element
        for element in root.iter()
        if element.tag.split("}")[-1] in ("item", "entry")
    ]
    return [
        {
            "title": _text(entry, ("title",)),
            "source": source,
            "published": _published(entry).isoformat(),
        }
        for entry in entries
        if _text(entry, ("title",))
    ]


def fetch_news(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> NewsResult:
    def load() -> Dict:
        params = urlencode(
            {
                "query": (
                    '("artificial intelligence" OR "generative AI" OR OpenAI '
                    "OR Anthropic OR Gemini) sourcelang:english"
                ),
                "mode": "ArtList",
                "maxrecords": "20",
                "format": "json",
                "sort": "HybridRel",
                "timespan": "24h",
            }
        )
        request = Request(
            f"{GDELT_URL}?{params}",
            headers={"User-Agent": "JosDailyBrief/1.0"},
        )
        with opener(request, timeout=20) as response:
            articles = json.load(response).get("articles", [])
        candidates = []
        for article in articles:
            url = article.get("url", "")
            title = article.get("title", "")
            if not url or not title:
                continue
            candidates.append(
                {
                    "title": title,
                    "source": article.get("domain", ""),
                    "description": _safe_article_description(opener, url),
                }
            )
            if len(candidates) == 10:
                break
        if not candidates:
            raise OSError("Geen bruikbare AI-artikelen uit de laatste 24 uur")
        return {"topics": _summarize(candidates, opener)}

    cached = load_with_cache(
        "ai-news",
        load,
        fresh_for=timedelta(minutes=30),
        stale_for=timedelta(hours=2),
        cache_dir=cache_dir,
        now=now,
    )
    items = [
        NewsItem(topic["title"], topic["source"], "\n".join(topic["lines"]))
        for topic in cached.payload.get("topics", [])[:3]
    ]
    return NewsResult(
        items,
        cached.stale,
        [],
    )
