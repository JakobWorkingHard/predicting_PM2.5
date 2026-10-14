from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from tabulate import tabulate
import pandas as pd

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
