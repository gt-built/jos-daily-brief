# Jos Daily Brief

Een kleine, printer-onafhankelijke basis voor een persoonlijke ochtendbrief op
80 mm bonpapier. Zolang de Epson-printer er nog niet is, wordt de bon als PNG
opgeslagen.

De vastgelegde huidige en toekomstige wensen staan in
[`docs/requirements.md`](docs/requirements.md).

## Installeren

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Proefbon maken

```bash
python -m daily_brief
```

De bon verschijnt in `output/daily-brief.png`. Met `--text` kun je dezelfde
inhoud in de terminal bekijken:

```bash
python -m daily_brief --text
```

Op de Raspberry Pi print je dezelfde bon direct via ESC/POS:

```bash
python -m daily_brief --print
```

De weersverwachting wordt automatisch opgehaald bij Open-Meteo. De standaard
is Drunen, Noord-Brabant. Je kunt later een andere locatie instellen zonder
code te wijzigen:

```bash
export DAILY_BRIEF_LOCATION="Utrecht"
export DAILY_BRIEF_LATITUDE="52.0907"
export DAILY_BRIEF_LONGITUDE="5.1214"
python -m daily_brief
```

De laatst opgehaalde verwachting wordt lokaal bewaard. Bij een tijdelijke
internetstoring gebruikt de brief die cache; als er nog geen cache is, worden
de veilige testgegevens gebruikt.

Als `BRAINJOS_API_URL` en `BRAINJOS_API_TOKEN` zijn ingesteld, worden de
prioriteiten voor vandaag uit BrainJos opgehaald. De agenda komt rechtstreeks
uit Microsoft 365.

Onderaan staat iedere dag een korte, wisselende taoïstische gedachte.

## Verjaardagen uit Google Contacts

Schakel de Google People API in, maak OAuth-inloggegevens voor een
desktoptoepassing en bewaar het gedownloade bestand als:

```text
~/.config/jos-daily-brief/google-credentials.json
```

Meld daarna eenmalig aan:

```bash
python -m daily_brief.google_contacts login
```

De toepassing vraagt uitsluitend leesrechten voor Google Contacts. De
vernieuwbare token wordt met bestandsrechten `0600` buiten het project bewaard.

## Microsoft 365-agenda

Maak in Microsoft Entra een appregistratie voor een openbare client, schakel
device-code-aanmelding in en geef gedelegeerde toestemming voor
`Calendars.Read`. Zet daarna het client-ID in `.env`:

```bash
MS_GRAPH_CLIENT_ID="jouw-client-id"
MS_GRAPH_TENANT_ID="common"
```

Meld de Raspberry Pi eenmalig aan:

```bash
python -m daily_brief.microsoft login
```

De vernieuwbare token-cache komt buiten het project te staan in
`~/.config/jos-daily-brief/` en krijgt automatisch bestandsrechten `0600`.

## AI-nieuws en Synology

De nieuwssectie haalt AI-gerelateerde posts op uit je favoriete subreddits.
OpenAI selecteert daaruit de vijf meest relevante posts en schrijft per post
maximaal vijf korte Nederlandse samenvattingsregels. Stel in:

```bash
OPENAI_API_KEY="jouw-api-key"
OPENAI_NEWS_MODEL="gpt-5.4-mini"
DAILY_BRIEF_REDDIT_SUBREDDITS="AI_Agents;ClaudeAI;technology"
REDDIT_CLIENT_ID="jouw-client-id"
REDDIT_CLIENT_SECRET="jouw-client-secret"
```

Reddit vereist sinds 2023 OAuth, ook voor het lezen van publieke subreddits.
Maak op <https://old.reddit.com/prefs/apps> een app aan van het type
**script** (persoonlijk gebruik) en vul de client-ID (staat direct onder de
appnaam) en het secret hierboven in. `daily_brief/news.py` (GDELT + RSS)
blijft bestaan maar wordt niet meer standaard gebruikt; `DAILY_BRIEF_RSS_FEEDS`
heeft dus voorlopig geen effect.

Maak voor Synology een apart DSM-account met alleen leesrechten. Bewaar de
verbinding in `~/.config/jos-daily-brief/synology.json`:

```json
{
  "url": "https://192.168.1.10:5001",
  "username": "dailybrief",
  "password": "vul-hier-het-wachtwoord-in"
}
```

Beveilig het bestand met:

```bash
chmod 600 ~/.config/jos-daily-brief/synology.json
```

Voor een beperkt account gebruikt Daily Brief bij voorkeur SNMPv3. Zet de
SNMPv3-instellingen in
`~/.config/jos-daily-brief/synology-snmp.json` met bestandsrechten `0600`.
Wanneer dit bestand bestaat, krijgt SNMP voorrang op de DSM WebAPI. Installeer
op Raspberry Pi OS ook de commandoregelclient:

```bash
sudo apt install snmp
```

De NAS-sectie wordt alleen afgedrukt bij een concrete opslag-, temperatuur- of
Security Advisor-waarschuwing. Een gezonde NAS neemt dus geen ruimte in op de
bon. Alle broncaches staan in `~/.cache/jos-daily-brief/`.

## Elke ochtend automatisch een bon (Raspberry Pi)

Met een systemd user-timer maakt en print de Pi elke ochtend om 06:30
automatisch een nieuwe dagelijkse brief.

```bash
mkdir -p ~/.config/systemd/user
cp deploy/jos-daily-brief.service ~/.config/systemd/user/
cp deploy/jos-daily-brief.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now jos-daily-brief.timer
```

De service verwacht het project in `~/jos-daily-brief` met een venv in
`~/jos-daily-brief/.venv`. Wijk je van dat pad af, pas dan `WorkingDirectory`
en `ExecStart` in `deploy/jos-daily-brief.service` aan.

Handig om te controleren:

```bash
systemctl --user list-timers jos-daily-brief.timer
journalctl --user -u jos-daily-brief.service
```

Zorg dat `loginctl enable-linger $USER` is uitgevoerd, anders stopt de
user-timer zodra je uitlogt van je SSH-sessie.

## Opzet

- `daily_brief/cache.py`: gedeelde, atomair geschreven broncache
- `daily_brief/models.py`: printer-onafhankelijke inhoud van de brief
- `daily_brief/sample_data.py`: tijdelijke testgegevens
- `daily_brief/weather.py`: actuele weersverwachting via Open-Meteo
- `daily_brief/brainjos.py`: prioriteiten uit de beveiligde BrainJos-API
- `daily_brief/microsoft.py`: Microsoft Graph-agenda en device-code-login
- `daily_brief/google_contacts.py`: verjaardagen uit Google Contacts
- `daily_brief/formula_one.py`: laatste Formule 1-uitslag
- `daily_brief/moon.py`: dagelijkse maanstand en -teken, persoonlijk geduid
  voor Jos' geboortehoroscoop (zie `docs/requirements.md`)
- `daily_brief/news.py`: configureerbare RSS- en Atom-feeds
- `daily_brief/synology.py`: compacte DSM-systeem- en opslagstatus
- `daily_brief/renderer.py`: renderer voor een bon van 80 mm
- `daily_brief/__main__.py`: lokaal startcommando

Later vervangen we de testgegevens één voor één door echte koppelingen. De
renderer blijft daarbij hetzelfde. Zodra de Epson beschikbaar is, voegen we
naast de PNG-renderer een ESC/POS-uitvoer toe.
