import base64
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import NewsItem
from .news import NewsResult


REDDIT_USER_AGENT = "JosDailyBrief/1.0 (by /u/aehuizer)"
REDDIT_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
OPENAI_URL = "https://api.openai.com/v1/responses"
DEFAULT_SUBREDDITS = ("AI_Agents", "ClaudeAI", "technology")
MAX_POSTS = 5
MAX_LINES_PER_POST = 5


def _subreddits() -> List[str]:
    configured = os.getenv("DAILY_BRIEF_REDDIT_SUBREDDITS")
    if not configured:
        return list(DEFAULT_SUBREDDITS)
    result = [entry.strip() for entry in configured.split(";") if entry.strip()]
    return result or list(DEFAULT_SUBREDDITS)


def _access_token(opener: Callable) -> str:
    client_id = os.environ["REDDIT_CLIENT_ID"]
    client_secret = os.environ["REDDIT_CLIENT_SECRET"]
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    request = Request(
        REDDIT_TOKEN_URL,
        data=urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "Authorization": f"Basic {credentials}",
            "User-Agent": REDDIT_USER_AGENT,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with opener(request, timeout=15) as response:
        return json.load(response)["access_token"]


def _fetch_subreddit_posts(opener: Callable, subreddit: str, access_token: str) -> List[Dict]:
    request = Request(
        f"https://oauth.reddit.com/r/{subreddit}/top?limit=10&t=day",
        headers={
            "User-Agent": REDDIT_USER_AGENT,
            "Authorization": f"Bearer {access_token}",
        },
    )
    with opener(request, timeout=15) as response:
        payload = json.load(response)
    candidates = []
    for child in payload.get("data", {}).get("children", []):
        post = child.get("data", {})
        title = post.get("title", "")
        if not title:
            continue
        candidates.append(
            {
                "title": title,
                "source": f"r/{subreddit}",
                "score": post.get("score", 0),
                "context": (post.get("selftext") or post.get("url", ""))[:500],
            }
        )
    return candidates


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
            "posts": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_POSTS,
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "source": {"type": "string"},
                        "lines": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": MAX_LINES_PER_POST,
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["title", "source", "lines"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["posts"],
        "additionalProperties": False,
    }
    body = {
        "model": os.getenv("OPENAI_NEWS_MODEL", "gpt-5.4-mini"),
        "instructions": (
            "Selecteer de vijf meest relevante AI-gerelateerde Reddit-posts uit de "
            "aangeleverde kandidaten. Gebruik uitsluitend de aangeleverde feiten. "
            "Schrijf een korte Nederlandse kop en maximaal vijf compacte Nederlandse "
            "samenvattingsregels per post."
        ),
        "input": json.dumps(candidates, ensure_ascii=False),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "daily_reddit_ai_news",
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
        return json.loads(_response_text(json.load(response)))["posts"]


def fetch_reddit_news(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> NewsResult:
    def load() -> Dict:
        access_token = _access_token(opener)
        candidates = []
        unavailable = []
        for subreddit in _subreddits():
            try:
                candidates.extend(_fetch_subreddit_posts(opener, subreddit, access_token))
            except Exception:
                unavailable.append(f"r/{subreddit}")
        if not candidates:
            raise OSError("Geen bruikbare Reddit-posts uit de favoriete kanalen")
        return {"posts": _summarize(candidates, opener), "unavailable": unavailable}

    cached = load_with_cache(
        "reddit-ai-news",
        load,
        fresh_for=timedelta(minutes=30),
        stale_for=timedelta(hours=2),
        cache_dir=cache_dir,
        now=now,
    )
    items = [
        NewsItem(post["title"], post["source"], "\n".join(post["lines"]))
        for post in cached.payload.get("posts", [])[:MAX_POSTS]
    ]
    return NewsResult(
        items,
        cached.stale,
        cached.payload.get("unavailable", []),
    )
