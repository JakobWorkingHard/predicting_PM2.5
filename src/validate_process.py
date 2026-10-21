import pandas as pd

from src.logger import setup_logger

log = setup_logger(__name__)

# Gemensam källa för giltighetsintervall i väderdata (Lufttemperatur saknar
# regel, precis som i huvudpipelinens replace_invalid_values). Missbrukas
# av både tabellversionen (replace_invalid_values) och singelradsversionen
# (sanity_kolla_vader) i live-flödet.
VADER_INTERVALL = {
    "Vindriktning": (0, 360),
    "Vindhastighet": (0, None),
    "Relativ luftfuktighet": (0, 100),
    "Nederbördsmängd": (0, None),
}

def convert_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """Konverterar kolumnen 'tid' till svensk timezone-aware datetime."""
    
    df = df.copy()

    df["tid"] = (
        pd.to_datetime(df["tid"], utc=True)
        .dt.tz_convert("Europe/Stockholm")
    )

    return df


def sort_by_time(df: pd.DataFrame) -> pd.DataFrame:
    """Sorterar observationerna kronologiskt efter 'tid'."""

    df = df.copy()

    return df.sort_values("tid").reset_index(drop=True)


def check_duplicates(df: pd.DataFrame) -> None:
    """Kontrollerar om det finns dubbla tidsstämplar."""

    duplicates = df["tid"].duplicated().sum()

    if duplicates > 0:
        log.warning(
            "Datasetet innehåller %s dubbla tidsstämplar.",
            duplicates,
        )

        raise ValueError(
            f"Datasetet innehåller {duplicates} dubbla tidsstämplar."
        )


def ensure_complete_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Säkerställer att det finns en rad för varje timme i tidsserien."""

    df = df.copy()

    full_timeline = pd.date_range(
        start=df["tid"].min(),
        end=df["tid"].max(),
        freq="h"
    )

    df = (
        df.set_index("tid")
        .reindex(full_timeline)
        .rename_axis("tid")
        .reset_index()
    )

    return df


def replace_invalid_values(df: pd.DataFrame) -> pd.DataFrame:
    """Ersätter uppenbart ogiltiga mätvärden med NaN."""
    df = df.copy()

    # PM2.5 kan inte vara negativt
    df.loc[df["pm25"] < 0, "pm25"] = pd.NA

    # I SMHI:s data betyder 0° vindstilla och 360° nord.
    # För sin/cos är 0° och 360° samma vinkel, så 360° sätts till 0°.
    # Vindstilla hanteras i add_wind_features (Vindhastighet == 0).
    df.loc[df["Vindriktning"] == 360, "Vindriktning"] = 0.0

    # Giltighetsintervall per väderkolumn — reglerna lever i VADER_INTERVALL
    for kolumn, (MIN, MAX) in VADER_INTERVALL.items():
        ogiltig = df[kolumn] < MIN
        if MAX is not None:
            ogiltig = ogiltig | (df[kolumn] > MAX)
        df.loc[ogiltig, kolumn] = pd.NA

    return df


def find_nan_gaps(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Hittar sammanhängande perioder med saknade värden i en kolumn."""

    missing = df[column].isna()

    # Varje gång vi går från NaN till icke-NaN eller tvärtom
    # börjar en ny grupp
    groups = missing.ne(missing.shift()).cumsum()

    gaps = (
        df[missing]
        .groupby(groups[missing])
        .agg(
            start=("tid", "first"),
            end=("tid", "last"),
            hours=("tid", "size")
        )
        .reset_index(drop=True)
    )

    return gaps


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Validerar tidsserie och mätvärden utan interpolation."""

    log.info("Startar datavalidering.")

    df = convert_datetime(df)
    df = sort_by_time(df)

    # Kontrollera att tidsstämplarna är unika
    check_duplicates(df)

    # Säkerställ en komplett timaxel
    df = ensure_complete_timeline(df)

    # Ersätt ogiltiga mätvärden med NaN
    df = replace_invalid_values(df)

    log.info(
        "Datavalidering slutförd. Antal rader: %s, antal kolumner: %s.",
        len(df),
        len(df.columns),
    )

    return df


# Används av predict pipeline
def sanity_kolla_vader(rad: pd.Series) -> pd.Series:
    """
    Intervallreglerna för en enskild rad väderdata (live-flödet):
    ogiltigt -> NaN, 360 grader -> 0.

    Exakt samma regler som replace_invalid_values tillämpar på hela
    tabeller — båda bygger på VADER_INTERVALL. `rad` förväntas vara
    en Series med väderkolumnerna; saknade värden (None/NaN) lämnas.
    """
    rad = rad.astype(float).copy()

    if rad["Vindriktning"] == 360:
        rad["Vindriktning"] = 0.0

    for kolumn, (MIN, MAX) in VADER_INTERVALL.items():
        if rad[kolumn] < MIN or (MAX is not None and rad[kolumn] > MAX):
            rad[kolumn] = pd.NA

    return rad