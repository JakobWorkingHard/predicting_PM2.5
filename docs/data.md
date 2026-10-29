# Data

Projektet använder timvisa mätningar av PM2.5 från Malmö Dalaplan och väderobservationer från SMHI:s station Malmö A. De två källorna slås ihop på tidsstämpel. Perioderna beräknas dynamiskt vid varje körning (se nedan), för att få aktuell data behöver endast `python main.py` köras.

## Källor och ansvarig

| Data | Ansvarig | API | Station/tidsserie |
|---|---|---|---|
| PM2.5, timvärden i µg/m³ | Naturvårdsverket. SMHI är datavärd för luftkvalitetsdata på uppdrag av Naturvårdsverket; mätningarna vid Dalaplan görs av Malmö stad. | `https://datavardluft.smhi.se/52North/api` | Malmö Dalaplan (gaturum), tidsserie 6247, aktiv sedan 2023-05-26 |
| Väder, timvärden | SMHI | `https://opendata-download-metobs.smhi.se/api/version/1.0` | Malmö A, station 52350, ca 4 km från Dalaplan |

**Väderparametrar** (nummer hos SMHI):

| Parameter | Nummer | Enhet |
|---|---|---|
| Lufttemperatur | 1 | °C |
| Vindriktning | 3 | grader |
| Vindhastighet | 4 | m/s |
| Relativ luftfuktighet | 6 | % |
| Nederbördsmängd | 7 | mm |

**Stationsval:** PM2.5-serien vid Dalaplan täcker hela projektperioden utan instrumentbyten. Malmö A är närmaste aktiva SMHI-station och ingår i SMHI:s kärnnät (CORE), som SMHI själva övervakar och underhåller. Ingen luftstation närmare Malmö A mäter PM2.5.

## Licenser

- **Väderdata (SMHI):** öppna data under Creative Commons Erkännande 4.0 (CC BY 4.0). SMHI ska anges som källa och det ska framgå om datan har bearbetats.
- **Luftkvalitetsdata (Naturvårdsverket):** CC0 1.0 Universal (Public Domain Dedication).
- Båda API:erna är öppna och kräver ingen nyckel.

## Tidsperioder – beräknas dynamiskt

Perioderna räknas ut i `src/config.py` (`berakna_tranings_och_valideringsperiod`) vid varje körning och styrs av två saker: startdatumet `2023-05-26` (då PM2.5-serien började) och **senaste tillgängliga tidpunkt i SMHI:s kvalitetskontrollerade väderarkiv** (`corrected-archive`).

| Period | Regel | Exempel (körning 2026-10-23) |
|---|---|---|
| Träning | 2023-05-26 → dagen före valideringens start | 2023-05-26 – 2025-12-31 |
| Validering | De 6 senaste hela kalendermånaderna före den månad där `corrected-archive` slutar | 2026-01-01 – 2026-06-30 |
| Test | Från första tillgängliga timme i `latest-months` efter valideringsslut → nu minus 4 timmar | 2026-07-01 – 2026-10-23 (nu − 4 h) |

**Källor per period:** Träning och validering använder kvalitetskontrollerat arkiv (`corrected-archive`). Testdatan kommer från `latest-months` (ungefär de senaste fyra månaderna, okontrollerad).

**Viktigt om testdatan:** testperioden slutar alltid "nu minus 4 timmar", eftersom de allra senaste PM2.5- och vädervärdena kan saknas eller ännu inte vara uppdaterade. Eftersom `latest-months` rullar framåt och perioden räknas om vid varje körning hämtas testdatan vid varje pipeline-körning – den är alltså **inte** fryst. Filnamnen stämplas med perioden (t.ex. `test_merged_2026-07-01_2026-10-23_...csv`), så tidigare hämtningar finns kvar, men resultatet av en körning är bara exakt återkombart för den körningen. Körningar spårar sig själva med timestamp i `logs/datakontroll.csv` och `logs/jamforelse_champion.csv`.

## Pipelinen och datamapparna

`main.py` läser `config.toml` och kör flödet i `src/orchestrator.py`. **Obs:** hela pipelinen hoppas över om den vanliga championen tränats inom de senaste 7 dagarna (`champion_is_fresh` i `src/io.py`; gränsen `[model] antal_dagar_sedan` i `config.toml`).

När pipelinen körs:

1. **Testperioden beräknas** och testdata hämtas (`fetch_and_merge_test` i `src/data_pipeline.py`): PM2.5 och väder hämtas från `latest-months`.
2. **PM2.5** för träning/validering hämtas med `hamta_pm25` i `src/extracting_data.py`, en månad i taget (stora frågor mot API:et kan annars ta lång tid eller misslyckas). Datumsträngar tolkas i svensk tid och slutdatumet ingår. Dubletter som kan uppstå vid månadsskiften tas bort.
3. **Väder** hämtas med `vader_data`: för varje parameter hämtas hela `corrected-archive`, och perioden plockas sedan ut i koden.
4. **Sammanslagning** av PM2.5 och väder på tidsstämpel (outer join) → `data/merged/`.
5. **Bearbetning** (`build_processed_dataset` i `src/data_pipeline.py`): validering → features → målvariabel → borttag av rader med saknade värden → `data/processed/`. Sex filer byggs: train/val/test för både den vanliga och den förskjutna modellinjen. Antal rader och saknade värden loggas i `logs/datakontroll.csv`.

Alla filer skrivs med läget "skapa bara om filen saknas" (`generate_csv` i `src/io.py`), så existerande filer skrivs aldrig över och fungerar som cache: finns filen hämtas inte data igen från API:et.

