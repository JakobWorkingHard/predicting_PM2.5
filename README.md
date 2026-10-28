# Predicting Air Quality

Prediktion av PM2.5-halten vid Dalaplan i Malmö sex timmar framåt, med historiska luftkvalitetsdata och meteorologiska data från SMHI.

## Problem och syfte

Halten av fina partiklar (PM2.5) i stadsluft varierar kraftigt från timme till timme, beroende på trafik, väder och vind. Projektet förutsäger PM2.5-halten vid mätstationen Malmö Dalaplan **6 timmar framåt** utifrån den senaste PM2.5-mätningen, väderdata och tidpunkt.

**Ingår:**
- Automatisk hämtning av luftkvalitets- och väderdata från SMHI:s API:er
- Validering, rensning och feature engineering
- Träning och jämförelse av flera modeller mot en persistence-baseline
- Två modellinjer:
  - **vanlig:** väderobservationer vid prediktionstillfället
  - **förskjuten:** väder vid måltiden, som i drift hämtas från SMHI:s väderprognos
- Automatiskt val och sparande av en championmodell per modellinje
- Live-prediktion baserad på nuvarande championmodell med SMHI:s senaste data och uppföljning av prediktionerna mot faktiska mätningar

**Ingår inte:**
- Andra luftföroreningar (t.ex. PM10 eller NO₂) eller andra mätstationer
- Andra prognoshorisonter än 6 timmar
- Varningstjänst, app eller hälsoråd

## Målgrupp

Lösningen riktar sig till dem som vill veta hur luftkvaliteten vid Dalaplan sannolikt blir de närmaste timmarna, till exempel personer med astma eller andra luftvägsbesvär som planerar utomhusaktiviteter, eller kommunala miljöhandläggare som vill se en trend. I sin nuvarande form är projektet ett kursprojekt och en demonstration av en ML-pipeline med kontinuerlig träning, inte en färdig tjänst.

## Gruppmedlemmar

| Namn | Ansvarsområden |
|---|---|
| Jakob Ohlsén S. | live prediction |
| Daniel Rangmyr |  Datahantering, dynamisk hantering av tidsperioder, logging. |
| Victoria Elmander | Datakvalitet, granskning av metoder och analys av resultat  |
| Elisabeth Weise | championlogik och pipelinestruktur  |

## Datakälla

- **Luftkvalitet:** Naturvårdsverkets REST-API för luftkvalitetsdata med SMHI som datavärd. Station Malmö Dalaplan (gaturum), PM2.5-tidsserie 6247, aktiv sedan 2023-05-26.
- **Väderobservationer:** SMHI:s öppna API för meteorologiska observationer, station Malmö A (id 52350), cirka 4 km från Dalaplan. 
- **Väderprognoser:** SMHI:s öppna API för punktprognoser, hämtade för Dalaplans koordinater (lat 55.584747, lon 13.006230). Används bara i live-läget.

Mer om datan, perioderna och hur de beräknas finns i [docs/data.md](docs/data.md).

## Projektstruktur

```
predicting_air_quality/
├── data/            # Data i olika steg: raw (från API:erna), merged, validated och processed
├── docs/            # Dokumentation
│   ├── data.md          # Datakällor, perioder och datakvalitet
│   ├── decisions.md     # Beslut som gruppen har fattat och varför
│   └── evaluation.md    # Utvärdering av modellerna
├── logs/            # Loggar: championer, datakontroller, jämförelser och projektlogg
├── models/          # Sparade championmodeller (.joblib) med metadata (.json)
├── notebooks/       # Notebooks för utforskning och analys
├── prognoser/       # Live-prediktioner: rå väderprognos (JSON + 24h-CSV) per körning,
│                    # PM2.5-mätningar (pm25/) och prediktioner_live.csv för uppföljning
├── src/             # Projektets källkod
├── tests/           # Tester (pytest)
├── config.toml      # Gemensamma inställningar: sökvägar, API:er, stationer, horisont och urvalsmått
├── main.py          # Startar hela pipelinen: datahämtning, träning och championval
├── live.py          # Live-prediktion och uppföljning
└── requirements.txt # Python-beroenden
```

