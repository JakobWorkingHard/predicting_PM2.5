import numpy as np
import pandas as pd

from src.champion import compete_with_champion


class DummyModel:
    def __init__(self, predictions):
        self.predictions = np.array(predictions)

    def predict(self, X):
        return self.predictions


def test_champion_selection_with_mae(tmp_path):
    test_df = pd.DataFrame({
        "pm25": [10, 20, 30],
        "target": [12, 22, 32],
    })

    test_path = tmp_path / "test.csv"
    test_df.to_csv(test_path, index=False)

    new_model = DummyModel([12, 22, 32])  # MAE = 0
    old_model = DummyModel([10, 20, 30])  # MAE = 2

    winner, results_df = compete_with_champion(
        new_model=new_model,
        new_name="New",
        old_model=old_model,
        old_name="Old",
        test_path=test_path,
        features=["pm25"],
        target="target",
        metric="Validation MAE",
    )

    assert winner == "new"
    assert results_df.iloc[0]["MAE"] == 0
    assert results_df.iloc[1]["MAE"] == 2