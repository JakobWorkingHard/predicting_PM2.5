import pandas as pd
import joblib
import json
from pathlib import Path
from datetime import datetime, timedelta
from src.logger import setup_logger

log = setup_logger(__name__)


def generate_csv(data, path_and_name_of_csv, index = True):
    """Försöker spara en DataFrame till en CSV-fil. 
    Om filen redan existerar, görs ingenting.
    """
    try:
        # mode='x' gör att pandas kastar ett FileExistsError om filen redan finns
        data.to_csv(path_and_name_of_csv, mode='x', index=index)
        print(f"Skapade: {path_and_name_of_csv,}")
        
    except FileExistsError:
        # Filen finns redan, vi avbryter tyst
        pass

def merge_df_and_generate_csv(data1_path, data2_path, on_column: str, path_and_name_of_csv, index, how = "outer"):
    """ Tar emot två df filer och mergar ihop dessa baserat på
    kolumn: on_column
    genererar sedan en mergad csv
    NOTERING: Fungerar endast om kolumnamnen är detsamma i båda dfs:en"""
    if path_and_name_of_csv.is_file():
        return None

    df1 = pd.read_csv(data1_path)
    df2 = pd.read_csv(data2_path)
    merged_df = pd.merge(df1, df2, on=on_column, how=how)
    return generate_csv(merged_df, path_and_name_of_csv, index)


