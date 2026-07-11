import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo

from .cache import DEFAULT_CACHE_DIR, load_with_cache
from .models import Weather


API_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = ZoneInfo("Europe/Amsterdam")

WEATHER_SUMMARIES = {
    0: "Onbewolkt",
    1: "Overwegend helder",
    2: "Halfbewolkt",
    3: "Bewolkt",
    45: "Mistig",
    48: "Mist met rijp",
    51: "Lichte motregen",
    53: "Motregen",
    55: "Stevige motregen",
    56: "Lichte ijzel",
    57: "IJzel",
    61: "Lichte regen",
    63: "Regen",
    65: "Zware regen",
    66: "Lichte ijsregen",
    67: "IJsregen",
    71: "Lichte sneeuw",
    73: "Sneeuw",
    75: "Zware sneeuw",
    77: "Sneeuwkorrels",
    80: "Lichte buien",
    81: "Buien",
    82: "Zware buien",
    85: "Lichte sneeuwbuien",
    86: "Zware sneeuwbuien",
    95: "Onweer",
    96: "Onweer met hagel",
    99: "Zwaar onweer met hagel",
}


def _settings() -> Dict[str, str]:
    return {
        "latitude": os.getenv("DAILY_BRIEF_LATITUDE", "51.6861"),
        "longitude": os.getenv("DAILY_BRIEF_LONGITUDE", "5.1314"),
        "location": os.getenv("DAILY_BRIEF_LOCATION", "Drunen"),
    }


def _parse(payload: Dict, location: str) -> Weather:
    daily = payload["daily"]
    return Weather(
        summary=WEATHER_SUMMARIES.get(int(daily["weather_code"][0]), "Wisselvallig"),
        low_c=round(float(daily["temperature_2m_min"][0])),
        high_c=round(float(daily["temperature_2m_max"][0])),
        rain_chance=round(float(daily["precipitation_probability_max"][0])),
        location=location,
    )


@dataclass
class WeatherResult:
    weather: Weather
    stale: bool = False


def fetch_weather_with_status(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    opener: Callable = urlopen,
    now: Optional[datetime] = None,
) -> WeatherResult:
    local_now = now or datetime.now(TIMEZONE)
    settings = _settings()

    def load() -> Dict:
        query = urlencode(
            {
                "latitude": settings["latitude"],
                "longitude": settings["longitude"],
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "timezone": "auto",
                "forecast_days": 1,
            }
        )
        with opener(f"{API_URL}?{query}", timeout=10) as response:
            return json.load(response)

    cached = load_with_cache(
        f"weather-{local_now.date().isoformat()}",
        load,
        fresh_for=timedelta(hours=3),
        stale_for=timedelta(days=1),
        cache_dir=cache_dir,
        now=local_now,
    )
    return WeatherResult(_parse(cached.payload, settings["location"]), cached.stale)


def fetch_weather(
    cache_path: Optional[Path] = None,
    opener: Callable = urlopen,
) -> Weather:
    cache_dir = cache_path.parent if cache_path else DEFAULT_CACHE_DIR
    return fetch_weather_with_status(cache_dir, opener).weather
