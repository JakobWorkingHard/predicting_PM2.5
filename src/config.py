from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ProjectConfig:
    # Mappar
    raw_dir: Path
    merged_dir: Path
    validated_dir: Path
    processed_dir: Path
    models_dir: Path
    champion_log: Path

    # Fullständiga sökvägar till specifika filer
    train_pm25: Path
    train_vader: Path
    train_merged: Path
    train_vader_forskjuten: Path
    train_merged_forskjuten: Path
    train_validated: Path
    train_processed: Path

    # Valideringsdata
    val_pm25: Path
    val_vader: Path
    val_merged: Path
    val_validated: Path
    val_processed: Path

    # API:er
    luft_api: str
    vader_api: str

    # Modell
    horisont: int
    features: list
    selection_metric: str
    random_state: int
    target_column: str
    antal_dagar_sedan: int

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
    validated_dir = PATH_PROJECT_ROOT / p["validated_dir"]                      
    processed_dir = PATH_PROJECT_ROOT / p["processed_dir"]
    models_dir=PATH_PROJECT_ROOT / p["models_dir"]
    champion_log = PATH_PROJECT_ROOT / p["champion_log"]

    # Råvärden
    pm25_station = pm25["namn"]
    vaderstation = vader["namn"]
    train_start = t["train_start"]
    train_slut = t["train_slut"]
    pm25_tidsserie_id = pm25["tidsserie_id"]
    vaderstation_id = vader["id"]
    validering_start = t["validering_start"]
    validering_slut = t["validering_slut"]  
    

    # Värden för filnamnsmallar (stationsnamn sanerade, övriga oförändrade)
    fmt = {
        "pm25_station": pm25_station.replace(" ", "_"),
        "vaderstation": vaderstation.replace(" ", "_"),
        "train_start": train_start,
        "train_slut": train_slut,
        "pm25_tidsserie_id": pm25_tidsserie_id,
        "vaderstation_id": vaderstation_id,
        "horisont": mod["horisont"],
        "validering_start": validering_start,
        "validering_slut": validering_slut,
    }

    return ProjectConfig(
        # Mappar
        raw_dir=raw_dir,
        merged_dir=merged_dir,
        validated_dir=validated_dir,
        processed_dir=processed_dir,
        models_dir = models_dir,
        champion_log=champion_log,

        # Fullständiga sökvägar till träningsdata
        train_pm25=raw_dir / fn["train_pm25"].format(**fmt),
        train_vader=raw_dir / fn["train_vader"].format(**fmt),
        train_merged=merged_dir / fn["train_merged"].format(**fmt),
        train_vader_forskjuten=raw_dir / fn["train_vader_forskjuten"].format(**fmt),
        train_merged_forskjuten=merged_dir / fn["train_merged_forskjuten"].format(**fmt),
        train_validated=validated_dir / fn["train_validated"].format(**fmt),
        train_processed=processed_dir / fn["train_processed"].format(**fmt),

        # Fullständiga sökvägar till valideringsdata
        val_pm25=raw_dir / fn["val_pm25"].format(**fmt),
        val_vader=raw_dir / fn["val_vader"].format(**fmt),
        val_merged=merged_dir / fn["val_merged"].format(**fmt),
        val_validated=validated_dir / fn["val_validated"].format(**fmt),
        val_processed=processed_dir / fn["val_processed"].format(**fmt),

        # API:er
        luft_api=api["luft"],
        vader_api=api["vader"],

        # Modell
        horisont=mod["horisont"],
        features=mod["features"]["columns"],
        selection_metric=mod["selection_metric"],
        random_state=mod["random_state"],
        target_column=mod["target_column"],
        antal_dagar_sedan=mod["antal_dagar_sedan"],

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
