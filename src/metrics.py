from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tabulate import tabulate
import pandas as pd
from datetime import datetime

from src.io import hamta_champion_modell, append_jamfordelse_log
from src.logger import setup_logger

log = setup_logger(__name__)

def evaluate_model(y_true, y_pred):
    """
    Beräknar MAE, RMSE och R² för en modell/baseline.

    Parametrar
    ----------
    y_true : pd.Series
        Sanna värden.
    y_pred : pd.Series
        Predicerade värden.

    Returnerar
    -------
    dict
        {"MAE": float, "RMSE": float, "R2": float}
    """
    return {
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": mean_squared_error(y_true, y_pred) ** 0.5,
        "R2": r2_score(y_true, y_pred),
    }



def display_df(df):
    print(tabulate(df, headers="keys", tablefmt="fancy_grid", showindex=False))


def select_best_model(results_df, metric="Validation MAE"):
    """
    Väljer den modell i results_df som presterar bäst på `metric`.

    Avgör automatiskt om lägre eller högre är bättre:
      - Kolumner som innehåller "R²" eller "R2" -> högre är bättre (idxmax)
      - MAE, MSE, RMSE och övriga -> lägre är bättre (idxmin)

    Parametrar
    ----------
    results_df : pd.DataFrame
        Tabell från train_and_evaluate_models.
    metric : str
        Kolumnnamn i results_df, t.ex. "Validation MAE".

    Returnerar
    -------
    (best_name, best_row) : tuple[str, pd.Series]
    """
    # Kolumner i results_df där högre värde är bättre
    _MAX_METRICS = {"Train R²", "Validation R²"}
    if metric not in results_df.columns:
        raise ValueError(
            f"Kolumnen {metric!r} finns inte i results_df. "
            f"Tillgängliga kolumner: {list(results_df.columns)}"
        )

    higher_is_better = metric in _MAX_METRICS or "R²" in metric or "R2" in metric
    selector = results_df[metric].idxmax if higher_is_better else results_df[metric].idxmin

    best_idx = selector()
    best_row = results_df.loc[best_idx]
    best_name = best_row["Modell"]
    return best_name, best_row


def build_comparison_table(results_df, baseline_val_metrics, sort_by):
    """
    Bygger en jämförelsetabell där alla modeller + persistence baseline
    sorteras på selection_metric (finns i config.toml).

    Parametrar
    ----------
    results_df : pd.DataFrame
        Tabell från train_and_evaluate_models.
    baseline_val_metrics : dict
        Dict med nycklar "MAE", "RMSE", "R2" från persistence_baseline.

    Returnerar
    -------
    pd.DataFrame
        Kolumner: Modell, Validation MAE, Validation RMSE, Validation R².
        Persistence Baseline är inlagd som en rad.
    """
    model_cols = ["Modell", "Validation MAE", "Validation RMSE", "Validation R²"]
    model_comparison = results_df[model_cols].copy()

    baseline_row = pd.DataFrame([{
        "Modell":          "Persistence Baseline",
        "Validation MAE":  baseline_val_metrics["MAE"],
        "Validation RMSE": baseline_val_metrics["RMSE"],
        "Validation R²":   baseline_val_metrics["R2"],
    }])

    comparison_df = (
        pd.concat([baseline_row, model_comparison], ignore_index=True)
        .sort_values(by=sort_by, ascending=True)
        .reset_index(drop=True)
    )
    return comparison_df


def jamfor_championer(
    cfg,
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
    forskjuten_modell : estimator
        Den tränade förskjuna championen.
    forskjuten_namn : str
        Namn på den förskjuna championen, t.ex. "SVR (T+6)".
    test_path_vanlig : Path
        Processad testfil för championens variant (vädret gäller T).
    test_path_forskjuten : Path
        Processad testfil för den förskjuna varianten (vädret gäller T+6).
    """
    champion_modell, champion_namn = hamta_champion_modell(
        cfg.models_dir,
        cfg.champion_log,
    )

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
