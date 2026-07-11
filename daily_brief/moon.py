from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .cache import DEFAULT_CACHE_DIR
from .models import MoonInsight


EPHEMERIS_FILE = "de421.bsp"
ZODIAC_SIGNS = (
    "Ram",
    "Stier",
    "Tweelingen",
    "Kreeft",
    "Leeuw",
    "Maagd",
    "Weegschaal",
    "Schorpioen",
    "Boogschutter",
    "Steenbok",
    "Waterman",
    "Vissen",
)

# Fasegrenzen als (max. faseho ek in graden, naam, samenvatting, doe-tip).
# Gebaseerd op de 8 maanfasen uit Maan-Dagelijkse-Gids-Jos.pdf.
PHASES = (
    (45, "Nieuwe Maan", "Energie is laag, je bent naar binnen gekeerd.", "Stel intenties, plan, rust uit."),
    (90, "Wassende Sikkel", "Energie keert langzaam terug, motivatie groeit.", "Zet een eerste kleine stap."),
    (135, "Eerste Kwartier", "Spanning en obstakels vragen om een keuze.", "Hak een knoop door."),
    (180, "Wassende Gibbeuze", "Hoge energie, focus op details en verfijning.", "Verfijn een lopend project, waak voor perfectionisme."),
    (225, "Volle Maan", "Piek van emotionele intensiteit, alles komt naar boven.", "Oogst en vier, vermijd grote beslissingen."),
    (270, "Afnemende Gibbeuze", "Energie daalt, reflectie en dankbaarheid overheersen.", "Deel wat je geleerd hebt."),
    (315, "Derde Kwartier", "Innerlijke spanning om los te laten.", "Laat los, maak ruimte."),
    (360, "Afnemende Sikkel", "Laagste energie van de cyclus, behoefte aan alleen-zijn.", "Rust en bereid je voor op een nieuw begin."),
)

# Persoonlijke notitie voor Jos (Zon Kreeft / Maan Schorpioen), per fase.
PERSONAL_NOTES = {
    "Nieuwe Maan": "Als Kreeft extra gevoelig: gun jezelf stilte.",
    "Wassende Sikkel": "Als Kreeft: koester nieuwe ideeën als zaden.",
    "Eerste Kwartier": "Als Kreeft: let op terugtrekken in je schulp.",
    "Wassende Gibbeuze": "Dit is je geboortefase, je natuurlijke ritme.",
    "Volle Maan": "Als Kreeft extra gevoelig: plan bewust rusttijd in.",
    "Afnemende Gibbeuze": "Als Kreeft: goede tijd om voor anderen te zorgen.",
    "Derde Kwartier": "Als Kreeft lastig: je houdt vast, oefen bewust loslaten.",
    "Afnemende Sikkel": "Als Kreeft: luister naar je lichaam, het vraagt om rust.",
}

# Extra duiding wanneer de maan zelf door Kreeft of Schorpioen staat.
ZODIAC_NOTES = {
    "Kreeft": "Maan in Kreeft: verhoogde emotionaliteit, sterke intuïtie — je krachtigste dagen voor intuïtieve beslissingen.",
    "Schorpioen": "Maan in Schorpioen, jouw maanretour: maximale intensiteit — goede dagen voor journaling, vermijd zware gesprekken.",
}


@dataclass
class MoonFetchResult:
    insight: MoonInsight
    stale: bool = False


def _phase_name(phase_angle_degrees: float) -> str:
    for max_degrees, name, _summary, _tip in PHASES:
        if phase_angle_degrees < max_degrees:
            return name
    return PHASES[0][1]


def _phase_details(phase_name: str):
    for _max_degrees, name, summary, tip in PHASES:
        if name == phase_name:
            return summary, tip
    return "", ""


def _zodiac_sign(ecliptic_longitude_degrees: float) -> str:
    index = int(ecliptic_longitude_degrees // 30) % 12
    return ZODIAC_SIGNS[index]


def _build_insight(phase_angle_degrees: float, ecliptic_longitude_degrees: float) -> MoonInsight:
    phase_name = _phase_name(phase_angle_degrees)
    summary, tip = _phase_details(phase_name)
    sign = _zodiac_sign(ecliptic_longitude_degrees)
    personal_note = PERSONAL_NOTES.get(phase_name, "")
    zodiac_note = ZODIAC_NOTES.get(sign)
    if zodiac_note:
        personal_note = f"{personal_note} {zodiac_note}".strip()
    return MoonInsight(
        phase_name=phase_name,
        zodiac_sign=sign,
        summary=summary,
        tip=tip,
        personal_note=personal_note,
    )


def fetch_moon_insight(
    cache_dir: Path = DEFAULT_CACHE_DIR,
    now: Optional[datetime] = None,
) -> MoonFetchResult:
    from skyfield import almanac
    from skyfield.api import Loader

    current_time = now or datetime.now(timezone.utc)

    cache_dir.mkdir(parents=True, exist_ok=True)
    loader = Loader(str(cache_dir))
    eph = loader(EPHEMERIS_FILE)
    ts = loader.timescale()
    t = ts.from_datetime(current_time.astimezone(timezone.utc))

    phase_angle = almanac.moon_phase(eph, t).degrees
    earth, moon = eph["earth"], eph["moon"]
    _lat, lon, _dist = earth.at(t).observe(moon).ecliptic_latlon()

    return MoonFetchResult(_build_insight(phase_angle, lon.degrees))