| Mapp | Innehåll |
|---|---|
| `data/raw/` | Rådata per period och källa, som den hämtades från API:erna |
| `data/merged/` | PM2.5 och väder sammanslagna på tidsstämpel |
| `data/validated/` | Skapas av koden men skrivs inte längre; validerad data ingår i de processade filerna |
| `data/processed/` | Bearbetade dataset för modellträning och utvärdering, med validerad data, skapade features och målvariabel samt borttagna rader med saknade värden |

**Återskapa data:** radera innehållet i `data/raw/`, `data/merged/` och `data/processed/` och kör `python main.py` från projektets rot. Notera att `data/` ligger i `.gitignore` – datat mappas **inte** av git, och olika datorer kan därför ha olika lokala filer. Eftersom perioderna beräknas om dynamiskt kan en omhämtning också ge andra perioder (och därmed andra filnamn) än tidigare körningar.

## Validering

`validate_data` i `src/validate_process.py`:

1. gör om tidsstämplarna från text till riktig tid i svensk tidszon (`Europe/Stockholm`)
2. sorterar raderna i tidsordning
3. stoppar körningen om det finns dubbla tidsstämplar
4. lägger till tomma rader för timmar som saknas, så att det finns exakt en rad per timme
5. ersätter ogiltiga värden med saknade värden: negativ PM2.5, vindriktning utanför 0–360°, vindhastighet under 0, luftfuktighet utanför 0–100 % och nederbörd under 0
6. gör om vindriktningen 360° till 0° (samma vinkel för sin/cos)

Värden fylls aldrig i – varken genom interpolation eller medelvärden. De interpolationfunktioner som fanns tidigare är borttagna ur kodbasen.

## Saknade värden och features

Rader där någon feature eller själva målet saknas tas bort (`dropna`) **efter** att målvariabeln skapats, så att målet alltid ligger exakt sex timmar framåt (horisonten styrs av `[model] horisont` i `config.toml`).

- **Mål:** PM2.5-halten vid T + 6 timmar.
- **Features** (`[model.features]` i `config.toml`): `pm25`, `Lufttemperatur`, `vind_sin`, `vind_cos` (vindriktning som sin/cos; vindstilla ger 0/0), `Vindhastighet`, `Relativ luftfuktighet`, `Nederbördsmängd`, samt tidsfeatures för **måltiden**: `timme_sin`, `timme_cos`, `helg`, `helg_timme_sin` och `helg_timme_cos` (se `add_time_features` i `src/features.py`).
- **Två modellinjer:** Den *vanliga* använder observerat väder vid tidpunkten T. Den *förskjutna* använder i stället observerat väder vid T + 6 timmar. Vädervariablerna ersätts före sin/cos-omvandlingen, så att även vindriktningens features baseras på måltidens väder. Vid live-prediktion används SMHI:s väderprognos för T + 6 i stället för faktiska observationer (se `docs/evaluation.md`).

## Statistik för senaste körning (2026-10-23, ur `logs/datakontroll.csv`)

| Dataset | Rader efter validering | Saknade värden per kolumn | Borttagna rader |
|---|---|---|---|
| Träning | 22 825 | PM2.5 154, Lufttemperatur 536, vind 572, Vindhastighet 572, luftfuktighet 570, Nederbördsmängd 1 069, target 158 | 1 270 (5,6 %) → 21 555 kvar |
| Validering | 4 343 | PM2.5 3, vind 2, Nederbördsmängd 48, target 8 | 61 (1,4 %) → 4 282 kvar |
| Test | 2 741 | PM2.5 17, Nederbördsmängd 96, target 23 | 125 (4,6 %) → 2 616 kvar |

Siffrorna uppdateras vid varje pipeline-körning; aktuell statistik finns alltid i `logs/datakontroll.csv`.

## Kvalitetsproblem

- **Preliminär data i test och live:** `latest-months` är inte kvalitetskontrollerad; värden kan ändras eller underkännas i efterhand, vilket gör testresultat från olika körningar svåra att jämföra exakt.

- **Saknade vädervärden:** Samtliga vädervariabler saknas samtidigt under vissa perioder. Nederbördsmängd har därutöver flera separata luckor där övriga vädervariabler har registrerade värden.
- **Saknade PM2.5-värden:** PM2.5 har främst kortare och mer utspridda luckor, men även längre sammanhängande bortfall. Rader med saknade värden tas bort enligt avsnittet Saknade värden.


## Begränsningar

- **Skilda datakvaliteter:** träning och validering sker på kvalitetskontrollerat arkiv (`corrected-archive`), men test och live använder okontrollerade realtidsvärden (`latest-months`). En del av testfelet kan alltså bero på mätvärden som senare korrigeras, inte på modellen.
- **En station, gaturum:** Dalaplan är en trafikmiljö och är inte nödvändigtvis representativ för andra delar av Malmö.
- **Avstånd mellan stationerna:** väderdatan kommer från en station cirka 4 km från Dalaplan, och lokala vindförhållanden i ett gaturum kan skilja från dem vid Malmö A.
- **Kort historik:** PM2.5-serien börjar i maj 2023, så träningsdatan innehåller tre somrar och höstar men bara två vintrar och vårar.
- **Testdatan används i championvalet** och hämtas om vid varje körning – testresultat mellan olika körningar är därför inte helt jämförbara. Detta är ett medvetet beslut, se `docs/decisions.md`.
