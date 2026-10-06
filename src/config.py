from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ProjectConfig:
    # Mappar
    raw_dir: Path
    merged_dir: Path
    processed_dir: Path

    # Fullständiga sökvägar till specifika filer
    train_pm25: Path
    train_vader: Path
    train_merged: Path
    train_vader_forskjuten: Path
    train_merged_forskjuten: Path

    # API:er
    luft_api: str
    vader_api: str

    # Modell
    horisont: int

    # Tidsperioder
    train_start: str
    train_slut: str
    validering_start: str
    validering_slut: str
    test_start: str

    # PM2.5 Station
    pm25_station: str
    pm25_tidsserie_id: int
    pm25_lat: float
    pm25_lon: float

    # Väderstation
    vaderstation: str
    vaderstation_id: int
    vader_lat: float
    vader_lon: float
    vader_parametrar: dict

def load_config(PATH_CONFIG_TOML: Path, PATH_PROJECT_ROOT: Path ) -> ProjectConfig:
    with open(PATH_CONFIG_TOML, "rb") as f:
        raw = tomllib.load(f)

    p = raw["paths"]
    fn = raw["paths"]["filenames"]
    api = raw["api"]
    mod = raw["model"]
    t = raw["time"]
    pm25 = raw["station"]["pm25"]
    vader = raw["station"]["vader"]

    # Baskataloger
    raw_dir = PATH_PROJECT_ROOT / p["raw_dir"]
    merged_dir = PATH_PROJECT_ROOT / p["merged_dir"]
    processed_dir = PATH_PROJECT_ROOT / p["processed_dir"]

    # Råvärden
    pm25_station = pm25["namn"]
    vaderstation = vader["namn"]
    train_start = t["train_start"]
    train_slut = t["train_slut"]
    pm25_tidsserie_id = pm25["tidsserie_id"]
    vaderstation_id = vader["id"]

    # Värden för filnamnsmallar (stationsnamn sanerade, övriga oförändrade)
    fmt = {
        "pm25_station": pm25_station.replace(" ", "_"),
        "vaderstation": vaderstation.replace(" ", "_"),
        "train_start": train_start,
        "train_slut": train_slut,
        "pm25_tidsserie_id": pm25_tidsserie_id,
        "vaderstation_id": vaderstation_id,
        "horisont": mod["horisont"],
    }

    return ProjectConfig(
        # Mappar
        raw_dir=raw_dir,
        merged_dir=merged_dir,
        processed_dir=processed_dir,

        # Fullständiga sökvägar (mall + baskatalog)
        train_pm25=raw_dir / fn["train_pm25"].format(**fmt),
        train_vader=raw_dir / fn["train_vader"].format(**fmt),
        train_merged=merged_dir / fn["train_merged"].format(**fmt),
        train_vader_forskjuten=raw_dir / fn["train_vader_forskjuten"].format(**fmt),
        train_merged_forskjuten=merged_dir / fn["train_merged_forskjuten"].format(**fmt),

        # API:er
        luft_api=api["luft"],
        vader_api=api["vader"],

        # Modell
        horisont=mod["horisont"],

        # Tidsperioder
        train_start=train_start,
        train_slut=train_slut,
        validering_start=t["validering_start"],
        validering_slut=t["validering_slut"],
        test_start=t["test_start"],

        # PM2.5 Station
        pm25_station=pm25_station,
        pm25_tidsserie_id=pm25_tidsserie_id,
        pm25_lat=pm25["lat"],
        pm25_lon=pm25["lon"],

        # Väderstation
        vaderstation=vaderstation,
        vaderstation_id=vaderstation_id,
        vader_lat=vader["lat"],
        vader_lon=vader["lon"],
        vader_parametrar=vader["parametrar"],
    )