## Installation

**Python-version:** 3.13.7 (se `.python-version`)

```bash
git clone https://github.com/JakobWorkingHard/predicting_air_quality.git
cd predicting_air_quality
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

På macOS behöver LightGBM och XGBoost biblioteket `libomp`:

```bash
brew install libomp
```

**Miljövariabler:** Inga. SMHI:s API:er är öppna och kräver ingen API-nyckel.

## Hur projektet körs

### 1. Hela pipelinen: från data till championmodell

```bash
python main.py
```

Pipelinen gör följande:

1. **Beräknar perioderna dynamiskt.** Träningen börjar alltid 2023-05-26. Valideringen är de 6 hela månaderna före den månad då SMHI:s kvalitetskontrollerade väderarkiv slutar, och träningen slutar dagen före valideringen. Testperioden börjar efter valideringen och går fram till nu minus 4 timmar.
2. **Hämtar PM2.5- och väderdata** för träning, validering och test och sammanfogar dem. Rådata som redan finns i `data/raw/` läses från fil i stället för att hämtas igen.
3. **Validerar och bearbetar datan** (felaktiga värden, vindkomponenter och tidsfeatures) och loggar en datakontroll i `logs/datakontroll.csv`.
4. **Tränar modellerna** för båda modellinjerna, om den senaste championen är äldre än gränsen i `config.toml`.
5. **Väljer dagens bästa kandidat** på valideringsdatan (lägst Validation MAE).
6. **Låter kandidaten tävla mot den tidigare championen** på testdatan (högst R²). Vinnaren sparas i `models/` och loggas i `logs/champion_vanlig.csv` eller `logs/champion_forskjuten.csv`.
7. **Jämför de två modellinjerna** och baseline på testdatan och loggar resultatet i `logs/jamforelse_champion.csv`.

Bearbetade filer i `data/processed/` skrivs aldrig över. Ta bort mappen om datan ska byggas om från början.

### 2. Live-prediktion (demo)

```bash
python live.py
```

Hämtar SMHI:s senaste PM2.5-mätning, väderobservation och väderprognos, och predikterar PM2.5 6 timmar framåt med båda championmodellerna. Prediktionerna visas i terminalen och loggas.

### 3. Uppföljning av live-prediktionerna

```bash
python live.py --uppföljning
```

Jämför loggade prediktioner med de PM2.5-värden som faktiskt uppmättes, och visar MAE, RMSE, R² och Bias per modellinje och för baseline.

### 4. Tester

```bash
pytest
```

## Modeller och metoder

- **Persistence Baseline:** antar att PM2.5 om 6 timmar är samma som nu. Alla modeller måste slå den för att vara meningsfulla.
- **Linear Regression:** linjärt samband mellan features och PM2.5, enkel och lätt att tolka.
- **Ridge Regression:** linjär regression med regularisering, som minskar risken för överanpassning.
- **Random Forest:** många beslutsträd vars prediktioner medelvärdesbildas, fångar icke-linjära samband.
- **HistGradientBoosting:** scikit-learns snabba gradient boosting, där träden byggs i följd och rättar varandras fel.
- **SVR:** Support Vector Regression, anpassar en funktion som tillåter en viss felmarginal och är robust mot enstaka avvikande värden.
- **LightGBM:** effektiv gradient boosting som bygger träden blad för blad.
- **XGBoost:** gradient boosting med inbyggd regularisering.

**Championval:** dagens bästa kandidat väljs på valideringsdatan med Validation MAE. Den tävlar sedan mot den tidigare championen på testdatan med R². Vid lika resultat behålls den tidigare championen. Att testdatan används i championvalet är ett medvetet beslut, se [docs/decisions.md](docs/decisions.md).

## Viktigaste resultat

Båda championmodellerna (SVR) presterar bättre än persistence-baseline med cirka 11–12 % lägre MAE på testdatan, motsvarande omkring 0,2 µg/m³ lägre genomsnittligt prognosfel. Den förskjutna modellen (T+6) presterar marginellt bäst, men skillnaden är liten. Modellerna underskattar höga PM2.5-halter, så resultaten stödjer användning för generella prognoser men inte som varningssystem. Siffrorna avser pipeline-körningen 2026-10-23.

| Modell | MAE | RMSE | R² | Bias |
|---|---|---|---|---|
| Persistence-baseline | 1,741 | 2,628 | 0,414 | −0,004 |
| SVR (vanlig) | 1,545 | 2,265 | 0,565 | 0,056 |
| **SVR (förskjuten, T+6)** | **1,536** | **2,231** | **0,578** | 0,103 |

Mer om utvärderingen finns i [docs/evaluation.md](docs/evaluation.md).

## Begränsningar

- **En station och en horisont.** Modellerna gäller bara Malmö Dalaplan och 6 timmar framåt.
- **Avstånd mellan stationerna.** Väderdatan kommer från Malmö A, cirka 4 km från Dalaplan, eftersom ingen närmare station mäter det vi behöver.
- **Höga halter underskattas.** Modellerna har negativ bias för timmar med höga PM2.5-halter, alltså just de timmar som är viktigast för känsliga personer.
- **Den förskjutna modellen tränas med "perfekt" väder.** Under träningen används uppmätt väder vid måltiden. I drift används SMHI:s prognos, som har egna fel, så resultaten blir sannolikt sämre i live-läget än i utvärderingen.
- **Testdatan används i championvalet.** Det gör testresultaten något för optimistiska.
- **Olika årstider.** Validerings- och testperioderna täcker olika delar av året, och PM2.5 varierar med årstiden.
- **Realtidsdata är inte kvalitetskontrollerad.** Live-datan och testdatan kan korrigeras av SMHI i efterhand.
- **Championerna är lokala.** Modeller och loggar sparas per dator, så olika gruppmedlemmar kan ha olika championer.

**Lösningen bör inte användas** som underlag för hälsobeslut eller varningar, för andra platser än Dalaplan eller för andra horisonter än 6 timmar.

## Användning av generativ AI

Vi har använt generativ AI (bland annat Claude från Anthropic) som stöd i arbetet, ungefär som en extra diskussionspartner. AI har inte skrivit projektet åt oss. Vi har använt det till att:

- **Diskutera lösningar:** jämföra olika sätt att lösa ett problem, till exempel hur championmodellen ska väljas, hur tränings-, validerings- och testperioder kan beräknas dynamiskt och hur dataläckage kan undvikas.
- **Granska kod:** låta AI läsa igenom vår egen och varandras kod för att hitta buggar, inkonsekvenser och kommentarer som inte längre stämmer.
- **Strukturera kod:** få förslag på hur långa funktioner och filer kan delas upp, hur dubblerad logik kan samlas på ett ställe och hur funktioner kan namnges och dokumenteras.
- **Förklara:** reda ut begrepp, felmeddelanden och git-arbetsflöden.

### Så har vi granskat resultatet

- Alla beslut om modeller, data och metoder har fattats av gruppen. 
- Ändringar har testats lokalt innan de pushats.
- Alla ändringar har gått via pull requests som granskats av minst en annan gruppmedlem.
- Vi har inte delat API-nycklar, lösenord eller personuppgifter.

## Licens och användningsvillkor

- **Kod:** [MIT-licensen](LICENSE) – fullständig licenstext finns i filen `LICENSE`.
- **Data:**
  * **SMHI:** Används under licensen [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
  * **Naturvårdsverket (luftkvalitet):** Används under licensen [CC0 1.0 Universal (Public Domain Dedication)](https://creativecommons.org/publicdomain/zero/1.0/).

## Arbetsflöde

- Ingen pushar direkt till `main`.
- Varje ändring görs i en egen branch.
- Ändringar slås ihop via pull request som godkänts av minst en annan gruppmedlem.
