import time
import pandas as pd
import requests
import io
import os



def till_svensk_tid(ms):
    tid = pd.to_datetime(ms, unit="ms", utc=True)
    if isinstance(tid, pd.Series):
        return tid.dt.tz_convert("Europe/Stockholm")
    return tid.tz_convert("Europe/Stockholm")


def hamta_pm25(TRAIN_START, TRAIN_SLUT, tidsserie_id, LUFT_API, csv_path):
    """Hämtar PM2.5 en månad i taget. Datumen tolkas i svensk tid och slutdatumet ingår.
    Om csv_path redan finns returneras df direkt från filen."""
    if os.path.exists(csv_path):
        print(f"Läser pm2.5 från befintlig fil: {csv_path}")
        return pd.read_csv(csv_path, index_col="tid", parse_dates=True)

    start_tid = pd.Timestamp(TRAIN_START, tz="Europe/Stockholm")
    slut_tid = pd.Timestamp(TRAIN_SLUT, tz="Europe/Stockholm") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)

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
    return df.set_index("tid")[["value"]].rename(columns={"value": "pm25"})


def hamta_vader_arkiv(parameter, station_id, VADER_API, csv_path, period="corrected-archive"):
    """
    Hämtar väderdata från SMHI.
    
    Parametrar
    ----------
    period : str
        Vilken tidsperiod som ska hämtas. Giltiga val:
        'corrected-archive', 'latest-months', 'latest-day', 'latest-hour'
    """
    
    # Använd bara den sparade filen om vi ber om det fasta arkivet
    # (Vill vi ha "latest-day" vill vi ju faktiskt hämta den senaste datan varje gång)
    if period == "corrected-archive" and os.path.exists(csv_path):
        print(f"Läser väderdata från befintlig fil: {csv_path}")
        return pd.read_csv(csv_path, index_col="tid", parse_dates=True)

    # Använd variabeln {period} i URL 
    url = f"{VADER_API}/parameter/{parameter}/station/{station_id}/period/{period}/data.csv"
    
    try:
        text = requests.get(url, timeout=120).text
    except requests.exceptions.RequestException as e:
        print(f"Nätverksfel vid hämtning av väderdata (parameter {parameter}): {e}")
        raise
    except Exception as e:
        print(f"Oväntat fel vid hämtning av väderdata: {e}")
        raise

    try:
        # Hoppa över beskrivningen överst, tabellen börjar på raden som startar med "Datum"
        rader = text.splitlines()
        startrad = next(i for i, rad in enumerate(rader) if rad.startswith("Datum"))
        df = pd.read_csv(io.StringIO("\n".join(rader[startrad:])), sep=";", usecols=[0, 1, 2, 3])
        df.columns = ["datum", "tid_utc", "varde", "kvalitet"]

        df["tid"] = pd.to_datetime(df["datum"] + " " + df["tid_utc"], utc=True).dt.tz_convert("Europe/Stockholm")
        df = df.set_index("tid")[["varde", "kvalitet"]]
        
        # Spara den nedladdade datan till csv_path om du vill spara även ny data
        df.to_csv(csv_path)
        
        return df
        
    except StopIteration:
        print(f"Kunde inte hitta tabellstart ('Datum') i svaret för parameter {parameter}")
        raise
    except Exception as e:
        print(f"Fel vid tolkning av väderdata för parameter {parameter}: {e}")
        raise



def vader_data(parametrar, starttid, sluttid, station_id, VADER_API, csv_path):
    """Skapar dictionary av väderdata inhämtat via api med våra parametrar.
    Om csv_path redan finns returneras df direkt från filen."""
    if os.path.exists(csv_path):
        print(f"Läser väderdata från befintlig fil: {csv_path}")
        return pd.read_csv(csv_path, index_col="tid", parse_dates=True)

    vader_delar = {}
    for namn, nummer in parametrar.items():
        print(f"Hämtar {namn}...", flush=True)
        try:
            data = hamta_vader_arkiv(nummer, station_id, VADER_API)
            vader_delar[namn] = data.loc[starttid:sluttid, "varde"]
        except Exception as e:
            print(f"  Fel för {namn}: {e}")
    return pd.DataFrame(vader_delar)



