from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional


@dataclass
class AgendaItem:
    time: str
    title: str
    location: str = ""


@dataclass
class Task:
    title: str
    important: bool = False


@dataclass
class NewsItem:
    title: str
    source: str
    summary: str = ""


@dataclass
class Weather:
    summary: str
    low_c: int
    high_c: int
    rain_chance: int
    location: str = ""


@dataclass
class SynologyStatus:
    reachable: bool
    storage_percent: Optional[int] = None
    warnings: List[str] = field(default_factory=list)
    stale: bool = False


@dataclass
class FormulaOneResult:
    race_name: str
    top_three: List[str]
    max_result: str


@dataclass
class MoonInsight:
    phase_name: str
    zodiac_sign: str
    summary: str
    tip: str
    personal_note: str = ""


@dataclass
class DailyBrief:
    day: date
    greeting: str
    weather: Weather
    birthdays: List[str] = field(default_factory=list)
    formula_one: Optional[FormulaOneResult] = None
    moon: Optional[MoonInsight] = None
    agenda: List[AgendaItem] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    teletekst: List[str] = field(default_factory=list)
    news: List[NewsItem] = field(default_factory=list)
    synology_status: Optional[SynologyStatus] = None
    source_notes: List[str] = field(default_factory=list)
    focus: str = ""
    quote: str = ""
