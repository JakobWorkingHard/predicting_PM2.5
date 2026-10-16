import pandas as pd

from src.logger import setup_logger

log = setup_logger(__name__)

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

    # Vindhastighet kan inte vara negativ
    df.loc[df["Vindhastighet"] < 0, "Vindhastighet"] = pd.NA

    # Relativ luftfuktighet ska ligga mellan 0 och 100 %
    df.loc[
        (df["Relativ luftfuktighet"] < 0)
        | (df["Relativ luftfuktighet"] > 100),
        "Relativ luftfuktighet"
    ] = pd.NA

    # Nederbördsmängd kan inte vara negativ
    df.loc[
        df["Nederbördsmängd"] < 0,
        "Nederbördsmängd"
    ] = pd.NA

    # I SMHI:s data betyder 0° vindstilla och 360° nord.
    # För sin/cos är 0° och 360° samma vinkel, så 360° sätts till 0°.
    # Vindstilla hanteras i add_wind_features (Vindhastighet == 0).
    df.loc[
        df["Vindriktning"] == 360,
        "Vindriktning"
    ] = 0.0

    # Övriga värden utanför intervallet 0–360° är ogiltiga
    df.loc[
        (df["Vindriktning"] < 0)
        | (df["Vindriktning"] > 360),
        "Vindriktning"
    ] = pd.NA

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