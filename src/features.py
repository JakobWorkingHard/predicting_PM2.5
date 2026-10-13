import numpy as np
import pandas as pd


def add_wind_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Omvandlar vindriktning från grader till sinus och cosinus.

    Vindstilla får vind_sin = 0 och vind_cos = 0,
    eftersom vindriktningen saknar betydelse när vinden står stilla.

    Returnerar en kopia av DataFrame med de nya kolumnerna.
    """

    df = df.copy()

    # Omvandla grader till radianer
    radianer = np.deg2rad(df["Vindriktning"])

    # Skapa nya features
    df["vind_sin"] = np.sin(radianer)
    df["vind_cos"] = np.cos(radianer)

    # Vindstilla saknar meningsfull vindriktning
    vindstilla = df["Vindhastighet"] == 0
    df.loc[vindstilla, ["vind_sin", "vind_cos"]] = 0.0

    return df