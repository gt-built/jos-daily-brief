from datetime import date

from .models import AgendaItem, DailyBrief, NewsItem, Task, Weather
from .quotes import taoist_quote


def make_sample_brief(weather: Weather = None) -> DailyBrief:
    today = date.today()
    return DailyBrief(
        day=today,
        greeting="Goedemorgen Jos",
        weather=weather
        or Weather(
            summary="Fris, later zonnig",
            low_c=8,
            high_c=17,
            rain_chance=15,
            location="Testlocatie",
        ),
        agenda=[
            AgendaItem("09:00", "Weekstart", "Teams"),
            AgendaItem("11:30", "Focusblok: Daily Brief"),
            AgendaItem("15:00", "Afspraak in Utrecht", "Centrum"),
        ],
        tasks=[
            Task("Concept voor de week afronden", important=True),
            Task("E-mail aan leverancier beantwoorden"),
            Task("Boodschappenlijst bijwerken"),
        ],
        news=[
            NewsItem("AI-agents worden steeds praktischer", "Technieuws"),
            NewsItem("Nieuwe plannen voor duurzamer vervoer", "NOS"),
        ],
        focus="Maak eerst het belangrijkste af; houd de rest bewust klein.",
        quote=taoist_quote(today),
    )
