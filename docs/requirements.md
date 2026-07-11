# Requirements — Jos Daily Brief

## REQ-ASTRO-001 — Persoonlijke maanstand (geïmplementeerd)

De dagelijkse bon bevat een compact onderdeel over de actuele maanstand in
relatie tot Jos' geboortehoroscoop.

Acceptatiecriteria:

- toont de actuele maanfase en relevante astrologische positie;
- koppelt deze aan de geboortehoroscoop van Jos;
- geeft in gewone Nederlandse taal aan wat Jos daar die dag mogelijk van merkt;
- formuleert de duiding als reflectie, niet als vaststaand feit of advies;
- gebruikt maximaal enkele regels, passend op 80 mm bonpapier;
- gebruikt caching en een nette fallback wanneer de bron niet beschikbaar is;
- behandelt geboortedatum, exacte geboortetijd en geboorteplaats als geheime
  persoonsgegevens en plaatst deze nooit in Git of logs.

Implementatie (`daily_brief/moon.py`):

- geboortegegevens (27-06-1977, 05:30, Willemstad) zijn niet in code
  vastgelegd — alleen het vaste resultaat daarvan (Zon in Kreeft, Maan in
  Schorpioen, geboren tijdens Wassende Gibbeuze) staat als duidingstabel in
  de module, overgenomen uit `docs/Maan-Dagelijkse-Gids-Jos.pdf`;
- de actuele maanfase en het actuele maanteken worden dagelijks live
  berekend met `skyfield` (DE421-ephemeris);
- geen bron-cache zoals de andere fetchers: de berekening is lokaal en
  netwerkonafhankelijk op de dag zelf, alleen de eenmalige ephemeris-download
  (~17 MB) wordt door skyfield zelf persistent bewaard in
  `~/.cache/jos-daily-brief/de421.bsp`;
- bij een onverwachte fout (bijv. ephemeris niet beschikbaar) valt de brief
  terug op het "Maan: niet beschikbaar"-bronbericht, zoals de andere secties.

## REQ-FIT-001 — Koppeling met Jos Fittracker

De dagelijkse bon bevat een compact persoonlijk gezondheidsoverzicht uit Jos'
eigen Fittracker.

Acceptatiecriteria:

- haalt gegevens automatisch en alleen-lezen op;
- toont uitsluitend vooraf gekozen kernwaarden, passend op de bon;
- vergelijkt waar nuttig met het persoonlijke doel of recente gemiddelde;
- gebruikt caching en een nette fallback zodat een storing de bon niet stopt;
- bewaart tokens en gezondheidsgegevens buiten Git met beperkte
  bestandsrechten;
- presenteert informatie als persoonlijke voortgang, niet als medisch advies.

Nog te bepalen bij implementatie:

- locatie en techniek van de Fittracker, bijvoorbeeld API, database of bestand;
- authenticatiemethode;
- gewenste waarden, zoals beweging, gewicht, slaap, training of herstel;
- bewaartermijn en privacyregels voor lokale cachegegevens.
