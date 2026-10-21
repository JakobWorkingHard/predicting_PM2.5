# Plan: Live-prediktioner som pipeline i `src/`

Lifta `notebooks/live_prediktioner.ipynb` till projektets `src/`-struktur.
Pipeline körs stegvis: varje steg motsvarar en funktion som kopieras in manuellt,
en i taget, med genomgång av funktionaliteten.

Referens (ändras inte): `notebooks/live_prediktioner.ipynb`

## Beslut (från planeringen)

- **Filstruktur:** Ny `src/live_pipeline.py` (live-orchestrator) + enskilda funktioner
  sprids i befintliga moduler där de passar.
- **Konfiguration:** Ny `[live]`-sektion i `config.toml`, fält i `ProjectConfig`.
- **Förskjuten champion:** Återanvänd `load_latest_champion(cfg.forskjuten_log, cfg.models_dir)`
  (ingen globbning av `forskjuten_*.joblib`).
- **Uppföljning:** `folj_uppa` blir ett separat steg i pipelinen.

## Flödet som ska byggas (från notebooken)

1. **Hämta** — punktprognos (SMHI metfcst), färsk PM2.5 (unik sökväg tvingar fram
   ny data), väderobservationer (latest-months).
2. **Ankarpunkt** — T_obs = senaste hela timme med komplett pm25 + alla väderparametrar.
3. **Vakter** — hoppa över om T_obs är äldre än max-ålder, eller redan predikterad (idempotens).
4. **Modellrader** — två rader per körning: *vanlig* (väderobservation vid T_obs) och
   *förskjuten* (väderprognos för T_obs + horisont). Sanity-regler + features.
5. **Prediktera** — vanlig champion via `hamta_champion_modell`, förskjuten via
   `load_latest_champion(cfg.forskjuten_log, ...)`.
6. **Logga** — en rad per linje i `prognoser/prediktioner_live.csv`.
7. **Uppföljning (separat steg)** — rättar loggade prediktioner mot verkliga mätningar,
   sammanställer MAE/Bias per linje + persistence-baseline.

## Befintliga funktioner som återanvänds

| Funktion | Fil |
|---|---|
| `hamta_pm25`, `hamta_test_vader` | `src/extracting_data.py` |
| `add_wind_features`, `add_time_features` | `src/features.py` |
| `hamta_champion_modell` | `src/io.py` |
| `load_latest_champion` | `src/champion.py` |
| `display_df` | `src/metrics.py` |
| `load_config` | `src/config.py` |

## Placering av ny kod

| Notebook-kod | Placering | Motivering |
|---|---|---|
| Konstanter (URL, prognosparametrar, mappar, max-ålder, loggsökväg) | `config.toml [live]` + `ProjectConfig` | Konsekvent med projektet |
| `hamta_prognos` | `src/extracting_data.py` | API-hämtning |
| `hamta_senaste_pm25`, `hamta_senaste_vaderobs` | `src/data_pipeline.py` | Omslag runt befintliga hämtare |
| `VADER_INTERVALL` + `sanity_kolla_vader` | `src/validate_process.py` | Speglar `replace_invalid_values` för en rad |
| `bestam_ankarpunkt` | `src/data_pipeline.py` | Kompletthet i pm25 + väder |
| `bygg_live_rader` | `src/features.py` | Bygger feature-rader |
| `las_forskjuten_champion` | ersätts av `load_latest_champion` | Loggbaserad, som orchestrator |
| `kor_live_prediktion` | `src/live_pipeline.py` (ny) | Live-orchestrator |
| `folj_uppa` | `src/live_pipeline.py` | Del av live-flödet |
| MAE/Bias-sammanställning ur `folj_uppa` | `src/metrics.py` | Ren metriktabell |
| Loggappend av prediktioner | `src/io.py` (liten hjälpare) | Samma mönster som `append_champion_log` |
| Entry point | `live.py` i projektroten | Speglar `main.py` |

## Anpassningar vid lyftet

