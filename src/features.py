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


def add_time_features(df: pd.DataFrame, horisont: int = 6) -> pd.DataFrame:
    """
    Lägger till timme på dygnet och helg för måltiden,
    alltså den tidpunkt som prognosen gäller (tid + horisont).

    Skapar fem nya kolumner:
      timme_sin, timme_cos              timmen som sinus och cosinus
      helg                              1 = lördag eller söndag, 0 = vardag
      helg_timme_sin, helg_timme_cos    timmen på helger, 0 på vardagar

    Alla kolumner får ett värde på varje rad. Vardagar får 0,
    inte ett tomt värde, så inga rader tas bort av dropna.

    Timmen omvandlas till sinus och cosinus, så att kl. 23 och kl. 00
    hamnar nära varandra. Timmen räknas i svensk tid, eftersom
    trafiken följer den lokala klockan.

    Interaktionstermerna gör att linjär regression kan ge helgen
    en egen dygnskurva, till exempel en senare morgontopp.

    Returnerar en kopia av DataFrame med de nya kolumnerna.
    """

    df = df.copy()

    # Tidpunkten som prognosen gäller
    tid = pd.to_datetime(df["tid"], utc=True).dt.tz_convert("Europe/Stockholm")
    maltid = tid + pd.Timedelta(hours=horisont)

    # Timme på dygnet som sinus och cosinus
    timme = maltid.dt.hour
    df["timme_sin"] = np.sin(2 * np.pi * timme / 24)
    df["timme_cos"] = np.cos(2 * np.pi * timme / 24)

    # Helg: lördag och söndag = 1, vardag = 0
    df["helg"] = (maltid.dt.dayofweek >= 5).astype(int)

    # Interaktionstermer mellan helg och timme
    df["helg_timme_sin"] = df["helg"] * df["timme_sin"]
    df["helg_timme_cos"] = df["helg"] * df["timme_cos"]

    return df