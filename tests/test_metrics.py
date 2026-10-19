import pytest
import pandas as pd

from src.metrics import evaluate_model, build_comparison_table, select_best_model


def test_evaluate_model_without_threshold():
    """Kontrollerar grundläggande mått inklusive Bias."""

    y_true = [10, 20, 30, 40, 50]
    y_pred = [12, 18, 25, 35, 40]

    result = evaluate_model(y_true, y_pred)

    assert result["MAE"] == pytest.approx(4.8)
    assert result["RMSE"] == pytest.approx(5.62, abs=0.01)
    assert result["R2"] == pytest.approx(0.842)
    assert result["Bias"] == pytest.approx(-4.0)


def test_evaluate_model_with_threshold():
    """Kontrollerar utvärdering vid höga PM2.5-värden."""

    y_true = [10, 20, 30, 40, 50]
    y_pred = [12, 18, 25, 35, 40]

    result = evaluate_model(y_true, y_pred, threshold=40)

    assert result["High PM2.5 MAE"] == pytest.approx(7.5)
    assert result["High PM2.5 Bias"] == pytest.approx(-7.5)
    assert result["High PM2.5 Count"] == 2


def test_evaluate_model_without_high_values():
    """Kontrollerar att inga höga observationer hanteras."""

    y_true = [10, 20, 30]
    y_pred = [12, 18, 25]

    result = evaluate_model(y_true, y_pred, threshold=100)

    assert result["High PM2.5 Count"] == 0
    assert result["High PM2.5 MAE"] != result["High PM2.5 MAE"]
    assert result["High PM2.5 Bias"] != result["High PM2.5 Bias"]


def test_build_comparison_table():
    """Kontrollerar att modeller och baseline jämförs korrekt."""

    results_df = pd.DataFrame([
        {
            "Modell": "Random Forest",
            "Validation MAE": 3.0,
            "Validation RMSE": 4.5,
            "Validation R²": 0.80,
            "Validation Bias": -1.0,
            "Validation High PM2.5 MAE": 6.0,
        },
        {
            "Modell": "Linear Regression",
            "Validation MAE": 4.0,
            "Validation RMSE": 5.0,
            "Validation R²": 0.70,
            "Validation Bias": -2.0,
            "Validation High PM2.5 MAE": 8.0,
        },
    ])

    baseline_metrics = {
        "MAE": 5.0,
        "RMSE": 6.0,
        "R2": 0.60,
        "Bias": -3.0,
        "High PM2.5 MAE": 10.0,
    }

    comparison = build_comparison_table(
        results_df,
        baseline_metrics,
        sort_by="Validation MAE",
    )

    assert len(comparison) == 3
    assert comparison.iloc[0]["Modell"] == "Random Forest"
    assert "Validation Bias" in comparison.columns
    assert "Validation High PM2.5 MAE" in comparison.columns

    baseline = comparison[
        comparison["Modell"] == "Persistence Baseline"
    ].iloc[0]

    assert baseline["Validation MAE"] == 5.0
    assert baseline["Validation Bias"] == -3.0
    assert baseline["Validation High PM2.5 MAE"] == 10.0
    assert baseline["Validation R²"] == pytest.approx(0.60)


def test_build_comparison_table_sort_r2():
    """Kontrollerar att högsta R² hamnar först."""

    results_df = pd.DataFrame([
        {
            "Modell": "Model A",
            "Validation MAE": 3.0,
            "Validation R²": 0.70,
        },
        {
            "Modell": "Model B",
            "Validation MAE": 2.0,
            "Validation R²": 0.90,
        },
    ])

    baseline_metrics = {
        "MAE": 4.0,
        "R2": 0.50,
    }

    comparison = build_comparison_table(
        results_df,
        baseline_metrics,
        sort_by="Validation R²",
    )

    assert comparison.iloc[0]["Modell"] == "Model B"


def test_select_best_model_mae():
    """Lägsta MAE ska vinna."""

    results_df = pd.DataFrame([
        {"Modell": "Model A", "Validation MAE": 3.0},
        {"Modell": "Model B", "Validation MAE": 2.0},
    ])

    name, row = select_best_model(results_df, "Validation MAE")

    assert name == "Model B"
    assert row["Validation MAE"] == 2.0


def test_select_best_model_r2():
    """Högsta R² ska vinna."""

    results_df = pd.DataFrame([
        {"Modell": "Model A", "Validation R²": 0.90},
        {"Modell": "Model B", "Validation R²": 0.70},
    ])

    name, row = select_best_model(results_df, "Validation R²")

    assert name == "Model A"


def test_select_best_model_bias():
    """Bias närmast noll ska vinna."""

    results_df = pd.DataFrame([
        {"Modell": "Model A", "Validation Bias": -5.0},
        {"Modell": "Model B", "Validation Bias": 1.0},
        {"Modell": "Model C", "Validation Bias": 3.0},
    ])

    name, row = select_best_model(results_df, "Validation Bias")

    assert name == "Model B"


def test_build_comparison_table_sort_bias():
    """Bias närmast noll ska hamna först."""

    results_df = pd.DataFrame([
        {"Modell": "Model A", "Validation Bias": -5.0},
        {"Modell": "Model B", "Validation Bias": 1.0},
    ])

    baseline_metrics = {"Bias": -2.0}

    comparison = build_comparison_table(
        results_df,
        baseline_metrics,
        sort_by="Validation Bias",
    )

    assert comparison["Modell"].tolist() == [
        "Model B",
        "Persistence Baseline",
        "Model A",
    ]