def save_champion_model(
    model,
    model_name,
    best_row,
    models_dir,
    random_state,
    metric,
    filprefix="",
):
    """
    Sparar den vinnande modellen och en JSON-fil med metadata.

    Parametrar
    ----------
    model : estimator
        Den tränade och fit:ade modellen.
    model_name : str
        Namn på modellen, t.ex. "Linear Regression".
    best_row : pd.Series
        Raden för vinnaren från results_df (innehåller alla metriker).
    models_dir : Path
        Mapp där modellen ska sparas. Skapas om den inte finns.
    random_state : int
        Frö som användes vid träning.
    metric : str
        Metrikk som avgjorde valet, t.ex. "Validation MAE".
    filprefix : str, valfri
        Prefix på filnamnen, t.ex. "forskjuten_" för den förskjuna
        modellinjen. Gör det möjligt att skilja varianterna åt i
        models-mappen och vid inläsning av champion-modellen.
    """
    models_dir = Path(models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y_%m_%d_%H-%M")
    safe_name = model_name.replace(" ", "_").lower()
    metris_namn = metric.replace(' ','_').replace("²", "2")
    model_path = models_dir / f"{filprefix}{safe_name}_{metris_namn}_{timestamp}.joblib"
    meta_path = models_dir / f"{filprefix}{safe_name}_{metris_namn}_{timestamp}.json"

    joblib.dump(model, model_path)
    print(f"Sparade modell: {model_path}")

    meta = {
        "model_name": model_name,
        "model_file": str(model_path),
        "variant": filprefix,
        "random_state": random_state,
        "selection_metric": metric,
        "metrics": best_row.to_dict(),
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Sparade metadata: {meta_path}")
    return model_path
    


def append_champion_log(log_path, model_name, metric, score, sokvag=None):
    # sokvag är en frivillig parameter. Om ingen sökväg skickas med, 
    # till exempel när baslinjen vinner, blir den tom.
    """
    Appendar en rad med vinnande modell, timestamp, metric och score
    till champion-loggen (CSV). Skapar filen med rubrikrad om den saknas.

    Parametrar
    ----------
    log_path : Path
        Sökväg till loggfilen, t.ex. "logs/champion_vanlig.csv".
    model_name : str
        Namn på vinnaren, t.ex. "Linear Regression" eller
        "Persistence Baseline" (om baslinjen vann räknas det som en giltig
        körning och loggas därmed också).
    metric : str
        Metrik som avgjorde valet, t.ex. "Validation R²".
    score : float
        Vinnarens värde på metricken.
    sokvag : Path eller None
        Sökväg till championens .joblib-fil. Tom om baslinjen vann.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    rad = pd.DataFrame(
        [
            {
                "modell": model_name,
                "timestamp": timestamp,
                "metric": metric,
                "score": score,
                # Bara filnamnet sparas, så att loggen fungerar på alla datorer.
                # Modellen läses in med cfg.models_dir / filnamnet.
                "sokvag": Path(sokvag).name if sokvag is not None else "",
            }
        ]
    )

    # rubrik behövs bara om filen inte finns än
    header = not log_path.is_file()
    rad.to_csv(log_path, mode="a", header=header, index=False)
    print(f"Loggade champion i: {log_path} ({model_name}, {timestamp})")


def champion_is_fresh(log_path, antal_dagar) -> bool:
    """
    Avgör om senaste champion-loggningen är gjord inom de senaste
    'antal_dagar' dagarna.

    Returnerar True om champion är färsk (orskestratorns steg 5 kan skippas),
    False annars. Fail-safe: om filen saknas, är tom eller innehåller en
    ogiltig timestamp returneras False, så att en full träning tvingas fram.

    Parametrar
    ----------
    log_path : Path
        Sökväg till loggfilen, t.ex. "logs/champion_vanlig.csv".
    antal_dagar : int
        Maximal ålder i dagar för att champion ska räknas som färsk.
    """
    log_path = Path(log_path)
    if not log_path.is_file():
        return False

    try:
        log_df = pd.read_csv(log_path)
        if log_df.empty or "timestamp" not in log_df.columns:
            return False

        senaste_timestamp = pd.to_datetime(log_df["timestamp"].iloc[-1])
        if pd.isna(senaste_timestamp):
            return False

        alder = datetime.now() - senaste_timestamp.to_pydatetime()
        return alder <= timedelta(days=antal_dagar)

    except Exception as e:
        print(f"Varning: kunde inte läsa {log_path} ({e}) - kör full träning.")
        return False

    

def hamta_champion_modell(models_dir, champion_log):
    """
    Laddar den senaste sparade champion-modellen (exklusive förskjuna
    varianter) och returnerar (modell, namn).

    Använder den senaste raden i champion-loggen som inte är
    "Persistence Baseline" för att hitta rätt modellfil, och utesluter
    filer med prefixet "forskjuten_".

    Returnerar
    -------
    tuple
        (modell, namn) om en modell hittas, annars (None, None).
    """
    log_path = Path(champion_log)
    if not log_path.is_file():
        return None, None

    try:
        log_df = pd.read_csv(log_path)
    except Exception as e:
        print(f"Varning: kunde inte läsa {log_path} ({e}).")
        return None, None

    if log_df.empty or "modell" not in log_df.columns:
        return None, None

    modellrader = log_df[log_df["modell"] != "Persistence Baseline"]
    if modellrader.empty:
        print("Ingen sparad champion-modell i loggen (endast baseline-vinster).")
        return None, None

    # Senaste modellvinnaren
    namn = modellrader["modell"].iloc[-1]
    safe_name = namn.replace(" ", "_").lower()

    models_dir = Path(models_dir)
    filer = [
        f for f in models_dir.glob(f"{safe_name}_*.joblib")
        if not f.name.startswith("forskjuten_")
    ]

    if not filer:
        print(f"Varning: hittade ingen modellfil för {namn!r} i {models_dir}.")
        return None, None

    senaste_fil = max(filer, key=lambda f: f.stat().st_mtime)
    print(f"Läser in champion-modell: {senaste_fil}")
    return joblib.load(senaste_fil), namn


def append_jamfordelse_log(log_path, df):
    """
    Appendar en rad (eller flera) med head-to-head-jämförelse till en CSV.
    Skapar filen med rubrikrad om den saknas.

    Parametrar
    ----------
    log_path : Path
        Sökväg till loggfilen, t.ex. "logs/jamforelse_champion.csv".
    df : pd.DataFrame
        Rader att appenda, t.ex. en rad per modell i jämförelsen.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    header = not log_path.is_file()
    df.to_csv(log_path, mode="a", header=header, index=False)
    print(f"Loggade jämförelse i: {log_path}")


def append_datakontroll_log(log_path, dataset, antal_merged, antal_validerad, antal_kvar, saknade):
    """
    Skriver ut hur många rader som togs bort av dropna, och appendar
    samma information som en rad i datakontroll-loggen (CSV).
    Skapar filen med rubrikrad om den saknas.

    Parametrar
    ----------
    log_path : Path
        Sökväg till loggfilen, t.ex. "logs/datakontroll.csv".
    dataset : str
        Namn på datasetet, t.ex. filnamnet för train eller val.
    antal_merged : int
        Antal rader i den mergade filen.
    antal_validerad : int
        Antal rader efter validate_data. Kan vara fler än antal_merged,
        eftersom saknade timmar läggs till som tomma rader.
    antal_kvar : int
        Antal rader efter dropna.
    saknade : pd.Series
        Antal saknade värden per feature/target-kolumn, före dropna.
        En rad kan sakna flera värden, så summan kan vara större än
        antalet borttagna rader.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    borttagna = antal_validerad - antal_kvar
    andel = borttagna / antal_validerad

    # Utskrift
    log.info("--- Datakontroll: %s ---", dataset)
    log.info("Rader i mergad fil: %s", antal_merged)
    log.info("Rader efter validate_data: %s", antal_validerad)
    log.info("Rader efter dropna: %s", antal_kvar)
    log.info("Borttagna rader: %s (%.1f%%)", borttagna, andel * 100)
    
    log.info("Saknade värden per kolumn (en rad kan sakna flera):\n%s",
         saknade[saknade > 0].to_string())

    # En rad i loggen. Alla kolumner tas med, även de med 0 saknade,
    # så att loggen har samma kolumner vid varje körning.
    rad = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "dataset": dataset,
        "rader_merged": antal_merged,
        "rader_validerad": antal_validerad,
        "rader_kvar": antal_kvar,
        "borttagna": borttagna,
        "andel_borttagna": round(andel, 4),
    }
    for kolumn, antal in saknade.items():
        rad[f"saknade_{kolumn}"] = int(antal)

    header = not log_path.is_file()
    pd.DataFrame([rad]).to_csv(log_path, mode="a", header=header, index=False)
    log.info("Loggade datakontroll i: %s", log_path)