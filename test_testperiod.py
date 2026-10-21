from pathlib import Path
import tomllib

from src.extracting_data import hamta_testperiod

ROOT = Path(__file__).resolve().parent

with open(ROOT / "config.toml", "rb") as f:
    config = tomllib.load(f)

vader = config["station"]["vader"]
api = config["api"]

validering_slut = "2026-06-30"

test_start, test_slut = hamta_testperiod(
    station_id=vader["id"],
    VADER_API=api["vader"],
    validering_slut=validering_slut,
)

print(f"Validering slutar: {validering_slut}")
print(f"Test startar:      {test_start}")
print(f"Test slutar:       {test_slut}")

from src.extracting_data import hamta_test_vader

test_vader = hamta_test_vader(
    parametrar=vader["parametrar"],
    test_start=test_start,
    test_slut=test_slut,
    station_id=vader["id"],
    VADER_API=api["vader"],
)

print("\nTestdata:")
print(f"Antal rader: {len(test_vader)}")
print(f"Första mätning: {test_vader.index.min()}")
print(f"Sista mätning: {test_vader.index.max()}")

print("\nAntal saknade värden per parameter:")
print(test_vader.isna().sum())



print("\nAntal saknade värden per månad:")

print(
    test_vader["Nederbördsmängd"]
    .isna()
    .resample("ME")
    .sum()
)

# Undersök de saknade nederbördsvärdena
saknade = test_vader.loc[
    test_vader["Nederbördsmängd"].isna()
]

print("\nSaknade nederbördsvärden:")
print(f"Antal: {len(saknade)}")
print(f"Första tidpunkt: {saknade.index.min()}")
print(f"Sista tidpunkt: {saknade.index.max()}")

print("\nExempel på rader med saknad nederbörd:")
print(saknade.head(10))