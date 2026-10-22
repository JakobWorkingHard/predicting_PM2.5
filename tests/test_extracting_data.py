"""Tester för src/extracting_data.py."""

import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.extracting_data import hamta_senaste_pm25


def _cfg(tmp_path):
    """Minimal config med bara de fält som hamta_senaste_pm25 använder."""
    return SimpleNamespace(
        prognos_dir=tmp_path / "prognoser",
        pm25_tidsserie_id=123,
        luft_api="https://example.test/luft",
    )


def _fake_pm25(n=3):
    """Liten pm25-dataframe i samma format som hamta_pm25 returnerar."""
    tid = pd.date_range(pd.Timestamp.now(tz="Europe/Stockholm"), periods=n, freq="h")
    return pd.DataFrame({"pm25": [5.0, 6.0, 7.0][:n]}, index=tid).rename_axis("tid")


def test_hamta_senaste_pm25_fyller_arkiv_och_tvingar_fram_ny_data(tmp_path):
    """Wrapperns två verkliga beteenden:

    1) csv_path får INTE finnas när hamta_pm25 anropas — annars returnerar
       den cachad data och live-prediktionen bygger på gamla mätvärden.
    2) Hämtningen sparas i prognos_dir/pm25/ (hamta_pm25 skriver aldrig
       csv_path själv, så arkivet fylls annars aldrig).
    """

    def fake_hamta_pm25(start, slut, tidsserie_id, luft_api, csv_path):
        # Härma riktiga hamta_pm25:s första rad: finns filen -> returnera cache.
        assert not Path(str(csv_path)).is_file(), (
            f"csv_path {csv_path} fanns redan — den timestampade sökvägen "
            "måste vara unik för att tvinga fram ny data"
        )
        return _fake_pm25()

    cfg = _cfg(tmp_path)

    with patch("src.extracting_data.hamta_pm25", side_effect=fake_hamta_pm25):
        hamta_senaste_pm25(cfg)

    # Arkivet fylls: exakt en sparad hämtning på rätt ställe
    sparade = list((cfg.prognos_dir / "pm25").glob("pm25_*.csv"))
    assert len(sparade) == 1
