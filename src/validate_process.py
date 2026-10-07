import numpy as np
import pandas as pd


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

    # Vindriktning ska ligga mellan 0 och 360 grader.
    # 360° och 0° representerar båda nord.
    # Normalisera därför 360° till 0°.
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


def check_missing_values(df: pd.DataFrame) -> pd.Series:
    """Returnerar antal saknade värden per kolumn."""
    
    return df.isna().sum()


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


def interpolate_short_gaps(
    df: pd.DataFrame,
    column: str,
    max_gap: int = 3
) -> pd.DataFrame:
    """Interpolerar linjärt endast luckor som är högst max_gap timmar."""

    df = df.copy()

    # Hitta alla sammanhängande NaN-luckor
    gaps = find_nan_gaps(df, column)

    # Skapa interpolerade värden för hela kolumnen
    interpolated = df[column].interpolate(
        method="linear",
        limit_area="inside"
    )

    # Använd de interpolerade värdena endast i korta luckor
    for _, gap in gaps.iterrows():
        if gap["hours"] <= max_gap:

            mask = (
                (df["tid"] >= gap["start"])
                & (df["tid"] <= gap["end"])
            )

            df.loc[mask, column] = interpolated.loc[mask]

    return df


def interpolate_wind_direction(
    df: pd.DataFrame,
    column: str = "Vindriktning",
    max_gap: int = 3
) -> pd.DataFrame:
    """Interpolerar korta luckor i vindriktning cirkulärt."""

    df = df.copy()

    # Hitta sammanhängande NaN-luckor
    gaps = find_nan_gaps(df, column)

    # Omvandla grader till radianer
    radians = np.deg2rad(df[column])

    # Representera vindriktningen med x- och y-komponenter
    x = np.cos(radians)
    y = np.sin(radians)

    # Interpolera komponenterna
    x_interpolated = x.interpolate(method="linear", limit_area="inside")
    y_interpolated = y.interpolate(method="linear", limit_area="inside")

    # Omvandla tillbaka till grader
    interpolated_direction = (
        np.rad2deg(
            np.arctan2(y_interpolated, x_interpolated)
        ) % 360
    )

    # Hantera flyttalsavrundning nära 360° så att nord representeras som 0°
    interpolated_direction = interpolated_direction.mask(
        np.isclose(interpolated_direction, 360.0),
        0.0
    )



    # Fyll endast luckor som är högst max_gap timmar
    for _, gap in gaps.iterrows():
        if gap["hours"] <= max_gap:

            mask = (
                (df["tid"] >= gap["start"])
                & (df["tid"] <= gap["end"])
            )

            df.loc[mask, column] = interpolated_direction.loc[mask]

    return df


def fill_short_rain_gaps(
    df: pd.DataFrame,
    column: str = "Nederbördsmängd",
    max_gap: int = 3
) -> pd.DataFrame:
    """Fyller korta nederbördsluckor med 0 om det är 0 före och efter."""

    df = df.copy()

    gaps = find_nan_gaps(df, column)

    for _, gap in gaps.iterrows():

        if gap["hours"] <= max_gap:

            before = df.loc[
                df["tid"] < gap["start"],
                column
            ]

            after = df.loc[
                df["tid"] > gap["end"],
                column
            ]

            # Luckan måste ha ett värde både före och efter
            if before.empty or after.empty:
                continue

            before_value = before.iloc[-1]
            after_value = after.iloc[0]

            # Fyll endast om det är 0 både före och efter luckan
            if before_value == 0 and after_value == 0:

                mask = (
                    (df["tid"] >= gap["start"])
                    & (df["tid"] <= gap["end"])
                )

                df.loc[mask, column] = 0.0

    return df


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    """Preprocessar data inför vidare analys och modellering."""

    df = convert_datetime(df)
    df = sort_by_time(df)

    # Tidsstämplarna måste vara unika innan en komplett timaxel skapas
    check_duplicates(df)

    df = ensure_complete_timeline(df)

    # Uppenbart ogiltiga mätvärden behandlas som saknade värden
    df = replace_invalid_values(df)

    # Linjär interpolation av korta luckor
    linear_columns = [
        "pm25",
        "Lufttemperatur",
        "Vindhastighet",
        "Relativ luftfuktighet",
    ]

    for column in linear_columns:
        df = interpolate_short_gaps(df, column)

    # Variabelspecifik hantering
    df = interpolate_wind_direction(df)
    df = fill_short_rain_gaps(df)


    return df

if __name__ == "__main__":
    from pathlib import Path
    from src.config import load_config

    projekt_rot = Path(__file__).resolve().parent.parent
    cfg = load_config(projekt_rot / "config.toml", projekt_rot)

    df = pd.read_csv(cfg.train_merged)

    print("Fil:", cfg.train_merged.name)
    print("Shape:", df.shape)
    print(df.head())
    df = convert_datetime(df)
    df = sort_by_time(df)

    print("\nDatatyp för tid:")
    print(df["tid"].dtype)

    print("\nÄr tiden sorterad?")
    print(df["tid"].is_monotonic_increasing)

    print("\nKontrollerar dubbletter:")
    #check_duplicates(df)

    print("\nSaknade värden:")
    print(check_missing_values(df))

    print("\nLuckor:")
    print(find_nan_gaps(df, "pm25"))