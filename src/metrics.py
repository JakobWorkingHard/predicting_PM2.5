from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tabulate import tabulate
import pandas as pd
import numpy as np
from datetime import datetime

from src.io import append_jamfordelse_log
from src.logger import setup_logger

log = setup_logger(__name__)

#------------------------------------------------------------------------
# 1. Grundläggande mått
#------------------------------------------------------------------------

def calculate_bias(y_true, y_pred):
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    return float(np.mean(y_pred - y_true))

#------------------------------------------------------------------------
# 2. Specialiserade mått
#------------------------------------------------------------------------

def calculate_high_pm25_metrics(y_true, y_pred, threshold):
    """Beräknar MAE och Bias vid höga PM2.5-värden."""

    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)

    mask = y_true >= threshold

    if not mask.any():
        return {
            "High PM2.5 MAE": np.nan,
            "High PM2.5 Bias": np.nan,
            "High PM2.5 Count": 0,
        }

    return {
        "High PM2.5 MAE": mean_absolute_error(
            y_true[mask], y_pred[mask]
        ),
        "High PM2.5 Bias": calculate_bias(
            y_true[mask], y_pred[mask]
        ),
        "High PM2.5 Count": int(mask.sum()),
    }

#----------------------------------------------------------
# 3. Gemensam utvärdering
#----------------------------------------------------------

def evaluate_model(y_true, y_pred, threshold=None):
    """
    Utvärderar en modells prediktioner.

    Beräknar MAE, RMSE, R² och Bias.
    Om threshold anges beräknas även mått för höga PM2.5-värden.

    Parametrar
    ----------
    y_true : array-like
        Faktiska PM2.5-värden.
    y_pred : array-like
        Predicerade PM2.5-värden.
    threshold : float, optional
        Gränsvärde för höga PM2.5-koncentrationer.

    Returnerar
    -------
    dict
        Dictionary med modellens utvärderingsmått.
    """

    metrics = {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": mean_squared_error(y_true, y_pred) ** 0.5,
        "R2": r2_score(y_true, y_pred),
        "Bias": calculate_bias(y_true, y_pred),
    }

    if threshold is not None:
        metrics.update(
            calculate_high_pm25_metrics(y_true, y_pred, threshold)
        )

    return metrics


#----------------------------------------------------------
# 4. Modelljämförelse
#----------------------------------------------------------

def build_comparison_table(results_df, baseline_val_metrics, sort_by):
    """
    Bygger en jämförelsetabell med alla modeller och persistence baseline.

    Tar automatiskt med samtliga valideringsmått som finns
    både i modellresultaten och baseline-resultatet.

    Parametrar
    ----------
    results_df : pd.DataFrame
        Resultat från train_and_evaluate_models.
    baseline_val_metrics : dict
        Utvärderingsmått för persistence baseline.
    sort_by : str
        Kolumn som tabellen ska sorteras efter.

    Returnerar
    -------
    pd.DataFrame
        Jämförelsetabell med modeller och baseline.
    """

    # 1. Hitta samtliga valideringskolumner
    val_cols = [
        col for col in results_df.columns
        if col.startswith("Validation ")
    ]

    # 2. Välj modellnamn och valideringsmått
    model_comparison = results_df[
        ["Modell", *val_cols]
    ].copy()

    # 3. Skapa baseline-rad med motsvarande mått
    baseline_row = {"Modell": "Persistence Baseline"}

    for col in val_cols:
        metric_name = col.removeprefix("Validation ")

        if metric_name == "R²":
            metric_name = "R2"

        baseline_row[col] = baseline_val_metrics.get(
            metric_name, float("nan")
        )

    # 4. Slå samman modeller och baseline
    comparison_df = pd.concat(
        [pd.DataFrame([baseline_row]), model_comparison],
        ignore_index=True,
    )

    # 5. Sortera enligt valt utvärderingsmått
    if sort_by not in comparison_df.columns:
        raise ValueError(f"Okänt sorteringsmått: {sort_by}")

    if "Bias" in sort_by:
        comparison_df = comparison_df.sort_values(
            by=sort_by,
            key=lambda col: col.abs()
        )

    else:
        higher_is_better = "R²" in sort_by or "R2" in sort_by

        comparison_df = comparison_df.sort_values(
            by=sort_by,
            ascending=not higher_is_better
        )

    comparison_df = comparison_df.reset_index(drop=True)

    return comparison_df

#----------------------------------------------------------
# 5. Modellval
#----------------------------------------------------------

