# Predicting Air Quality

Prediktion av PM2.5-halten vid Dalaplan i Malmö sex timmar framåt med hjälp av historiska luftkvalitetsdata och meteorologiska data.

## Datakällor

- **Luftkvalitet:** Naturvårdsverkets REST-API för luftkvalitetsdata, tillhandahållet av SMHI som datavärd. Station: Malmö Dalaplan (gaturum), PM2.5-tidsserie 6247.
- **Väder:** SMHI:s öppna API för meteorologiska observationer. Station: Malmö A (id 52350), cirka 4 km från Dalaplan.

Data från SMHI används under licensen CC BY 4.0.

## Data

- `data/raw/` innehåller rådata som den hämtades från API:erna. Den versionshanteras så att alla arbetar med exakt samma data, eftersom realtidsdata kan korrigeras i efterhand.
- `data/processed/` innehåller rensad och sammanslagen data. Den versionshanteras inte och skapas med koden i `src/`.

### Tidsperioder

| Period | Från | Till |
|---|---|---|
| Träning | 2023-05-26 | 2025-12-31 |
| Validering | 2026-01-01 | 2026-04-30 |
| Test | 2026-05-01 | – |


**Viktigt:** Testdata från 2026-05-01 och framåt får inte hämtas eller committas under utvecklingen. Den används en gång, i slutet av projektet, för att utvärdera den slutliga modellen.

Alla perioder och stationer definieras i `src/config.py`.

## Kom igång

    git clone https://github.com/JakobWorkingHard/predicting_air_quality.git
    cd predicting_air_quality
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Arbetsflöde

- Ingen pushar direkt till `main`.
- Varje ändring görs i en egen branch.
- Ändringar slås ihop via pull request som godkänts av minst en annan gruppmedlem.