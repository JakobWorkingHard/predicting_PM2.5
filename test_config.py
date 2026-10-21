from pathlib import Path

from src.config import load_config

ROOT = Path(__file__).resolve().parent

cfg = load_config(ROOT / "config.toml", ROOT)

print("\nTräningsperiod:")
print(cfg.train_start, "till", cfg.train_slut)

print("\nValideringsperiod:")
print(cfg.validering_start, "till", cfg.validering_slut)

print("\nExempel på filvägar:")
print(cfg.train_pm25)
print(cfg.val_pm25)