- Funktioner tar `cfg` som parameter (notebookens globaler försvinner).
- `log.info(...)` i stället för `print(...)` (projektstil); `display_df` behålls för tabeller.
- Arkiveringen (rå-JSON + 24 h-CSV) ligger samlad i `hamta_prognos`, som i notebooken.

## Steg (en funktion per steg)

### Steg 1 — Konfiguration
`[live]` i `config.toml` + nya fält i `ProjectConfig`/`load_config`.

```toml
[live]
prognos_dir = "prognoser"
prediktioner_log = "prognoser/prediktioner_live.csv"
prognos_url = "https://opendata-download-metfcst.smhi.se/api/category/snow1g/version/1/geotype/point/lon/{LON}/lat/{LAT}/data.json"
timmar = 24            # prognossteg som sparas i trimmad CSV
max_alder_timmar = 6   # hoppa över om T_obs är äldre
idempotent = true

[live.prognos_parametrar]
"Lufttemperatur" = "air_temperature"
"Vindriktning" = "wind_from_direction"
"Vindhastighet" = "wind_speed"
"Relativ luftfuktighet" = "relative_humidity"
"Nederbördsmängd" = "precipitation_amount_mean"
```

### Steg 2 — `hamta_prognos` → `src/extracting_data.py`
Hämtar punktprognosen, arkiverar rå-JSON + 24 h-CSV i `prognos_dir`,
returnerar `(prognos_df, referenstid)`.

### Steg 3 — `hamta_senaste_pm25` → `src/data_pipeline.py`
Omslag runt `hamta_pm25` med timestampad sökväg i `prognoser/pm25/`.

### Steg 4 — `hamta_senaste_vaderobs` → `src/data_pipeline.py`
Omslag runt `hamta_test_vader` (latest-months, cacheas aldrig).

### Steg 5 — `sanity_kolla_vader` + `VADER_INTERVALL` → `src/validate_process.py`
Singelradsversion av `replace_invalid_values`. Vid steget: diskutera att låsa
intervallen mot `replace_invalid_values` så reglerna inte glider isär.

### Steg 6 — `bestam_ankarpunkt` → `src/data_pipeline.py`
T_obs = senaste hela timme med komplett pm25 + alla väderparametrar.

### Steg 7 — Förskjuten champion (inget nytt att kopiera)
Verifiera att `load_latest_champion(cfg.forskjuten_log, cfg.models_dir)` hittar
modellen och vilket `namn` som loggas (t.ex. "SVR (T+6)").

### Steg 8 — `bygg_live_rader` → `src/features.py`
En modellrad per linje med rätt väderslot, `add_wind_features` +
`add_time_features`, kolumner ordnade efter `cfg.features`.

### Steg 9 — `kor_live_prediktion(cfg)` → ny `src/live_pipeline.py`
Hämta → T_obs → vakter → modellrader → ladda championer → prediktera →
visa → logga via append-hjälpare i `src/io.py`.

### Steg 10 — Entry point `live.py` i projektroten
Speglar `main.py`: hitta projektrot, `load_config`, köra `kor_live_prediktion`,
flagga (t.ex. `--uppföljning`) för steg 11.

### Steg 11 — `folj_uppa` → `src/live_pipeline.py` + `src/metrics.py`
- `metrics.py`: ny funktion som tar utvärderade loggrader och returnerar
  MAE/Bias per linje + persistence-baseline.
- `live_pipeline.py`: `folj_uppa(cfg)` hämtar verkliga värden, matchar mot
  `mål_tid`, anropar sammanställningen, visar med `display_df`.

## Att minnas under arbetet

- Notebooken lämnas omodifierad som referens.
- `load_config` gör nätverksanrop (`hamta_senaste_arkivtid`) vid varje laddning —
  oförändrat beteende, men värt att veta vid test av live-körningen.
- `orchestrator.py`-kommentaren: vid live-prediktion ska väderslotten fyllas med
  väderPROGNOS för T+6 — exakt det notebooken gör.
- Manuell testning per steg: kör funktionen isolerat (t.ex. via `python -c` eller
  kort skript) innan nästa steg påbörjas.
