import json
import time
import pandas as pd
import requests
import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from src.logger import setup_logger
from src.config import ProjectConfig
from src.io import generate_csv

log = setup_logger()

def hamta_med_retry(url, **kwargs):
    for forsok in range(1, 4):
        try:
            svar = requests.get(
                url,
                timeout=(20, 120),
                **kwargs,
            )
            svar.raise_for_status()
            return svar

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as e:
            if forsok == 3:
                raise

            vantetid = 5 * forsok
            log.warning(
                "Nätverksfel, försök %s/3: %s. Väntar %s sekunder.",
                forsok,
                e,
                vantetid,
            )
            time.sleep(vantetid)


def till_svensk_tid(ms):
    tid = pd.to_datetime(ms, unit="ms", utc=True)
    if isinstance(tid, pd.Series):
        return tid.dt.tz_convert("Europe/Stockholm")
    return tid.tz_convert("Europe/Stockholm")


def hamta_pm25(TRAIN_START, TRAIN_SLUT, tidsserie_id, LUFT_API, csv_path):
    """
    Hämtar PM2.5 en månad i taget.

    Datumsträngar tolkas som hela kalenderdagar i svensk tid.
    Tidsstämplar används som exakta tidpunkter.

    Om csv_path redan finns returneras data från filen.
    """
    if os.path.exists(csv_path):
        print(f"Läser pm2.5 från befintlig fil: {csv_path}")
        return pd.read_csv(csv_path, index_col="tid", parse_dates=True)

    start_tid = pd.Timestamp(TRAIN_START)
    slut_tid = pd.Timestamp(TRAIN_SLUT)

    # Hantera starttiden
    if start_tid.tzinfo is None:
        start_tid = start_tid.tz_localize("Europe/Stockholm")
    else:
        start_tid = start_tid.tz_convert("Europe/Stockholm")

    # Datumsträngar innebär hela kalenderdagar.
    # Tidsstämplar innebär exakta tidpunkter.
    if slut_tid.tzinfo is None:
        slut_tid = (
            slut_tid.tz_localize("Europe/Stockholm")
            + pd.Timedelta(days=1)
            - pd.Timedelta(seconds=1)
        )
    else:
        slut_tid = slut_tid.tz_convert("Europe/Stockholm")

    if start_tid > slut_tid:
        raise ValueError(
            f"Starttiden {start_tid} ligger efter sluttiden {slut_tid}."
        )

    

    alla_varden = []



    try:
        for manad in pd.period_range(start_tid.tz_localize(None), slut_tid.tz_localize(None), freq="M"):
            fran = max(start_tid, manad.start_time.tz_localize("Europe/Stockholm"))
            till = min(slut_tid, manad.end_time.tz_localize("Europe/Stockholm"))
            timespan = (f"{fran.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}/"
                        f"{till.tz_convert('UTC'):%Y-%m-%dT%H:%M:%SZ}")

            print(f"Hämtar {manad}...", flush=True)
            svar = svar = hamta_med_retry(
                f"{LUFT_API}/timeseries/{tidsserie_id}/getData",
                params={"timespan": timespan},
                )
            svar.raise_for_status()
            alla_varden.extend(svar.json()["values"])
            time.sleep(0.5)
    except requests.exceptions.RequestException as e:
        print(f"Nätverksfel vid hämtning av pm2.5: {e}")
        raise
    except Exception as e:
        print(f"Oväntat fel vid hämtning av pm2.5: {e}")
        raise

    df = pd.DataFrame(alla_varden)
    df["tid"] = till_svensk_tid(df["timestamp"])

    # Samma mätning kan komma med två gånger vid månadsskiften,
    # eftersom vi hämtar en månad i taget. Ta bort exakta kopior.
    df = df.drop_duplicates(subset=["timestamp", "value"])

    # Behåll endast observationer inom det begärda tidsintervallet
    df = df[(df["tid"] >= start_tid) & (df["tid"] <= slut_tid)]

    return df.set_index("tid")[["value"]].rename(columns={"value": "pm25"})


