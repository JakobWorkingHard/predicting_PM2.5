import numpy as np
import pandas as pd




# 1. Jakob, flytta add_time_features nedan till features.py


# Vi har sett att tid på dygnet påverkar PM2.5 med en peak kring kl 08 på vardagar
# och en peak på kring kl 10 på helger. Vi vill därför skapa en feature som fångar detta mönster.
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

# jag använde testet nedan för att kolla att det stämmer, men det behöver du inte ha med i features.py
if __name__ == "__main__":
    test = pd.DataFrame({
        "tid": pd.to_datetime([
            "2026-10-14 02:00",   # onsdag  -> måltid onsdag 08:00
            "2026-10-16 20:00",   # fredag  -> måltid lördag 02:00
            "2026-10-18 20:00",   # söndag  -> måltid måndag 02:00
        ]).tz_localize("Europe/Stockholm")
    })
    print(add_time_features(test, horisont=6))


# 2. Anropa add_time_features där vi bygger datasetet
# Funktionen kräver att df har en kolumn som heter "tid".
# Den kolumnen finns efter validate_data, så add_time_features måste
# anropas EFTER validate_data.
#
# Ordningen ska vara:
#   1. validate_data
#   2. add_wind_features
#   3. add_time_features   <- ny
#   4. skapa target med shift(-cfg.horisont)
#   5. dropna
#
# Den ska köras på både train- och valideringsdatan:
#
#   df = add_time_features(df, horisont=cfg.horisont)
#
# Använd cfg.horisont och skriv inte 6 direkt. Då pekar tidsfeaturen och
# target alltid på samma timme, även om vi ändrar horisonten i config.toml



# 3. Lägg till de nya kolumnerna i features-listan
# add_time_features skapar kolumnerna, men modellen använder dem bara
# om de finns med i listan över features:
#
#   features = [
#       "pm25",
#       "Lufttemperatur",
#       "vind_sin",
#       "vind_cos",
#       "Vindhastighet",
#       "Relativ luftfuktighet",
#       "Nederbördsmängd",
#       "timme_sin",        # ny
#       "timme_cos",        # ny
#       "helg",             # ny
#       "helg_timme_sin",   # ny
#       "helg_timme_cos",   # ny
#   ]
#
# features-listan definieras just nu på två ställen i model_trainval.ipynb.
# Se till att den bara finns på ett ställe när du flyttar koden, så att
# vi inte råkar ändra den ena men inte den andra.


# 4. Kör alla modeller igen, inklusive baslinjen, och kontrollera resultaten
#
# Kontroll 1: dropna ska ta bort lika många rader som innan,
# eftersom de nya kolumnerna inte har några saknade värden:
#   train: 21 555 rader efter dropna
#   val:   2 818 rader efter dropna
#
# Kontroll 2: baslinjen ska ge samma resultat som innan (val MAE 3.321).
# Baslinjen gissar att PM2.5 om 6 timmar är samma som nu och använder
# inga features. Om dess resultat ändras har något annat ändrats
# än features, till exempel vilka rader som är med.
#
# Om båda kontrollerna stämmer: jämför de andra modellernas nya resultat
# med de gamla (LR/Ridge hade val MAE 3.210).


