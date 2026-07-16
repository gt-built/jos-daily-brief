import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .cache import DEFAULT_CACHE_DIR, load_with_cache


SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]
CONFIG_DIR = Path.home() / ".config" / "jos-daily-brief"
CREDENTIALS_FILE = CONFIG_DIR / "google-credentials.json"
TOKEN_FILE = CONFIG_DIR / "google-token.json"


@dataclass
class GoogleBirthdaysResult:
    birthdays: List[str]
    stale: bool = False


LOGIN_PORT = 8765


def login() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not CREDENTIALS_FILE.exists():
        raise RuntimeError(f"Google OAuth-bestand ontbreekt: {CREDENTIALS_FILE}")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    credentials = flow.run_local_server(host="0.0.0.0", port=LOGIN_PORT, open_browser=False)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
    TOKEN_FILE.chmod(0o600)
    print("Google Contacts is gekoppeld.")


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN_FILE.exists():
        raise RuntimeError("Voer eerst uit: python -m daily_brief.google_contacts login")
    credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
        TOKEN_FILE.write_text(credentials.to_json(), encoding="utf-8")
        TOKEN_FILE.chmod(0o600)
    if not credentials.valid:
        raise RuntimeError("Google Contacts-token is niet geldig")
    return credentials


def _birthdays_for_day(people: Iterable[Dict], day: date) -> List[str]:
    names = []
    for person in people:
        birthday_dates = [
            birthday.get("date", {}) for birthday in person.get("birthdays", [])
        ]
        if not any(
            value.get("month") == day.month and value.get("day") == day.day
            for value in birthday_dates
        ):
            continue
        display_name = next(
            (
                name.get("displayName")
                for name in person.get("names", [])
                if name.get("displayName")
            ),
            None,
        )
        if display_name:
            names.append(display_name)
    return sorted(set(names), key=str.casefold)


def fetch_google_birthdays(
    service=None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    today: Optional[date] = None,
) -> GoogleBirthdaysResult:
    current_day = today or date.today()

    def load() -> Dict:
        nonlocal service
        if service is None:
            from googleapiclient.discovery import build

            service = build(
                "people", "v1", credentials=_credentials(), cache_discovery=False
            )
        people = []
        page_token = None
        while True:
            response = (
                service.people()
                .connections()
                .list(
                    resourceName="people/me",
                    pageSize=1000,
                    personFields="names,birthdays",
                    pageToken=page_token,
                )
                .execute()
            )
            people.extend(response.get("connections", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break
        return {"people": people}

    cached = load_with_cache(
        f"google-birthdays-{current_day.isoformat()}",
        load,
        fresh_for=timedelta(hours=6),
        stale_for=timedelta(days=1),
        cache_dir=cache_dir,
        now=datetime.combine(current_day, datetime.min.time(), timezone.utc),
    )
    return GoogleBirthdaysResult(
        _birthdays_for_day(cached.payload.get("people", []), current_day),
        cached.stale,
    )


def main() -> None:
    if sys.argv[1:] != ["login"]:
        raise SystemExit("Gebruik: python -m daily_brief.google_contacts login")
    login()


if __name__ == "__main__":
    main()
