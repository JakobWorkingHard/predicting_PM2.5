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