import numpy as np
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
    Tränar och utvärderar samtliga modeller.

    Utvärderingen omfattar MAE, RMSE, R², Bias samt
    särskilda mått för höga PM2.5-koncentrationer.

    Gränsen för höga PM2.5-värden definieras som
    90:e percentilen av träningsdata.

    Parametrar
    ----------
    models : dict[str, estimator]
        Modeller som ska tränas och jämföras.
    X_train, X_val : pd.DataFrame
        Förklarande variabler.
    y_train, y_val : pd.Series
        Faktiska målvärden.

    Returnerar
    -------
    tuple[pd.DataFrame, dict]
        Resultattabell och tränade modeller.
    """

    # 1. Förbered resultat och modeller
    results = []
    trained_models = {}

    # 2. Beräkna gemensam gräns från träningsdata
    high_pm25_threshold = y_train.quantile(0.90)

    print(
        f"High PM2.5 threshold: "
        f"{high_pm25_threshold:.2f} µg/m³"
    )

    # 3. Träna och utvärdera varje modell
    for name, model in models.items():
        print(f"Tränar {name}...")

        model.fit(X_train, y_train)

        y_pred_train = model.predict(X_train)
        y_pred_val = model.predict(X_val)

        # 4. Beräkna samtliga utvärderingsmått
        train_metrics = evaluate_model(
            y_train, y_pred_train, threshold=high_pm25_threshold
        )

        val_metrics = evaluate_model(
            y_val, y_pred_val, threshold=high_pm25_threshold
        )

        # 5. Sammanställ resultat
        results.append({
            "Modell": name,
            **{
                f"Train {k.replace('R2', 'R²')}": v
                for k, v in train_metrics.items()
            },
            **{
                f"Validation {k.replace('R2', 'R²')}": v
                for k, v in val_metrics.items()
            },
        })

        trained_models[name] = model

    # 6. Skapa och sortera resultattabell
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
    Persistence-baseline: antar att framtida PM2.5
    är lika med det aktuella värdet.

    Utvärderas med samma mått och gränsvärde
    som övriga modeller.

    Returnerar
    -------
    tuple[dict, dict]
        Utvärderingsmått för träning och validering.
    """

    # 1. Beräkna samma gränsvärde
    high_pm25_threshold = y_train.quantile(0.90)

    # 2. Persistence-prediktioner
    y_pred_train = X_train["pm25"]
    y_pred_val = X_val["pm25"]

    # 3. Utvärdera baseline
    train_metrics = evaluate_model(
        y_train, y_pred_train, threshold=high_pm25_threshold
    )

    val_metrics = evaluate_model(
        y_val, y_pred_val, threshold=high_pm25_threshold
    )

    return train_metrics, val_metrics