def hamta_vader_arkiv( parameter,station_id,VADER_API,csv_path=None,period="corrected-archive"):
    """
    Hämtar väderdata från SMHI.

    Parametrar
    ----------
    parameter : int
        SMHI:s parameter-ID.
    station_id : int
        SMHI:s stations-ID.
    VADER_API : str
        Basadress till SMHI:s API.
    csv_path : Path eller str, valfri
        Sökväg där hämtad data ska sparas.
        Om None sparas ingen fil.
    period : str
        Tidsperiod som ska hämtas:
        'corrected-archive', 'latest-months',
        'latest-day' eller 'latest-hour'.

    Returns
    -------
    pd.DataFrame
        DataFrame med tidsindex och kolumnerna
        'varde' och 'kvalitet'.
    """

    # Använd befintlig fil endast för corrected-archive
    if (
        period == "corrected-archive"
        and csv_path is not None
        and os.path.exists(csv_path)
    ):
        print(f"Läser väderdata från befintlig fil: {csv_path}")

        return pd.read_csv(
            csv_path,
            index_col="tid",
            parse_dates=True,
        )

    # Bygg URL till SMHI:s API
    url = (
        f"{VADER_API}/parameter/{parameter}"
        f"/station/{station_id}/period/{period}/data.csv"
    )

    try:
        svar = hamta_med_retry(url)

    except requests.exceptions.RequestException as e:
        print(
            f"Nätverksfel vid hämtning av väderdata "
            f"(parameter {parameter}): {e}"
        )
        raise

    try:
        # Hitta början av CSV-tabellen
        rader = svar.text.splitlines()

        startrad = next(
            i for i, rad in enumerate(rader)
            if rad.startswith("Datum")
        )

        # Läs in CSV-data
        df = pd.read_csv(
            io.StringIO("\n".join(rader[startrad:])),
            sep=";",
            usecols=[0, 1, 2, 3],
        )

        df.columns = [
            "datum",
            "tid_utc",
            "varde",
            "kvalitet",
        ]

        # Konvertera tidsstämplar till svensk tid
        df["tid"] = (
            pd.to_datetime(
                df["datum"] + " " + df["tid_utc"],
                utc=True,
            )
            .dt.tz_convert("Europe/Stockholm")
        )

        # Skapa DataFrame med tid som index
        df = df.set_index("tid")[["varde", "kvalitet"]]

        # Spara endast om en sökväg har angetts
        if csv_path is not None:
            df.to_csv(csv_path)

        return df

    except StopIteration:
        print(
            f"Kunde inte hitta tabellstart ('Datum') "
            f"i svaret för parameter {parameter}."
        )
        raise

    except Exception as e:
        print(
            f"Fel vid tolkning av väderdata "
            f"för parameter {parameter}: {e}"
        )
        raise


def hamta_senaste_arkivtid(
    parametrar: dict,
    station_id: int,
    VADER_API: str,
) -> pd.Timestamp:
    """Hämtar den senaste tillgängliga tidpunkten i corrected-archive."""

    senaste_tider = []

    for namn, nummer in parametrar.items():
        data = hamta_vader_arkiv(
            parameter=nummer,
            station_id=station_id,
            VADER_API=VADER_API,
            csv_path=None,
            period="corrected-archive",
        )

        if not data.empty:
            senaste_tider.append(data.index.max())
            print(f"{namn}: sista mätningen från corrected archive {data.index.max()}")

    if not senaste_tider:
        raise ValueError(
            "Hittade inga mätningar i corrected-archive."
        )

    return min(senaste_tider)








def vader_data(parametrar, starttid, sluttid, station_id, VADER_API, csv_path, period="corrected-archive"):
    """Skapar dictionary av väderdata inhämtat via api med våra parametrar.
    Om csv_path redan finns returneras df direkt från filen."""
    if os.path.exists(csv_path):
        print(f"Läser väderdata från befintlig fil: {csv_path}")
        return pd.read_csv(csv_path, index_col="tid", parse_dates=True)

    vader_delar = {}
    for namn, nummer in parametrar.items():
        print(f"Hämtar {namn}...", flush=True)
        try:
            data = hamta_vader_arkiv(nummer, station_id, VADER_API, csv_path=None, period=period)
            vader_delar[namn] = data.loc[starttid:sluttid, "varde"]
        except Exception as e:
            print(f"  Fel för {namn}: {e}")
    return pd.DataFrame(vader_delar)



