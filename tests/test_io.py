"""Tester för src/io.py: champion-färskhet per linje/horisont och champion-inläsning."""

from datetime import datetime, timedelta

import joblib
import pandas as pd

from src.io import champion_is_fresh, hamta_champion_modell


SUFFIX = " vanlig (T+6)"


def _skriv_championlogg(path, rader):
    pd.DataFrame(rader).to_csv(path, index=False)


def test_champion_is_fresh_saknad_fil(tmp_path):
    """Fail-safe: ingen logg -> False -> full träning tvingas fram."""
    assert champion_is_fresh(tmp_path / "finns_inte.csv", 7, SUFFIX) is False


def test_champion_is_fresh_med_matchande_suffix(tmp_path):
    logg = tmp_path / "champion.csv"
    _skriv_championlogg(logg, [
        {"modell": "SVR vanlig (T+6)",
         "timestamp": (datetime.now() - timedelta(days=1)).isoformat()},
    ])
    assert champion_is_fresh(logg, 7, SUFFIX) is True


def test_champion_is_fresh_ignorerar_annan_horisont(tmp_path):
    """Rader från en annan horisont håller inte träningen tillbaka."""
    logg = tmp_path / "champion.csv"
    _skriv_championlogg(logg, [
        {"modell": "SVR vanlig (T+1)", "timestamp": datetime.now().isoformat()},
    ])
    assert champion_is_fresh(logg, 7, SUFFIX) is False


def test_champion_is_fresh_ignorerar_forskjuten_linje(tmp_path):
    """En färsk forskjuten-champion håller inte vanlig-linjen tillbaka.

    Linjerna delar horisontsiffra men skiljer sig på etiketten i
    suffixet. Matchningen är endswith, så " vanlig (T+6)" får aldrig
    träffa "SVR forskjuten (T+6)" — inte ens om loggarna blandas.
    """
    logg = tmp_path / "champion.csv"
    _skriv_championlogg(logg, [
        {"modell": "SVR forskjuten (T+6)", "timestamp": datetime.now().isoformat()},
    ])
    assert champion_is_fresh(logg, 7, SUFFIX) is False


def test_champion_is_fresh_baseline_med_suffix_raknas(tmp_path):
    """Baseline loggas med suffix — en baseline-vinst räknas som färsk,
    så att linjen inte tränas om vid varje körning."""
    logg = tmp_path / "champion.csv"
    _skriv_championlogg(logg, [
        {"modell": f"Persistence Baseline{SUFFIX}",
         "timestamp": datetime.now().isoformat()},
    ])
    assert champion_is_fresh(logg, 7, SUFFIX) is True


def test_champion_is_fresh_gammal_champion(tmp_path):
    logg = tmp_path / "champion.csv"
    _skriv_championlogg(logg, [
        {"modell": "SVR vanlig (T+6)",
         "timestamp": (datetime.now() - timedelta(days=10)).isoformat()},
    ])
    assert champion_is_fresh(logg, 7, SUFFIX) is False


def test_hamta_champion_modell_hittar_suffixerad_champion(tmp_path):
    """Suffixerade namn fungerar hela vägen: logg-filter -> filglob ->
    inläsning. Baseline-raden (senast loggad) ska uteslutas via prefix,
    och forskjuten-filer ska aldrig plockas upp som vanlig-champion."""
    logg = tmp_path / "champion_vanlig.csv"
    _skriv_championlogg(logg, [
        {"modell": "SVR vanlig (T+6)",
         "timestamp": (datetime.now() - timedelta(days=2)).isoformat()},
        {"modell": f"Persistence Baseline{SUFFIX}",
         "timestamp": datetime.now().isoformat()},
    ])

    modeller = tmp_path / "models"
    modeller.mkdir()
    joblib.dump("dummy", modeller / "svr_vanlig_(t+6)_Validation_R2_2026_10_21_10-00.joblib")
    # Forskjuten-linjens filer delar horisont men ska aldrig läsas in
    # för vanlig-championen.
    joblib.dump(
        "forskjuten-dummy",
        modeller / "forskjuten_svr_forskjuten_(t+6)_Validation_R2_2026_10_21_11-00.joblib",
    )

    modell, namn = hamta_champion_modell(modeller, logg)

    assert namn == "SVR vanlig (T+6)"   # baseline-raden är senast men utesluten
    assert modell == "dummy"
