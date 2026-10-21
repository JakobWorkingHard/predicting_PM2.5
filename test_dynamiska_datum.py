import pandas as pd

from src.config import berakna_tranings_och_valideringsperiod


senaste_arkivtid = pd.Timestamp("2026-07-01 08:00:00", tz="Europe/Stockholm")

perioder = berakna_tranings_och_valideringsperiod(
    senaste_arkivtid=senaste_arkivtid,
    train_start="2023-05-26",
)

for namn, datum in perioder.items():
    print(f"{namn}: {datum}")