def hamta_testperiod(
    station_id: int,
    VADER_API: str,
    validering_slut: str,
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Beräknar testperioden dynamiskt.

    Teststart:
        Första tillgängliga tidpunkt i latest-months efter
        valideringsperiodens slut.

    Testslut:
        Aktuell svensk tid minus fyra timmar, avrundad nedåt
        till närmaste hela timme.
    """

    url = (
        f"{VADER_API}/parameter/1/station/{station_id}"
        "/period/latest-months/data.csv"
    )

    svar = hamta_med_retry(url)

    rader = svar.text.splitlines()
    startrad = next(
        i for i, rad in enumerate(rader)
        if rad.startswith("Datum")
    )

    df = pd.read_csv(
        io.StringIO("\n".join(rader[startrad:])),
        sep=";",
        usecols=[0, 1, 2, 3],
    )

    df.columns = ["datum", "tid_utc", "varde", "kvalitet"]

    if df.empty:
        raise ValueError("SMHI returnerade ingen data för latest-months.")

    tider = pd.to_datetime(
        df["datum"] + " " + df["tid_utc"],
        utc=True,
    ).dt.tz_convert("Europe/Stockholm")

    # Valideringen slutar vid dagens slut i svensk tid.
    validering_slut_tid = pd.Timestamp(
        validering_slut,
        tz="Europe/Stockholm",
    ) + pd.Timedelta(days=1)

    # Testen börjar vid första tillgängliga mätningen efter valideringen.
    testtider = tider[tider >= validering_slut_tid]

    if testtider.empty:
        raise ValueError(
            "Hittade inga testmätningar efter valideringsperiodens slut "
            f"({validering_slut}). SMHI:s latest-months kan sakna "
            "data för den önskade testperioden."
        )

    test_start = testtider.min()

    # Aktuell svensk tid minus fyra timmar.
    nu = pd.Timestamp.now(tz="Europe/Stockholm")
    test_slut = (nu - pd.Timedelta(hours=4)).floor("h")

    if test_start > test_slut:
        raise ValueError(
            f"Ogiltig testperiod: start {test_start}, slut {test_slut}."
        )

    return test_start, test_slut



def hamta_test_vader(
    parametrar: dict,
    test_start: pd.Timestamp,
    test_slut: pd.Timestamp,
    station_id: int,
    VADER_API: str,
) -> pd.DataFrame:
    """
    Hämtar väderdata för den dynamiska testperioden.
    Använder SMHI:s latest-months och begränsar resultatet
    till test_start och test_slut.
    """

    vader_delar = {}

    for namn, nummer in parametrar.items():
        print(f"Hämtar testdata för {namn}...", flush=True)

        data = hamta_vader_arkiv(
            parameter=nummer,
            station_id=station_id,
            VADER_API=VADER_API,
            csv_path=None,
            period="latest-months",
        )

        vader_delar[namn] = data.loc[test_start:test_slut, "varde"]

    return pd.DataFrame(vader_delar)



# ANVÄNDS I PREDICT PIPELINE

# 1. Hämta väderprognos
def hamta_prognos(cfg: ProjectConfig) -> tuple[pd.DataFrame, pd.Timestamp]:
    """
    Hämtar SMHIs punktprognos och arkiverar rå-JSON + trimmad CSV i prognos_dir.

    Returnerar hela prognos_df (svenska kolumnnamn enligt
    cfg.prognos_parametrar, tz-medvetet index i svensk tid) och
    prognosens referenstid (UTC).

    API-svaret (snow1g punktprognos) ser ut ungefär så här (förkortat):

        {
          "createdTime": "2026-10-21T13:44:23Z",
          "referenceTime": "2026-10-21T13:30:00Z",
          "geometry": { "type": "Point", "coordinates": [...] },
          "timeSeries": [
            { "time": "2026-10-21T14:00:00Z",
              "data": { "air_temperature": 11.5,
                        "wind_from_direction": 123,
                        "wind_speed": 3.4,
                        "relative_humidity": 95,
                        "precipitation_amount_mean": 0.1,
                        ... ca 20 parametrar till } },
            ... ett timsteg per element, totalt ca 83 steg
          ]
        }
    """
    log.info("Hämtar SMHI-punktprognos...")
    svar = requests.get(cfg.prognos_url, timeout=60)
    svar.raise_for_status()
    prognos_json = svar.json()

    referenstid = pd.to_datetime(prognos_json["referenceTime"], utc=True)

    # Arkiv: rå-JSON skrivs endast om den saknas
    # (samma referenstid = samma prognos, ingen ny fil behövs)
    cfg.prognos_dir.mkdir(parents=True, exist_ok=True)
    namn = f"prognos_{referenstid:%Y-%m-%dT%H%M}_utc"
    ra_sokvag = cfg.prognos_dir / (namn + ".json")
    if not ra_sokvag.is_file():
        with open(ra_sokvag, "w", encoding="utf-8") as f:
            json.dump(prognos_json, f, ensure_ascii=False)

    # Omformning: nästlad JSON -> rader.
    # Loopen har ett enda jobb: plocka ut tidssträngen (rå) +
    # våra parametervärden (mappade och omdöpta, saknade -> None).
    rader = []
    for steg in prognos_json["timeSeries"]:
        rad = {"tid": steg["time"]}
        for kolumn, nyckel in cfg.prognos_parametrar.items():
            rad[kolumn] = steg["data"].get(nyckel)
        rader.append(rad)

    # Tidskonvertering: en gång, vektoriserad på kolumnnivå
    prognos_df = pd.DataFrame(rader)
    prognos_df["tid"] = pd.to_datetime(
        prognos_df["tid"], utc=True
    ).dt.tz_convert("Europe/Stockholm")
    prognos_df = prognos_df.set_index("tid").sort_index()

    # Arkiv: trimmad CSV, de första prognos_arkiv_timmar stegen
    # från referenstiden och framåt (ARKIV, EJ PREDIKTION)
    prognos_df.head(cfg.prognos_arkiv_timmar).to_csv(
        cfg.prognos_dir / f"{namn}_{cfg.prognos_arkiv_timmar}h.csv"
    )

    log.info(
        "Prognos hämtad: referenstid %s, %d steg fram till %s.",
        referenstid,
        len(prognos_df),
        prognos_df.index.max(),
    )
    return prognos_df, referenstid


# 2. Hämta färsk pm2.5 data
def hamta_senaste_pm25(cfg, timmar_bak: int = 48):
    """
    Färska PM2.5-mätningar för live-prediktion.

    Hämtar de senaste `timmar_bak` timmarna fram till nu och sparar
    hämtningen i pm25-arkivet under prognosmappen. Den timestampade
    sökvägen är unik per körning, vilket tvingar fram ny data —
    hamta_pm25 cachar annars på befintliga sökvägar.

    Notera att hamta_pm25 aldrig skriver csv_path själv (i huvudpipelinen
    är det den anropande koden som sparar) — därför sparas hämtningen här
    via generate_csv så att pm25-arkivet faktiskt fylls.
    """
    nu = pd.Timestamp.now(tz="Europe/Stockholm")
    csv_path = cfg.prognos_dir / "pm25" / f"pm25_{nu:%Y%m%dT%H%M%S}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    pm25_df = hamta_pm25(
        nu - pd.Timedelta(hours=timmar_bak),
        nu,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        str(csv_path),
    )

    generate_csv(pm25_df, csv_path)

    log.info(
        "Senaste PM2.5 hämtad: %d rader, senaste %d timmarna.",
        len(pm25_df),
        timmar_bak,
    )

    return pm25_df



# 3. Hämta färsk väderdata
def hamta_senaste_vaderobs(cfg, timmar_bak: int = 48) -> pd.DataFrame:
    """
    Färska väderobservationer för live-prediktion (latest-months).

    Hämtar de senaste `timmar_bak` timmarna fram till och med nu.
    cachar aldrig (hamta_test_vader går alltid ut mot API:et), så här
    behövs ingen timestampad sökväg — till skillnad från hamta_senaste_pm25.

    Viktigt: slut är `nu`, INTE nu minus 4 h. Den 4-timmarsgapet i
    hamta_testperiod gäller bara testdatan. Publikationslagget löser
    sig självt senare i flödet: bestam_ankarpunkt väljer ändå bara
    den senaste hela timme med komplett data, och vakten
    max_alder_timmar skyddar mot för gammal data.
    """
    nu = pd.Timestamp.now(tz="Europe/Stockholm")

    vaderobs_df = hamta_test_vader(
        parametrar=cfg.vader_parametrar,
        test_start=nu - pd.Timedelta(hours=timmar_bak),
        test_slut=nu,
        station_id=cfg.vaderstation_id,
        VADER_API=cfg.vader_api,
    )

    # Nyttjar att parametrarna delar heltimmesindex: en rad per timme
    log.info(
        "Senaste väderobservationer hämtade: %d timmar, %d parametrar.",
        len(vaderobs_df),
        vaderobs_df.shape[1],
    )

    return vaderobs_df