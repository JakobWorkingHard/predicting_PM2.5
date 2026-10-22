
from pathlib import Path
import pandas as pd

from src.train_models import (
    load_train_val_data,
    build_model_registry,
    train_and_evaluate_models,
    persistence_baseline,
)
from src.champion import load_latest_champion, compete_with_champion
from src.metrics import build_comparison_table, select_best_model

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data" / "processed"

TRAIN = PROCESSED / "train_processed_2023-05-26_2025-12-31.csv"
VAL = PROCESSED / "val_processed_2026-01-01_2026-06-30.csv"
TEST = PROCESSED / "test_processed_2026-07-01_2026-10-22.csv"

FEATURES = [
    "pm25",
    "Lufttemperatur",
    "vind_sin",
    "vind_cos",
    "Vindhastighet",
    "Relativ luftfuktighet",
    "Nederbördsmängd",
    "timme_sin",
    "timme_cos",
    "helg",
    "helg_timme_sin",
    "helg_timme_cos",
]
TARGET = "target"

print("Läser tränings- och valideringsdata...", flush=True)

X_train, y_train, X_val, y_val = load_train_val_data(
    TRAIN, VAL, FEATURES, TARGET
)

# Träna samtliga modeller EN gång
models = build_model_registry(random_state=42)
results_df, trained_models = train_and_evaluate_models(
    models, X_train, y_train, X_val, y_val
)

# Beräkna persistence baseline
_, baseline_val = persistence_baseline(
    X_train, y_train, X_val, y_val
)

# Hämta befintlig champion
old_model, old_name, _ = load_latest_champion(
    ROOT / "logs" / "champion_vanlig.csv",
    ROOT / "models",
)

if old_model is None:
    raise RuntimeError("Kunde inte läsa in befintlig champion.")

print(f"\nBefintlig champion: {old_name}")

sammanfattning = []

for metric in ["Validation MAE", "Validation R²"]:
    print(f"\n{'=' * 55}")
    print(f"URVAL ENLIGT {metric}")
    print("=" * 55)

    comparison_df = build_comparison_table(
        results_df, baseline_val, metric
    )

    best_name, best_row = select_best_model(
        comparison_df, metric=metric
    )

    print(f"Bästa kandidat: {best_name}")
    print(f"Valideringsresultat: {best_row[metric]:.4f}")

    if best_name == "Persistence Baseline":
        print("Baseline vann valideringen.")
        print("Ingen champion-tävling enligt nuvarande pipeline.")
        sammanfattning.append({
            "Urvalsmått": metric,
            "Kandidat": best_name,
            "Champion-vinnare": "Ingen tävling",
        })
        continue

    winner, test_results = compete_with_champion(
        new_model=trained_models[best_name],
        new_name=best_name,
        old_model=old_model,
        old_name=old_name,
        test_path=TEST,
        features=FEATURES,
        target=TARGET,
        metric=metric,
    )

    print("\nResultat på testdata:")
    if test_results is not None:
        print(test_results.to_string(index=False))

    final_winner = best_name if winner == "new" else old_name
    print(f"\nChampion enligt {metric}: {final_winner}")

    sammanfattning.append({
        "Urvalsmått": metric,
        "Kandidat": best_name,
        "Champion-vinnare": final_winner,
    })

print("\n" + "=" * 55)
print("SLUTLIG JÄMFÖRELSE")
print("=" * 55)
print(pd.DataFrame(sammanfattning).to_string(index=False))

print("\nKlart! Inga modeller eller championloggar har ändrats.")
