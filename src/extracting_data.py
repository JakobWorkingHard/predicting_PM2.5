# Tillfällig import av variabler från config.py 
# innan vi skapar en config.toml
TRAIN_START = "2023-05-26"  # när PM2.5-tidsserien startade
TRAIN_SLUT = "2025-12-31"
VALIDERING_START = "2026-01-01"
VALIDERING_SLUT = "2026-04-30"
TEST_START = "2026-05-01"  # hämtas inte under utvecklingen
LUFT_API = "https://datavardluft.smhi.se/52North/api"
VADER_API = "https://opendata-download-metobs.smhi.se/api/version/1.0"
PM25_STATION = "Malmö Dalaplan"
PM25_TIDSSERIE_ID = 6247  # aktiv sedan 2023-05-26, täcker hela perioden
PM25_LAT = 55.584747
PM25_LON = 13.006230

# Väderstation
VADERSTATION = "Malmö A"
VADERSTATION_ID = 52350  # SMHI CORE-station, data sedan 1990
VADER_LAT = 55.5715
VADER_LON = 13.0708
import time
import pandas as pd
import requests
import io



def till_svensk_tid(ms):
    tid = pd.to_datetime(ms, unit="ms", utc=True)
    if isinstance(tid, pd.Series):
        return tid.dt.tz_convert("Europe/Stockholm")
    return tid.tz_convert("Europe/Stockholm")


def hamta_pm25(TRAIN_START, TRAIN_SLUT, tidsserie_id):
    """Hämtar PM2.5 en månad i taget. Datumen tolkas i svensk tid och slutdatumet ingår."""
    start_tid = pd.Timestamp(TRAIN_START, tz="Europe/Stockholm")
    slut_tid = pd.Timestamp(TRAIN_SLUT, tz="Europe/Stockholm") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

    alla_varden = []
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

    df = pd.DataFrame(alla_varden)
    df["tid"] = till_svensk_tid(df["timestamp"])
    return df.set_index("tid")[["value"]].rename(columns={"value": "pm25"})



def hamta_vader_arkiv(parameter, station_id, VADER_API):
    """Hämtar kvalitetskontrollerad arkivdata från SMHI för en parameter."""
    url = f"{VADER_API}/parameter/{parameter}/station/{station_id}/period/corrected-archive/data.csv"
    text = requests.get(url, timeout=120).text

    # Hoppa över beskrivningen överst, tabellen börjar på raden som startar med "Datum"
    rader = text.splitlines()
    startrad = next(i for i, rad in enumerate(rader) if rad.startswith("Datum"))
    df = pd.read_csv(io.StringIO("\n".join(rader[startrad:])), sep=";", usecols=[0, 1, 2, 3])
    df.columns = ["datum", "tid_utc", "varde", "kvalitet"]

    df["tid"] = pd.to_datetime(df["datum"] + " " + df["tid_utc"], utc=True).dt.tz_convert("Europe/Stockholm")
    return df.set_index("tid")[["varde", "kvalitet"]]


def vader_data(parametrar: dict, starttid, sluttid, station_id, VADER_API):
    "Skapar csv fil med vår hämtade väderdata."

    vader_delar = {}
    for namn, nummer in parametrar.items():
        print(f"Hämtar {namn}...", flush=True)
        try:
            data = hamta_vader_arkiv(nummer, station_id, VADER_API)
            vader_delar[namn] = data.loc[starttid:sluttid, "varde"]
        except Exception as e:
            print(f"  Fel för {namn}: {e}")
    return vader_delar



# Vi ska flytta parametrar till vår config.toml 
# så även detta är bara tillfälligt
parametrar = {
    "Lufttemperatur" : 1,
    "Vindriktning": 3,
    "Vindhastighet": 4,
    "Relativ luftfuktighet": 6,
    "Nederbördsmängd": 7
}



vader_2023 = pd.DataFrame(vader_data(parametrar, TRAIN_START, TRAIN_SLUT, VADERSTATION_ID, VADER_API))
vader_2023.to_csv("data/raw/vader_malmo_a_2023.csv")
print(vader_2023.describe())
vader_2023.head(50)



# Tillfällig exekutering (säger man så? Antar det)
# Detta flyttas till orkestreraren samt io.py senare
pm25_2023 = hamta_pm25(TRAIN_START, TRAIN_SLUT, PM25_TIDSSERIE_ID)
pm25_2023.to_csv("data/raw/pm25_dalaplan_2023.csv")
print(f"{len(pm25_2023)} rader")