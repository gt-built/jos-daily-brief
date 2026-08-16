import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import MoonInsight


TIMEZONE = ZoneInfo("Europe/Amsterdam")
OPENAI_URL = "https://api.openai.com/v1/responses"
CONFIG_PATH = Path.home() / ".config" / "jos-daily-brief" / "moon-relationship.json"

# Jos' profiel staat al publiek in moon.py; Malou's profiel is privacygevoelig
# (geboortedatum, MBTI) en komt daarom uit een niet-gecommit configbestand
# (zie README, sectie "Maan-relatie").
JOS_PROFILE = {
    "name": "Jos",
    "sun_sign": "Kreeft",
    "moon_sign": "Schorpioen",
    "mbti": "ENFJ",
}


@dataclass
class MoonRelationshipResult:
    text: str
    stale: bool = False


def _load_malou_profile(config_path: Path) -> Dict:
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return data["malou"]


def _response_text(payload: Dict) -> str:
    for output in payload.get("output", []):
        for content in output.get("content", []):
            if content.get("type") == "output_text":
                return content.get("text", "")
    raise ValueError("OpenAI-response bevat geen tekst")


def _generate(insight: MoonInsight, malou: Dict, opener: Callable) -> str:
    api_key = os.environ["OPENAI_API_KEY"]
    schema = {
        "type": "object",
        "properties": {"analysis": {"type": "string"}},
        "required": ["analysis"],
        "additionalProperties": False,
    }
    body = {
        "model": os.getenv("OPENAI_NEWS_MODEL", "gpt-5.4-mini"),
        "instructions": (
            "Schrijf een Nederlandse relatie-analyse van maximaal vijf zinnen, "
            "als één doorlopende alinea (geen opsomming, geen losse regels — "
            "laat de zinnen gewoon op elkaar volgen). Baseer je op de "
            "aangeleverde maanfase, het maanteken en de astrologische "
            "profielen van de twee partners. Beschrijf wat zij vandaag "
            "concreet in de omgang met elkaar kunnen merken — waar ze op "
            "elkaar aansluiten of juist kunnen wrijven — niet ieders dag apart."
        ),
        "input": json.dumps(
            {
                "phase_name": insight.phase_name,
                "zodiac_sign": insight.zodiac_sign,
                "summary": insight.summary,
                "tip": insight.tip,
                "jos": JOS_PROFILE,
                "malou": malou,
            },
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "moon_relationship",
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
    return payload["analysis"]


def fetch_moon_relationship_insight(
    insight: MoonInsight,
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    config_path: Path = CONFIG_PATH,
    now: Optional[datetime] = None,
) -> MoonRelationshipResult:
    local_now = (now or datetime.now(TIMEZONE)).astimezone(TIMEZONE)

    def load() -> Dict:
        malou = _load_malou_profile(config_path)
        return {"text": _generate(insight, malou, opener)}

    cached = load_with_cache(
        f"moon-relationship-{local_now.date().isoformat()}",
        load,
        fresh_for=timedelta(hours=20),
        stale_for=timedelta(days=1),
        cache_dir=cache_dir,
        now=local_now,
    )
    return MoonRelationshipResult(cached.payload["text"], cached.stale)
