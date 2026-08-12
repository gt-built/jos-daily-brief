import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import NewsItem
from .news import NewsResult

TWEAKERS_FEED_URL = "https://tweakers.net/feeds/nieuws.xml"
OPENAI_URL = "https://api.openai.com/v1/responses"
MAX_ITEMS = 5
AI_KEYWORDS_CASE_SENSITIVE = ("AI", "LLM")
AI_KEYWORDS_CASE_INSENSITIVE = (
    "kunstmatige intelligentie",
    "chatgpt",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "machine learning",
    "chatbot",
)


def _is_ai_news(title: str, description: str) -> bool:
    haystack = f"{title} {description}"
    lowered = haystack.lower()
    if any(keyword in lowered for keyword in AI_KEYWORDS_CASE_INSENSITIVE):
        return True
    return any(
        re.search(rf"(?<![A-Za-z]){keyword}(?![A-Za-z])", haystack)
        for keyword in AI_KEYWORDS_CASE_SENSITIVE
    )


def _fetch_candidates(opener: Callable) -> List[Dict]:
    request = Request(TWEAKERS_FEED_URL, headers={"User-Agent": "JosDailyBrief/1.0"})
    with opener(request, timeout=20) as response:
        root = ET.fromstring(response.read())
    candidates = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        if title and _is_ai_news(title, description):
            candidates.append({"title": title, "description": description})
        if len(candidates) == MAX_ITEMS:
            break
    return candidates


def _response_text(payload: Dict) -> str:
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise ValueError("OpenAI-response bevat geen tekst")


def _summarize(candidates: List[Dict], opener: Callable) -> List[List[str]]:
    api_key = os.environ["OPENAI_API_KEY"]
    schema = {
        "type": "object",
        "properties": {
            "summaries": {
                "type": "array",
                "minItems": len(candidates),
                "maxItems": len(candidates),
                "items": {
                    "type": "object",
                    "properties": {
                        "lines": {
                            "type": "array",
                            "minItems": 5,
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["lines"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["summaries"],
        "additionalProperties": False,
    }
    body = {
        "model": os.getenv("OPENAI_NEWS_MODEL", "gpt-5.4-mini"),
        "instructions": (
            "Schrijf voor elk aangeleverde Tweakers AI-nieuwsbericht, in dezelfde "
            "volgorde als aangeleverd, een samenvatting van exact vijf compacte "
            "Nederlandse regels. Gebruik uitsluitend de aangeleverde titel en "
            "omschrijving als bron."
        ),
        "input": json.dumps(candidates, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "tweakers_ai_news",
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
        payload = json.loads(_response_text(json.load(response)))
    return [entry["lines"] for entry in payload["summaries"]]


def fetch_tweakers_news(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> NewsResult:
    def load() -> Dict:
        candidates = _fetch_candidates(opener)
        if not candidates:
            raise OSError("Geen AI-nieuws gevonden op Tweakers")
        summaries = _summarize(candidates, opener)
        return {
            "items": [
                {"title": candidate["title"], "lines": lines}
                for candidate, lines in zip(candidates, summaries)
            ]
        }

    cached = load_with_cache(
        "tweakers-ai-news",
        load,
        fresh_for=timedelta(minutes=30),
        stale_for=timedelta(hours=2),
        cache_dir=cache_dir,
        now=now,
    )
    items = [
        NewsItem(entry["title"], "Tweakers", "\n".join(entry["lines"]))
        for entry in cached.payload.get("items", [])[:MAX_ITEMS]
    ]
    return NewsResult(items, cached.stale, [])
