import numpy as np
import pandas as pd
import pytest

from sklearn.linear_model import LinearRegression

from src.train_models import (
    train_and_evaluate_models,
    persistence_baseline,
)


@pytest.fixture
def sample_data():
    """Skapar enkla testdata för träning och validering."""

    X_train = pd.DataFrame({
        "pm25": [10, 15, 20, 25, 30, 40, 50, 60, 70, 80],
    })

    y_train = pd.Series(
        [12, 17, 22, 27, 32, 42, 52, 62, 72, 82]
    )

    X_val = pd.DataFrame({
        "pm25": [15, 30, 50, 75],
    })

    y_val = pd.Series([17, 32, 52, 77])

    return X_train, y_train, X_val, y_val


# ----------------------------------------------------------
# 1. Test av modellträning och utvärdering
# ----------------------------------------------------------

def test_train_and_evaluate_models(sample_data):

    X_train, y_train, X_val, y_val = sample_data

    models = {
        "Linear Regression": LinearRegression()
    }

    results_df, trained_models = train_and_evaluate_models(
        models, X_train, y_train, X_val, y_val
    )

    # Kontrollera att modellen tränats
    assert "Linear Regression" in trained_models
    assert len(results_df) == 1

    # Kontrollera att alla mått finns
    expected_columns = [
        "Train MAE",
        "Train RMSE",
        "Train R²",
        "Train Bias",
        "Train High PM2.5 MAE",
        "Validation MAE",
        "Validation RMSE",
        "Validation R²",
        "Validation Bias",
        "Validation High PM2.5 MAE",
        "Validation High PM2.5 Bias",
        "Validation High PM2.5 Count",
    ]

    for col in expected_columns:
        assert col in results_df.columns

    # Kontrollera gränsvärdet indirekt:
    # 90:e percentilen av y_train = 73.0
    # Endast y_val = 77 ligger över gränsen.
    assert results_df.iloc[0]["Validation High PM2.5 Count"] == 1

    # Modellen bör lära sig sambandet y = pm25 + 2
    assert results_df.iloc[0]["Validation MAE"] == pytest.approx(0)


# ----------------------------------------------------------
# 2. Test av persistence baseline
# ----------------------------------------------------------

def test_persistence_baseline(sample_data):

    X_train, y_train, X_val, y_val = sample_data

    train_metrics, val_metrics = persistence_baseline(
        X_train, y_train, X_val, y_val
    )

    # Kontrollera att samtliga mått finns
    expected_metrics = [
        "MAE",
        "RMSE",
        "R2",
        "Bias",
        "High PM2.5 MAE",
        "High PM2.5 Bias",
        "High PM2.5 Count",
    ]

    for metric in expected_metrics:
        assert metric in train_metrics
        assert metric in val_metrics

    # Baseline predikterar pm25 utan förändring,
    # medan faktiska värden är pm25 + 2.
    assert val_metrics["MAE"] == pytest.approx(2.0)
    assert val_metrics["Bias"] == pytest.approx(-2.0)

    # En hög observation i valideringsdata
    assert val_metrics["High PM2.5 Count"] == 1
    assert val_metrics["High PM2.5 MAE"] == pytest.approx(2.0)