def select_best_model(results_df, metric="Validation MAE"):
    """
    Väljer den modell som presterar bäst enligt valt mått.

    Urvalsregler
    ------------
    MAE, RMSE : lägre är bättre.
    R²        : högre är bättre.
    Bias      : närmare noll är bättre.

    Parametrar
    ----------
    results_df : pd.DataFrame
        Jämförelsetabell med modellernas resultat.
    metric : str
        Kolumn som används för modellval.

    Returnerar
    ----------
    tuple[str, pd.Series]
        Namn och resultatrad för bästa modellen.
    """

    # 1. Kontrollera att måttet finns
    if metric not in results_df.columns:
        raise ValueError(
            f"Kolumnen {metric!r} finns inte i results_df. "
            f"Tillgängliga kolumner: {list(results_df.columns)}"
        )

    # 2. Välj rätt urvalsregel
    if "Bias" in metric:
        best_idx = results_df[metric].abs().idxmin()

    elif "R²" in metric or "R2" in metric:
        best_idx = results_df[metric].idxmax()

    else:
        best_idx = results_df[metric].idxmin()

    # 3. Hämta bästa modellen
    best_row = results_df.loc[best_idx]
    best_name = best_row["Modell"]

    return best_name, best_row


#----------------------------------------------------------
# 6. Presentation och testjämförelse
#----------------------------------------------------------



def display_df(df):
    print(tabulate(df, headers="keys", tablefmt="fancy_grid", showindex=False))



def jamfor_championer(
    cfg,
    champion_modell,
    champion_namn: str,
    forskjuten_modell,
    forskjuten_namn: str,
    test_path_vanlig,
    test_path_forskjuten,
):
    """
    Head-to-head på TEST-data: den nuvarande championen mot den förskjuna
    championen, plus persistence-baseline, på de testrader som är
    kompletta i BÅDA varianterna. Körs vid omträning av den förskjuna
    modellinjen (orchestrator block 6).

    Championen predikteras från sin egen processed-fil (vädret gäller T)
    och den förskjuna modellen från sin (vädret gäller T+6). Raderna
    matchas via kolumnen 'tid'.

    Resultatet visas och appendas till logs/jamfordelse_forskjuten.csv.
    Observera: den förskjuna modellen utvärderas här med OBSERVERAT väder
    vid T+6 ("orakelprognos"), vilket ger ett övre gräns-värde – i
    produktion tillkommer prognosfel (se docs/evaluation.md).

    Parametrar
    ----------
    cfg : ProjectConfig
        Konfiguration: features, target-kolumn, loggar, models-katalog.
    champion_modell : estimator
        Den nuvarande championen (laddad av anroparen, t.ex. via
        hamta_champion_modell).
    champion_namn : str
        Namn på den nuvarande championen, t.ex. "SVR".
    forskjuten_modell : estimator
        Den tränade förskjuna championen.
    forskjuten_namn : str
        Namn på den förskjuna championen, t.ex. "SVR (T+6)".
    test_path_vanlig : Path
        Processad testfil för championens variant (vädret gäller T).
    test_path_forskjuten : Path
        Processad testfil för den förskjuna varianten (vädret gäller T+6).
    """
    if champion_modell is None:
        log.warning(
            "Hittade ingen sparad champion-modell. "
            "Hoppar över head-to-head-jämförelsen på testdata."
        )
        return

    champion_test = pd.read_csv(test_path_vanlig)
    forskjuten_test = pd.read_csv(test_path_forskjuten)

    gemensamma_tider = set(champion_test["tid"]) & set(forskjuten_test["tid"])

    if not gemensamma_tider:
        log.warning(
            "Inga gemensamma testrader mellan championen och den "
            "förskjuna varianten. Hoppar över jämförelsen."
        )
        return

    # Samma tider, samma sortering: raderna motsvarar varandra exakt.
    champion_rader = (
        champion_test[champion_test["tid"].isin(gemensamma_tider)]
        .sort_values("tid")
        .reset_index(drop=True)
    )
    forskjuten_rader = (
        forskjuten_test[forskjuten_test["tid"].isin(gemensamma_tider)]
        .sort_values("tid")
        .reset_index(drop=True)
    )

    if not champion_rader[cfg.target_column].equals(
        forskjuten_rader[cfg.target_column]
    ):
        log.warning(
            "Målvärdena skiljer mellan filerna på de gemensamma raderna. "
            "Jämförelsen kan vara missvisande."
        )

    y = champion_rader[cfg.target_column]

    prediktioner = {
        f"{champion_namn} (nuvarande champion)": champion_modell.predict(
            champion_rader[cfg.features]
        ),
        forskjuten_namn: forskjuten_modell.predict(forskjuten_rader[cfg.features]),
        "Persistence Baseline": champion_rader["pm25"],
    }

    rader = []
    for namn, y_pred in prediktioner.items():
        resultat = evaluate_model(y, y_pred)
        rader.append(
            {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "Modell": namn,
                "MAE": resultat["MAE"],
                "RMSE": resultat["RMSE"],
                "R2": resultat["R2"],
                "rader": len(champion_rader),
            }
        )

    jamfordelse_df = pd.DataFrame(rader)
    display_df(jamfordelse_df)

    append_jamfordelse_log(cfg.jamfordelse_log, jamfordelse_df)

    log.info(
        "Head-to-head på testdata (%s gemensamma rader) är klar.",
        len(champion_rader),
    )
