import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import AgendaItem
from .settings import load_env_file


TIMEZONE = ZoneInfo("Europe/Amsterdam")
CONFIG_DIR = Path.home() / ".config" / "jos-daily-brief"
TOKEN_CACHE = CONFIG_DIR / "microsoft-token-cache.json"
SCOPES = ["Calendars.Read"]


@dataclass
class MicrosoftAgendaResult:
    agenda: List[AgendaItem]
    stale: bool = False


def _application(token_cache):
    import msal

    client_id = os.environ["MS_GRAPH_CLIENT_ID"]
    tenant = os.getenv("MS_GRAPH_TENANT_ID", "common")
    return msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant}",
        token_cache=token_cache,
    )


def _load_token_cache():
    import msal

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE.exists():
        cache.deserialize(TOKEN_CACHE.read_text(encoding="utf-8"))
    return cache


def _save_token_cache(cache) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE.write_text(cache.serialize(), encoding="utf-8")
    TOKEN_CACHE.chmod(0o600)


def login() -> None:
    cache = _load_token_cache()
    app = _application(cache)
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError("Microsoft device-login kon niet worden gestart")
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        raise RuntimeError(result.get("error_description", "Microsoft-login mislukt"))
    _save_token_cache(cache)
    print("Microsoft 365-agenda is gekoppeld.")


def _access_token() -> str:
    cache = _load_token_cache()
    app = _application(cache)
    accounts = app.get_accounts()
    if not accounts:
        raise RuntimeError("Voer eerst uit: python -m daily_brief.microsoft login")
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    if cache.has_state_changed:
        _save_token_cache(cache)
    if not result or "access_token" not in result:
        raise RuntimeError("Microsoft-token kon niet worden vernieuwd")
    return result["access_token"]


def _parse_event(event: Dict) -> AgendaItem:
    if event.get("isAllDay"):
        item_time = "hele dag"
    else:
        starts_at = datetime.fromisoformat(event["start"]["dateTime"].replace("Z", "+00:00"))
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=TIMEZONE)
        item_time = starts_at.astimezone(TIMEZONE).strftime("%H:%M")
    return AgendaItem(
        item_time,
        event.get("subject") or "(geen titel)",
        event.get("location", {}).get("displayName", ""),
    )


def fetch_microsoft_agenda(
    opener: Callable = urlopen,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
    access_token: Optional[str] = None,
) -> MicrosoftAgendaResult:
    local_now = now or datetime.now(TIMEZONE)
    start = datetime.combine(local_now.date(), time.min, TIMEZONE)
    end = start + timedelta(days=1)

    def load() -> Dict:
        params = urlencode(
            {
                "startDateTime": start.isoformat(),
                "endDateTime": end.isoformat(),
                "$select": "id,subject,start,end,isAllDay,location",
                "$top": "100",
                "$orderby": "start/dateTime",
            }
        )
        headers = {
            "Authorization": f"Bearer {access_token or _access_token()}",
            "Accept": "application/json",
            "Prefer": 'outlook.timezone="Europe/Amsterdam"',
        }

        def get(url: str) -> Dict:
            request = Request(
                url,
                headers=headers,
            )
            with opener(request, timeout=10) as response:
                return json.load(response)

        return get(f"https://graph.microsoft.com/v1.0/me/calendarView?{params}")

    cached = load_with_cache(
        f"microsoft-agenda-{local_now.date().isoformat()}",
        load,
        fresh_for=timedelta(minutes=15),
        stale_for=timedelta(days=1),
        cache_dir=cache_dir,
        now=local_now,
    )
    agenda = [_parse_event(event) for event in cached.payload.get("value", [])]
    return MicrosoftAgendaResult(agenda, cached.stale)


def main() -> None:
    load_env_file()
    if sys.argv[1:] != ["login"]:
        raise SystemExit("Gebruik: python -m daily_brief.microsoft login")
    login()


if __name__ == "__main__":
    main()
