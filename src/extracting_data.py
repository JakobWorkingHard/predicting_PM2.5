import time
import pandas as pd
import requests
import io
import os
from datetime import datetime
from zoneinfo import ZoneInfo


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
            svar = requests.get(f"{LUFT_API}/timeseries/{tidsserie_id}/getData",
                                params={"timespan": timespan}, timeout=60)
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
        svar = requests.get(url, timeout=120)
        svar.raise_for_status()

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
            print(f"{namn}: senaste mätning {data.index.max()}")

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

    svar = requests.get(url, timeout=120)
    svar.raise_for_status()

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