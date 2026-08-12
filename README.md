# Jos Daily Brief

Een persoonlijke ochtendbrief op 80 mm bonpapier, geprint via een Epson
ESC/POS-thermische printer. Zonder aangesloten printer (bijv. lokaal
ontwikkelen) wordt de bon als PNG opgeslagen.

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

Met een aangesloten thermische printer print je dezelfde bon direct via
ESC/POS:

```bash
python -m daily_brief --print
```

In productie draait dit in Docker op een Proxmox-VM, zie
["Docker (productie)"](#docker-productie) hieronder.

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

## Docker (productie)

Productie draait in Docker op een Proxmox-VM (repo in `~/jos-daily-brief`),
niet meer op de oorspronkelijke Raspberry Pi.

```bash
docker compose build
docker compose run --rm daily-brief --text     # testen zonder te printen
docker compose run --rm daily-brief --print    # echte bon
```

`docker-compose.yml` bind-mount't `./config`, `./cache` en `./output` naar de
container (die als root draait, dus `/root/.config/jos-daily-brief` etc.) en
leest secrets uit `.env` (`chmod 600`, alleen op de VM ingevuld — nooit in
git of in een chatgesprek). De thermische printer wordt via USB doorgezet:
eerst Proxmox host → VM (Hardware → Add → USB Device in de Proxmox-UI), dan
VM → container via `devices: /dev/usb/lp0` in de compose-file.

Voor de eenmalige/incidentele Google-login draait een los `google-login`
compose-service, zie de sectie "Verjaardagen uit Google Contacts" hieronder.

### Elke ochtend automatisch een bon

Een systemd **system**-timer op de VM (niet in dit repo, geïnstalleerd op
`/etc/systemd/system/`) draait dagelijks om 06:30:

```bash
sudo cp deploy/docker/jos-daily-brief.service /etc/systemd/system/
sudo cp deploy/docker/jos-daily-brief.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now jos-daily-brief.timer
```

Controleren:

```bash
systemctl list-timers jos-daily-brief.timer
sudo journalctl -u jos-daily-brief.service   # sudo nodig voor de output
```

`Persistent=true` haalt een gemiste run in (bijv. na een VM-reboot rond
06:30). Om tijdelijk geen bon te printen (bijv. vakantie) zonder de timer
aan te raken, zet je `DAILY_BRIEF_PAUSE_FROM`/`DAILY_BRIEF_PAUSE_UNTIL`
(ISO-datums, inclusief) in `.env` — `--print` slaat die periode stil over,
`--text` blijft altijd werken. Zie `.env.example`.

## Verjaardagen uit Google Contacts

Schakel de Google People API in, maak OAuth-inloggegevens voor een
desktoptoepassing en bewaar het gedownloade bestand als:

```text
~/.config/jos-daily-brief/google-credentials.json
```

Meld daarna eenmalig aan. Draai je dit in Docker op een andere machine dan
waar je browser op staat (bijv. de Proxmox-VM), open dan eerst een
SSH-tunnel naar de vaste inlogpoort (8765) en start de login-container met
diezelfde poort doorgezet:

```bash
ssh -L 8765:localhost:8765 jos@192.168.1.107   # lokaal, op je Mac
docker compose run --rm google-login            # op de VM
```

Open de geprinte URL in de browser op je Mac; de tunnel zorgt dat de
redirect naar `localhost:8765` bij de container terechtkomt. Draai je lokaal
zonder Docker, dan volstaat:

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

Meld eenmalig aan (device-code-flow, dus geen lokale redirect-server nodig
— werkt identiek lokaal of in de Docker-container op de VM):

```bash
python -m daily_brief.microsoft login
```

De vernieuwbare token-cache komt buiten het project te staan in
`~/.config/jos-daily-brief/` en krijgt automatisch bestandsrechten `0600`.

## AI-nieuws en Synology

De nieuwssectie doorzoekt GDELT op AI-gerelateerd nieuws van de afgelopen 24
uur (met een voorkeur voor Anthropic/Claude, zie de query in
`daily_brief/news.py`). OpenAI selecteert daaruit maximaal vijf onderwerpen
en schrijft per onderwerp vijf korte Nederlandse samenvattingsregels. Stel in:

```bash
OPENAI_API_KEY="jouw-api-key"
OPENAI_NEWS_MODEL="gpt-5.4-mini"
```

Geen registratie of API-sleutel nodig voor de nieuwsbron zelf (GDELT is
publiek toegankelijk). Optioneel kun je met `DAILY_BRIEF_RSS_FEEDS` extra
RSS/Atom-feeds als achtergrond meegeven, zie `.env.example`.

`daily_brief/reddit_news.py` bevat een eerdere, Reddit-gebaseerde variant van
deze sectie. Die staat uit sinds Reddit's "Responsible Builder
Policy" het aanmaken van een OAuth-app blokkeerde; de module blijft bestaan
voor het geval dat later oplost, maar wordt niet aangeroepen.

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
Wanneer dit bestand bestaat, krijgt SNMP voorrang op de DSM WebAPI. Het
Docker-image installeert de `snmp`-commandoregelclient al (zie
`Dockerfile`); draai je lokaal zonder Docker, installeer die dan zelf:

```bash
sudo apt install snmp   # of: brew install net-snmp
```

De NAS-sectie wordt alleen afgedrukt bij een concrete opslag-, temperatuur- of
Security Advisor-waarschuwing. Een gezonde NAS neemt dus geen ruimte in op de
bon. Alle broncaches staan in `~/.cache/jos-daily-brief/`.

## Verouderd: Raspberry Pi user-timer

De oorspronkelijke opzet draaide op een Raspberry Pi met een systemd
**user**-timer (`deploy/jos-daily-brief.service` + `.timer`, lokale venv
i.p.v. Docker). Dat is retired sinds de migratie naar Docker op de VM (zie
["Docker (productie)"](#docker-productie)); de bestanden staan er nog als
historische referentie maar worden niet meer gebruikt.

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
- `daily_brief/news.py`: AI-nieuws via GDELT (standaard), met optionele
  RSS/Atom-feeds als achtergrond
- `daily_brief/reddit_news.py`: eerdere Reddit-gebaseerde variant van de
  NIEUWS-sectie, momenteel niet aangeroepen (zie "AI-nieuws en Synology")
- `daily_brief/synology.py`: compacte DSM-systeem- en opslagstatus
- `daily_brief/renderer.py`: renderer voor een bon van 80 mm (PNG en ESC/POS)
- `daily_brief/__main__.py`: CLI-entrypoint (`--text`/`--print`), incl.
  vakantiepauze-check

Later vervangen we de testgegevens één voor één door echte koppelingen. De
renderer blijft daarbij hetzelfde.
