from pathlib import Path
from src.metrics import evaluate_model, display_df, metric_direction

import joblib
import pandas as pd

from src.logger import setup_logger

log = setup_logger(__name__)


def load_latest_champion(log_path, models_dir):
    """
    Läser in den senast sparade championen via kolumnen 'sokvag' i loggen.

    Rader där 'sokvag' är tom hoppas över. Det är rader där baslinjen
    vann, och då sparades ingen modell.

    Returnerar (modell, namn, filnamn), eller (None, None, None) om
    loggen saknas, saknar kolumnen 'sokvag' eller om modellfilen inte finns.
    """
    log_path = Path(log_path)
    if not log_path.is_file():
        log.info("Ingen champion-logg hittades: %s", log_path)
        return None, None, None

    log_df = pd.read_csv(log_path)

    if "sokvag" not in log_df.columns:
        log.warning("Loggen %s saknar kolumnen 'sokvag'.", log_path)
        return None, None, None

    # Behåll bara rader där en modell faktiskt sparades.
    # En tom sökväg blir NaN när CSV-filen läses in.
    modellrader = log_df[log_df["sokvag"].notna() & (log_df["sokvag"] != "")]
    if modellrader.empty:
        log.info("Ingen sparad champion-modell i %s.", log_path)
        return None, None, None

    # Den senaste raden är den senaste championen
    senaste = modellrader.iloc[-1]
    filnamn = senaste["sokvag"]
    modellfil = Path(models_dir) / filnamn

    if not modellfil.is_file():
        log.warning("Modellfilen finns inte: %s", modellfil)
        return None, None, None

    log.info("Läser in champion %s från %s", senaste["modell"], modellfil)
    return joblib.load(modellfil), senaste["modell"], filnamn

def _metric_key_and_direction(metric):

    """Översätter t.ex. "Validation R²" till nyckeln i evaluate_model
    ("R2") och hämtar riktningen från metrics.metric_direction."""
    
    if "Bias" in metric:
        key = "Bias"
    elif "R²" in metric or "R2" in metric:
        key = "R2"
    elif "RMSE" in metric or "MSE" in metric:
        key = "RMSE"
    else:
        key = "MAE"
    return key, metric_direction(metric)

def compete_with_champion(
    new_model,
    new_name,
    old_model,
    old_name,
    test_path,
    features,
    target,
    metric,
):
    """
    Låter dagens bästa modell och den tidigare championen göra prognoser
    på samma testdata, utan att träna om någon av dem.

    Dagens modell vinner bara om den är bättre. Vid lika resultat behålls
    den tidigare championen. Om det inte finns någon tidigare champion
    vinner dagens modell automatiskt.

    Returnerar (winner, results_df), där winner är "new" eller "old".
    """
     # Läs in testdata
    test_df = pd.read_csv(test_path)
    X_test = test_df[features]
    y_test = test_df[target]

    # Utvärdera den nya kandidaten
    new_results = evaluate_model(y_test, new_model.predict(X_test))

    # Om ingen tidigare champion finns
    if old_model is None:
        log.info(
            "Ingen tidigare champion finns. %s vinner automatiskt.",
            new_name
        )

        results_df = pd.DataFrame([
            {"Modell": f"{new_name} (dagens bästa)", **new_results}
        ])

        display_df(results_df)
        return "new", results_df

    # Utvärdera tidigare champion på samma testdata
    old_results = evaluate_model(y_test, old_model.predict(X_test))

    # Välj vilket mått som ska avgöra jämförelsen
    key, direction = _metric_key_and_direction(metric)
    new_score = new_results[key]
    old_score = old_results[key]

    if direction == "higher":
        new_wins = new_score > old_score
    elif direction == "lower":
        new_wins = new_score < old_score
    else:
        new_wins = abs(new_score) < abs(old_score)

    # Sammanställ testresultaten
    results_df = pd.DataFrame([
        {"Modell": f"{new_name} (dagens bästa)", **new_results},
        {"Modell": f"{old_name} (tidigare champion)", **old_results},
    ])

    display_df(results_df)

    winner = "new" if new_wins else "old"

    log.info(
        "Champion-tävling på testdata (%s rader), mått %s: dagens %.4f, tidigare %.4f. Vinnare: %s.",
        len(test_df), key, new_score, old_score, winner,
    )

    return winner, results_df