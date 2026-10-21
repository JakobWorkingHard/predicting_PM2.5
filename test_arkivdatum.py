from pathlib import Path
import tomllib

from src.extracting_data import hamta_senaste_arkivtid

ROOT = Path(__file__).resolve().parent

# Läs in konfigurationen direkt
with open(ROOT / "config.toml", "rb") as f:
    config = tomllib.load(f)

vader = config["station"]["vader"]
api = config["api"]

senaste_tid = hamta_senaste_arkivtid(
    parametrar=vader["parametrar"],
    station_id=vader["id"],
    VADER_API=api["vader"],
)

print(f"\nSenaste gemensamma arkivgräns: {senaste_tid}")