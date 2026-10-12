# Data

Projektet använder timvisa mätningar av PM2.5 från Malmö Dalaplan och väderobservationer från SMHI:s station Malmö A. De två datakällorna slås ihop på tidsstämpel.

## Källa och ansvarig

| Data | Ansvarig | Källa | Station |
|---|---|---|---|
| PM2.5, timvärden i µg/m³ | Naturvårdsverket. SMHI är datavärd för luftkvalitetsdata på uppdrag av Naturvårdsverket. Mätningarna vid Dalaplan görs av Malmö stad. | [Naturvårdsverkets webbtjänster för luftkvalitetsdata](https://www.naturvardsverket.se/amnesomraden/luft/statistik--utslapp-och-halter/luftkvaliteten-i-realtid-och-preliminar-statistik/webbtjanster-luftkvalitetsdata/), REST-API: `https://datavardluft.smhi.se/52North/api` | Malmö Dalaplan (gaturum), tidsserie 6247 |
| Väder, timvärden | SMHI | [SMHI:s öppna data för meteorologiska observationer](https://opendata.smhi.se/metobs/introduction), API: `https://opendata-download-metobs.smhi.se/api/version/1.0` | Malmö A, station 52350 |

**Väderparametrar:**

| Parameter | Nummer hos SMHI | Enhet |
|---|---|---|
| Lufttemperatur | 1 | °C |
| Vindriktning | 3 | grader (varifrån det blåser) |
| Vindhastighet | 4 | m/s |
| Relativ luftfuktighet | 6 | % |
| Nederbördsmängd | 7 | mm |

**Stationsval:** PM2.5-tidsserien vid Dalaplan har varit aktiv sedan 2023-05-26 och täcker hela projektperioden utan instrumentbyten. Malmö A är den närmaste aktiva SMHI-stationen till Dalaplan, cirka 4 km bort, och ingår i SMHI:s kärnnät (CORE), som SMHI själva övervakar och underhåller. Ingen luftstation närmare Malmö A mäter PM2.5.

## Användningsvillkor

- **Väderdata från SMHI** är öppna data under licensen Creative Commons Erkännande 4.0 (CC BY 4.0). Datan får användas, delas och bearbetas, även kommersiellt, om SMHI anges som källa och det framgår om datan har bearbetats. Se [SMHI:s frågor och svar om öppna data](https://www.smhi.se/data/om-smhis-data/fragor-och-svar).
- **Luftkvalitetsdata från Naturvårdsverket:** [fylls i senare]. API:et anger att tidsserien har licensinformation. Den går troligen att läsa på `https://datavardluft.smhi.se/52North/api/timeseries/6247/extras`, och annars kan datavärden kontaktas på datavardluft@smhi.se.

Båda API:erna är öppna och kräver ingen nyckel.

## När datan hämtades

| Datamängd | Period | Hämtad |
|---|---|---|
| PM2.5, träning | 2023-05-26 – 2025-12-31 | 2026-10-02 |
| Väder, träning | 2023-05-26 – 2025-12-31 | 2026-10-02 |
| PM2.5, validering | 2026-01-01 – 2026-04-30 | 2026-10-12 |
| Väder, validering | 2026-01-01 – 2026-04-30 | 2026-10-12 |
| Test | 2026-05-01 – | [fyll i] |

Hämtningsdatumet spelar roll eftersom de senaste mätvärdena är preliminära och kan korrigeras i efterhand. Data som hämtas vid ett senare tillfälle kan därför skilja sig något.

## Hur datan hämtas eller återskapas

All data i `data/` versionshanteras, så att alla i gruppen arbetar med exakt samma data. För att återskapa den från API:erna, ta bort filerna i `data/raw/`, `data/merged/` och `data/validated/` och kör från projektets rot:

    python main.py

`main.py` läser in `config.toml`, där perioder, stationer, API-adresser och filnamn definieras, och kör flödet i `src/orchestrator.py`:

1. **PM2.5** hämtas med `hamta_pm25` i `src/extracting_data.py`, en månad i taget, eftersom stora frågor mot API:et kan ta lång tid eller misslyckas. Datumen tolkas i svensk tid och slutdatumet ingår. Resultatet sparas i `data/raw/`.
2. **Väder** hämtas med `vader_data` i `src/extracting_data.py`. För varje parameter hämtas stationens hela kvalitetskontrollerade historik (`corrected-archive`), och perioden plockas sedan ut i koden. Resultatet sparas i `data/raw/`.
3. **Sammanslagning** av PM2.5 och väder på tidsstämpel. Resultatet sparas i `data/merged/`.
4. **Validering** med `validate_data` i `src/validate_process.py`. Resultatet sparas i `data/validated/`.

Steg 1–3 hoppas över om utdatafilen redan finns. Steg 4 körs alltid.

### Tidsperioder

| Period | Från | Till |
|---|---|---|
| Träning | 2023-05-26 | 2025-12-31 |
| Validering | 2026-01-01 | 2026-04-30 |
| Test | 2026-05-01 | [fyll i] |

**Viktigt:** Testdata från 2026-05-01 och framåt får inte hämtas eller committas under utvecklingen. Den används en gång, i slutet av projektet, för att utvärdera den slutliga modellen.

### Datamappar

| Mapp | Innehåll |
|---|---|
| `data/raw/` | Rådata som den hämtades från API:erna |
| `data/merged/` | PM2.5 och väder sammanslagna på tidsstämpel |
| `data/validated/` | Validerad data, sorterad i tidsordning med en rad per timme |
| `data/backup/` | [fylls i] |

## Förbehandling

### Validering

`validate_data` i `src/validate_process.py`:

1. gör om tidsstämplarna från text till riktig tid i svensk tidszon
2. sorterar raderna i tidsordning
3. kontrollerar att det inte finns dubbla tidsstämplar, och stoppar körningen om det gör det
4. lägger till tomma rader för timmar som saknas, så att det finns exakt en rad per timme
5. ersätter ogiltiga värden med saknade värden: negativ PM2.5, negativ vindhastighet, negativ nederbörd, luftfuktighet utanför 0–100 % och vindriktning utanför 0–360°
6. gör om vindriktningen 360° till 0°

Inga värden fylls i under valideringen.

### Saknade värden

Saknade värden fylls inte i, varken genom interpolation eller medelvärden. Rader där någon feature eller målet saknas tas bort efter att målet har skapats, så att målet alltid ligger exakt sex timmar fram.

Saknade värden i träningsdatan (22 825 timmar):

| Kolumn | Saknade timmar |
|---|---|
| PM2.5 | 154 |
| Lufttemperatur | 536 |
| Vindriktning | 572 |
| Vindhastighet | 572 |
| Relativ luftfuktighet | 570 |
| Nederbördsmängd | 1 069 |

Totalt tas 1 270 rader bort (cirka 5,6 %).

[fyll i f;r valideringsdatan]

Funktionerna för interpolation i `src/validate_process.py` (`preprocess_data`, `interpolate_short_gaps`, `interpolate_wind_direction` och `fill_short_rain_gaps`) finns kvar men används inte.

### Features

Målvariabeln är PM2.5-halten sex timmar senare. Som features används PM2.5, lufttemperatur, vindriktning (vind_cos och vind_sin), vindhastighet, relativ luftfuktighet och nederbördsmängd vid prediktionstillfället.

## Kvalitetsproblem

- **Preliminär data:** de senaste mätvärdena från båda API:erna är okontrollerade realtidsdata som kan ändras eller underkännas i efterhand.
- **Nederbörd saknas i hela dygnsblock:** luckorna börjar och slutar ofta vid samma klockslag, vilket tyder på att hela mätdygn har underkänts i SMHI:s kvalitetskontroll.
- **Vintertid i den sammanslagna filen:** när filerna slås ihop är tidsstämpeln text, och raderna sorteras i bokstavsordning. Vid omställningen till vintertid hamnar därför de två timmarna 02:00 i fel ordning, vilket ger fel mål på 12 rader om den sammanslagna filen används direkt. Den validerade filen sorteras på riktig tid och har inte det problemet.
- **Vindriktning 0° och 360°:** i SMHI:s data betyder 0° vindstilla och 360° vind rakt norrifrån. Valideringen gör om 360° till 0°, så efter valideringen går nordlig vind och vindstilla bara att skilja åt på vindhastigheten.

## Begränsningar

- **Väder hämtas bara från det kvalitetskontrollerade arkivet.** Arkivet släpar efter några månader. Om en period sträcker sig längre än arkivet blir det inget fel, utan väderkolumnerna tar bara slut. Testperioden och live-prognoser kräver därför att även SMHI:s perioder `latest-months` och `latest-day` används.
- **Skillnad mellan träning och drift:** modellerna tränas på kvalitetskontrollerade data, men live används okontrollerade realtidsvärden.
- **En station:** PM2.5 mäts i trafikmiljö vid Dalaplan och är inte nödvändigtvis representativ för andra delar av Malmö.
- **Avstånd mellan stationerna:** väderdatan kommer från en station cirka 4 km från Dalaplan, och de lokala vindförhållandena i ett gaturum kan skilja sig från dem vid Malmö A.
- **Kort historik:** PM2.5-tidsserien startade i maj 2023, så träningsdatan innehåller tre somrar och höstar men bara två vintrar och vårar.
