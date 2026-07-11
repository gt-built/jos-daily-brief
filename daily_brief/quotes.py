from datetime import date


TAOIST_QUOTES = (
    "Wie vertraagt, ziet de weg.",
    "Zacht water vindt altijd ruimte.",
    "Laat los wat niet geduwd hoeft te worden.",
    "In eenvoud ontstaat helderheid.",
    "Wie meebeweegt, blijft in evenwicht.",
    "Een lege kom kan ontvangen.",
    "De kleine stap kent geen haast.",
)


def taoist_quote(day: date) -> str:
    return TAOIST_QUOTES[day.toordinal() % len(TAOIST_QUOTES)]
