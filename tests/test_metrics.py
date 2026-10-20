import pytest
import pandas as pd

from types import SimpleNamespace

from src.metrics import evaluate_model, build_comparison_table, select_best_model, jamfor_championer


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


def test_jamfor_championer_med_high_pm25(tmp_path, monkeypatch):

    class DummyModel:
        def predict(self, X):
            return X["pm25"].to_numpy() + 2

    # Två testfiler med samma tidpunkter
    df = pd.DataFrame({
        "tid": ["2026-06-01 00:00", "2026-06-01 01:00",
                "2026-06-01 02:00"],
        "pm25": [10, 30, 50],
        "target": [12, 32, 52],
    })

    vanlig_path = tmp_path / "vanlig.csv"
    forskjuten_path = tmp_path / "forskjuten.csv"

    df.to_csv(vanlig_path, index=False)
    df.to_csv(forskjuten_path, index=False)

    cfg = SimpleNamespace(
        features=["pm25"],
        target_column="target",
        jamfordelse_log=tmp_path / "jamfordelse.csv",
    )

    # Fånga resultatet utan att skriva någon riktig logg
    sparade_resultat = []

    monkeypatch.setattr(
        "src.metrics.append_jamfordelse_log",
        lambda path, df: sparade_resultat.append(df.copy()),
    )

    jamfor_championer(
        cfg=cfg,
        champion_modell=DummyModel(),
        champion_namn="Champion",
        forskjuten_modell=DummyModel(),
        forskjuten_namn="Förskjuten",
        test_path_vanlig=vanlig_path,
        test_path_forskjuten=forskjuten_path,
        high_pm25_threshold=40,
    )

    assert len(sparade_resultat) == 1

    resultat = sparade_resultat[0]

    # Tre modeller ska jämföras
    assert len(resultat) == 3

    # Kontrollera att de nya måtten finns
    assert "Bias" in resultat.columns
    assert "High PM2.5 MAE" in resultat.columns
    assert "High PM2.5 Bias" in resultat.columns
    assert "High PM2.5 Count" in resultat.columns

    # Bara ett faktiskt PM2.5-värde är >= 40
    assert (resultat["High PM2.5 Count"] == 1).all()

    # Persistence baseline underskattar med 2
    baseline = resultat.loc[
        resultat["Modell"] == "Persistence Baseline"
    ].iloc[0]

    assert baseline["Bias"] == pytest.approx(-2.0)
    assert baseline["High PM2.5 MAE"] == pytest.approx(2.0)
    assert baseline["High PM2.5 Bias"] == pytest.approx(-2.0)


def test_jamfor_championer_utan_threshold(tmp_path, monkeypatch):

    class DummyModel:
        def predict(self, X):
            return X["pm25"].to_numpy() + 2

    df = pd.DataFrame({
        "tid": ["2026-06-01 00:00", "2026-06-01 01:00"],
        "pm25": [10, 30],
        "target": [12, 32],
    })

    vanlig_path = tmp_path / "vanlig.csv"
    forskjuten_path = tmp_path / "forskjuten.csv"

    df.to_csv(vanlig_path, index=False)
    df.to_csv(forskjuten_path, index=False)

    cfg = SimpleNamespace(
        features=["pm25"],
        target_column="target",
        jamfordelse_log=tmp_path / "jamfordelse.csv",
    )

    sparade_resultat = []

    monkeypatch.setattr(
        "src.metrics.append_jamfordelse_log",
        lambda path, df: sparade_resultat.append(df.copy()),
    )

    # Observera att high_pm25_threshold INTE skickas med
    jamfor_championer(
        cfg=cfg,
        champion_modell=DummyModel(),
        champion_namn="Champion",
        forskjuten_modell=DummyModel(),
        forskjuten_namn="Förskjuten",
        test_path_vanlig=vanlig_path,
        test_path_forskjuten=forskjuten_path,
    )

    assert len(sparade_resultat) == 1

    resultat = sparade_resultat[0]

    assert len(resultat) == 3

    # Grundläggande mått ska finnas
    assert "MAE" in resultat.columns
    assert "RMSE" in resultat.columns
    assert "R2" in resultat.columns
    assert "Bias" in resultat.columns

    # Specialiserade mått kräver ett gränsvärde
    assert "High PM2.5 MAE" not in resultat.columns
    assert "High PM2.5 Bias" not in resultat.columns
    assert "High PM2.5 Count" not in resultat.columns