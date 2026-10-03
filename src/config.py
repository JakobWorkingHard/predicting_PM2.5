from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class ProjectConfig:
    # Mappar
    raw_dir: Path
    processed_dir: Path
    
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
    api = raw["api"]
    mod = raw["model"]
    t = raw["time"]
    pm25 = raw["station"]["pm25"]
    vader = raw["station"]["vader"]
    
    return ProjectConfig(
        # Konvertera textsträngar till Path-objekt baserat på projektets rot
        raw_dir=PATH_PROJECT_ROOT / p["raw_dir"],
        processed_dir=PATH_PROJECT_ROOT/ p["processed_dir"],
        
        luft_api=api["luft"],
        vader_api=api["vader"],
        
        horisont=mod["horisont"],
        
        train_start=t["train_start"],
        train_slut=t["train_slut"],
        validering_start=t["validering_start"],
        validering_slut=t["validering_slut"],
        test_start=t["test_start"],
        
        pm25_station=pm25["namn"],
        pm25_tidsserie_id=pm25["tidsserie_id"],
        pm25_lat=pm25["lat"],
        pm25_lon=pm25["lon"],
        
        vaderstation=vader["namn"],
        vaderstation_id=vader["id"],
        vader_lat=vader["lat"],
        vader_lon=vader["lon"],
        vader_parametrar = vader["parametrar"]
    )
