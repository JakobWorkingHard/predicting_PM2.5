"""Tester för src/predict_pipeline.py (live-prediktioner)."""

import pandas as pd

from src.predict_pipeline import bestam_ankarpunkt


def _tim(n, start="2026-10-21 10:00"):
    """Heltimmesindex i svensk tid, samma format som live-hämtningarna."""
    return pd.date_range(start, periods=n, freq="h", tz="Europe/Stockholm")


def test_bestam_ankarpunkt_valjer_senaste_kompletta_timme():
    """T_obs = senaste timme med pm25 och alla vaderparametrar kompletta."""
    tid = _tim(5)  # 10:00–14:00
    pm25 = pd.DataFrame({"pm25": [8.0, 8.1, 8.2, 8.3, 8.4]}, index=tid)
    vader = pd.DataFrame(
        {
            "Lufttemperatur": [5.0, 5.1, None, 5.3, 5.4],  # 12:00 ofullständig
            "Vindriktning": [10.0, 20.0, 30.0, 40.0, 360.0],
            "Vindhastighet": [1.0, 1.1, 1.2, 1.3, 1.4],
            "Relativ luftfuktighet": [70.0, 71.0, 72.0, 73.0, 74.0],
            "Nederbördsmängd": [0.0, 0.1, 0.2, 0.3, 0.4],
        },
        index=tid,
    )

    T_obs = bestam_ankarpunkt(pm25, vader)

    # Senaste KOMPLETTA timmen är 14:00 (12:00 saknar Lufttemperatur).
    # 360° i Vindriktning hindrar inte: ankarpunkten letar kompletthet,
    # inte validitet — 360 -> 0 är sanity_kolla_vaders jobb senare i flödet.
    assert T_obs == pd.Timestamp("2026-10-21 14:00", tz="Europe/Stockholm")


def test_bestam_ankarpunkt_faller_tillbaka_nar_senaste_ar_inkomplett():
    """Är den senaste timmen ofullständig väljs näst senaste kompletta."""
    tid = _tim(3)  # 10:00–12:00
    pm25 = pd.DataFrame({"pm25": [8.0, 8.1, 8.2]}, index=tid)
    vader = pd.DataFrame({"Lufttemperatur": [5.0, 5.1, None]}, index=tid)

    T_obs = bestam_ankarpunkt(pm25, vader)

    assert T_obs == pd.Timestamp("2026-10-21 11:00", tz="Europe/Stockholm")


def test_bestam_ankarpunkt_returnerar_none_om_inget_komplett():
    """Ingen komplett timme -> None (kor_live_prediktion hoppar senare över)."""
    tid = _tim(2)
    # 10:00 saknar pm25, 11:00 saknar Lufttemperatur -> ingen komplett timme
    pm25 = pd.DataFrame({"pm25": [None, 8.2]}, index=tid)
    vader = pd.DataFrame({"Lufttemperatur": [5.0, None]}, index=tid)

    assert bestam_ankarpunkt(pm25, vader) is None


def test_bestam_ankarpunkt_tolererar_duplikata_tidsstampelar():
    """Regression: duplikat i INGÅNGEN måste bort FÖRE concat — annars
    kraschar sammanfogningen ('cannot reindex from a duplicate axis')."""
    tid = _tim(2)
    pm25 = pd.DataFrame(
        {"pm25": [8.0, 8.1, 8.2]},  # keep="last" -> 11:00 får 8.2
        index=[tid[0], tid[1], tid[1]],  # 11:00 duplicerad
    )
    vader = pd.DataFrame({"Lufttemperatur": [5.0, 5.1]}, index=tid)

    T_obs = bestam_ankarpunkt(pm25, vader)

    assert T_obs == pd.Timestamp("2026-10-21 11:00", tz="Europe/Stockholm")
