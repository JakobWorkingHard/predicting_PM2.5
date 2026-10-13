import pandas as pd
from src.metrics import evaluate_model

from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.svm import SVR
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from lightgbm import LGBMRegressor
from xgboost import XGBRegressor


def build_model_registry(random_state=42):
    """
    Returnerar en dict med namn -> (estimator) för alla modeller
    som ska tävla i modellturneringen.

    Parametrar
    ----------
    random_state : int
        Slumpvärde för reproducerbarhet hos modeller som stödjer det.

    Returnerar
    -------
    dict[str, estimator]
    """
    return {
        "Linear Regression": LinearRegression(),

        "Ridge Regression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", Ridge(alpha=1.0)),
        ]),

        "Random Forest": RandomForestRegressor(
            n_estimators=200,
            random_state=random_state,
            n_jobs=-1,
        ),

        "HistGradientBoosting": HistGradientBoostingRegressor(
            random_state=random_state,
        ),

        "SVR": Pipeline([
            ("scaler", StandardScaler()),
            ("model", SVR(kernel="rbf", C=1.0, epsilon=0.1)),
        ]),

        "LightGBM": LGBMRegressor(
            random_state=random_state,
            n_jobs=-1,
            verbose=-1,
        ),

        "XGBoost": XGBRegressor(
            random_state=random_state,
            n_jobs=-1,
            verbosity=0,
        ),
    }


def train_and_evaluate_models(models, X_train, y_train, X_val, y_val):
    """
    Tränar varje modell i `models` på träningsdata, predicerar på både
    tränings- och valideringsdata, och utvärderar med MAE, RMSE och R².

    Parametrar
    ----------
    models : dict[str, estimator]
        Namn -> estimator, t.ex. från build_model_registry().
    X_train : pd.DataFrame
    y_train : pd.Series
    X_val : pd.DataFrame
    y_val : pd.Series

    Returnerar
    -------
    (results_df, trained_models) : tuple[pd.DataFrame, dict]
        results_df      : en rad per modell, sorterad på Validation MAE.
        trained_models  : namn -> fit estimator.
    """
    results = []
    trained_models = {}

    for name, model in models.items():
        print(f"Tränar {name}...")

        model.fit(X_train, y_train)

        y_pred_train = model.predict(X_train)
        y_pred_val   = model.predict(X_val)

        train_metrics = evaluate_model(y_train, y_pred_train)
        val_metrics   = evaluate_model(y_val, y_pred_val)

        results.append({
            "Modell":          name,
            "Train MAE":       train_metrics["MAE"],
            "Train RMSE":      train_metrics["RMSE"],
            "Train R²":        train_metrics["R2"],
            "Validation MAE":  val_metrics["MAE"],
            "Validation RMSE": val_metrics["RMSE"],
            "Validation R²":   val_metrics["R2"],
        })

        trained_models[name] = model

    results_df = (
        pd.DataFrame(results)
        .sort_values(by="Validation MAE", ascending=True)
        .reset_index(drop=True)
    )

    return results_df, trained_models




def load_train_val_data(
    train_path,
    val_path,
    features,
    target,
):
    """
    Läser in processad tränings- och valideringsdata och delar upp i X och y.

    Parametrar
    ----------
    train_path : Path
        Sökväg till processad träningsdata (cfg.train_processed).
    val_path : Path
        Sökväg till processad valideringsdata (cfg.val_processed).
    features : list[str]
        Kolumner som ska användas som features (cfg.features).
    target : str
        Namn på målvariabeln, t.ex. "target".

    Returnerar
    -------
    (X_train, y_train, X_val, y_val) : tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]
    """
    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    X_train = train_df[features]
    y_train = train_df[target]

    X_val = val_df[features]
    y_val = val_df[target]

    return X_train, y_train, X_val, y_val



def persistence_baseline(X_train, y_train, X_val, y_val):
    """
    Persistence-baseline: predikterar att PM2.5 om `horisont` timmar
    är lika med det aktuella PM2.5-värdet.

    Parametrar
    ----------
    X_train, X_val : pd.DataFrame
        Måste innehålla kolumnen "pm25".
    y_train, y_val : pd.Series
        Sanna målvärden för träning respektive validering.

    Returnerar
    -------
    (train_metrics, val_metrics) : tuple[dict, dict]
        Varje dict innehåller MAE, RMSE och R².
    """
    y_pred_train = X_train["pm25"]
    y_pred_val   = X_val["pm25"]

    train_metrics = evaluate_model(y_train, y_pred_train)
    val_metrics   = evaluate_model(y_val, y_pred_val)

    return train_metrics, val_metrics

