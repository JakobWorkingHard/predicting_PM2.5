import pandas as pd

from src.champion import load_latest_champion
from src.extracting_data import (
    hamta_prognos,
    hamta_senaste_pm25,
    hamta_senaste_vaderobs,
)
from src.features import add_wind_features, add_time_features
from src.io import append_prediktioner_log, hamta_champion_modell
from src.logger import setup_logger
from src.metrics import display_df
from src.validate_process import sanity_kolla_vader
from src.metrics import display_df, sammanstall_live_uppfoljning

log = setup_logger()

def bestam_ankarpunkt(pm25_df: pd.DataFrame, vaderobs_df: pd.DataFrame):
    """
    T_obs = senaste hela timme med komplett pm25 + alla väderparametrar.

    Parningen sker via indexet (heltimmes-tidsstämplar) — samma exakta
    parningsregel som huvudpipelinens merge på "tid", så live och träning
    kan aldrig para ihop data olika. Returnerar None om ingen komplett
    timme finns; kor_live_prediktion (steg 9) hoppar då över körningen.
    """
    # Defensivt: live passerar aldrig validate_data:s dublettkoll, och
    # duplikatetiketter måste bort FÖRE concat — annars kan själva
    # sammanfogningen krascha (reindex på dubbelt index).
    pm25 = pm25_df[~pm25_df.index.duplicated(keep="last")]
    vaderobs = vaderobs_df[~vaderobs_df.index.duplicated(keep="last")]

    gemensam = pd.concat([pm25["pm25"], vaderobs], axis=1).sort_index()

    kompletta = gemensam.dropna()

    if kompletta.empty:
        log.warning("Ingen komplett timme hittades — ingen ankarpunkt.")
        return None

    T_obs = kompletta.index.max()
    log.info("Ankarpunkt T_obs: %s", T_obs)
    return T_obs



def bygg_live_rader(cfg, T_obs, pm25_varde, vaderobs_rad, vader_prognos_df):
    """
    Bygger en modellrad per linje (vanlig + forskjuten) för live-prediktion.

    Båda raderna gäller tidpunkten T_obs med samma pm25-mätning; det som
    skiljer är väderslotten — samma slot-alignment som träningen
    (jämför ersatt_vader_med_maltidsvader):
      vanlig:    väderOBSERVATION vid T_obs
      forskjuten: väderPROGNOS för måltiden T_obs + horisont

    Båda slots går genom sanity_kolla_vader (samma intervallregler som
    replace_invalid_values tvingar på träningsdatan), sedan add_wind_
    features + add_time_features. Kolumnerna blir exakt cfg.features,
    i samma ordning som modellerna tränades med.

    Returnerar {"vanlig": df, "forskjuten": df}, enradiga DataFrames.
    """
    maltid = T_obs + pd.Timedelta(hours=cfg.horisont)

    if maltid not in vader_prognos_df.index:
        raise ValueError(
            f"Prognosen täcker inte måltiden {maltid}. "
            f"Senaste prognossteg: {vader_prognos_df.index.max()}."
        )

    slots = {
        "vanlig": sanity_kolla_vader(vaderobs_rad),
        "forskjuten": sanity_kolla_vader(vader_prognos_df.loc[maltid]),
    }

    rader = {}
    for namn, slot in slots.items():
        rad = {"tid": T_obs, "pm25": float(pm25_varde)}
        for kolumn in cfg.forskjuten_vaderkolumner:
            rad[kolumn] = slot[kolumn]

        df_rad = pd.DataFrame([rad])
        df_rad = add_wind_features(df_rad)
        df_rad = add_time_features(df_rad, cfg.horisont)
        rader[namn] = df_rad[list(cfg.features)]

    log.info("Modellrader byggda för T_obs %s, måltid %s.", T_obs, maltid)
    return rader





def kor_live_prediktion(cfg):
    """
    Kör live-flödet en gång: hämta → ankarpunkt → vakter → modellrader →
    ladda championer → prediktera → visa → logga.

    Vakter (i ordning):
      1. Ingen komplett timme (bestam_ankarpunkt -> None) → hoppa över
      2. T_obs äldre än cfg.max_alder_timmar → hoppa över
      3. Idempotens: T_obs redan loggad (om cfg.idempotent) → hoppa över
      4. Per linje: champion saknas → logga varning, hoppa över linjen

    Returnerar DataFrame med en rad per FAKTISKT predikterad linje, eller
    None om alla vakter/linjer hoppades över (inget loggas då).
    """
    nu = pd.Timestamp.now(tz="Europe/Stockholm")

    # 1. Hämta prognos + senaste observationer
    # Notera att referenstiden är NÄR prognosen skapades hos SMHI, dvs en timestamp för hur färsk prognosen är
    prognos_df, referenstid = hamta_prognos(cfg)
    pm25_df = hamta_senaste_pm25(cfg)
    vaderobs_df = hamta_senaste_vaderobs(cfg)

    # 2. Ankartid
    T_obs = bestam_ankarpunkt(pm25_df, vaderobs_df)
    if T_obs is None:
        log.warning("Live-körning hoppades över: ingen komplett timme.")
        return None

    alder_h = (nu - T_obs).total_seconds() / 3600
    maltid = T_obs + pd.Timedelta(hours=cfg.horisont)
    log.info("T_obs: %s (%.1f h gammal) -> prediktion för %s", T_obs, alder_h, maltid)

    # 3. Vakter
    if alder_h > cfg.max_alder_timmar:
        log.warning(
            "Live-körning hoppades över: T_obs %.1f h gammal (max %s h).",
            alder_h, cfg.max_alder_timmar,
        )
        return None

    if cfg.idempotent and cfg.prediktioner_log.is_file():
        tidigare = pd.read_csv(cfg.prediktioner_log)
        gamla_t_obs = pd.to_datetime(tidigare["t_obs"], utc=True)
        if (gamla_t_obs == T_obs).any():
            gamla = tidigare[gamla_t_obs == T_obs]
            log.warning(
                "Live-körning hoppades över: T_obs redan predikterad "
                "(slå av [live].idempotent för att köra ändå)."
            )
            log.info("Tidigare prediktioner för T_obs %s:", T_obs)
            display_df(
                gamla[["linje", "modell", "prediktion", "mål_tid", "pm25_senaste"]]
            )
            return None

    # 4. Modellrader för båda linjerna (rieal kedja: steg 5–8)
    rader = bygg_live_rader(
        cfg=cfg,
        T_obs=T_obs,
        pm25_varde=pm25_df.loc[T_obs, "pm25"],
        vaderobs_rad=vaderobs_df.loc[T_obs],
        vader_prognos_df=prognos_df,
    )

    # 5. Ladda championer (olika tupellängd! )
    vanlig_modell, vanlig_namn = hamta_champion_modell(cfg.models_dir, cfg.champion_log)
    forskjuten_modell, forskjuten_namn, _ = load_latest_champion(
        cfg.forskjuten_log, cfg.models_dir
    )

    linjer = [
        ("vanlig", vanlig_modell, vanlig_namn),
        ("forskjuten", forskjuten_modell, forskjuten_namn),
    ]


    poster = []
    for linje, modell, namn in linjer:
        if modell is None:
            log.warning("Hoppar över linjen %s: ingen champion hittades.", linje)
            continue

        poster.append({
            "körningstid": nu.isoformat(),
            "t_obs": T_obs.isoformat(),
            "mål_tid": maltid.isoformat(),
            "pm25_senaste": float(pm25_df.loc[T_obs, "pm25"]),
            "pm25_alder_h": round(alder_h, 2),
            "horisont": cfg.horisont,
            "prognos_referenstid": referenstid.isoformat(),
            "linje": linje,
            "modell": namn,
            "prediktion": float(modell.predict(rader[linje])[0]),
        })

    if not poster:
        log.warning("Inga prediktioner gjordes — inget loggas.")
        return None

    # 6. Visa och logga en rad per linje
    resultat = pd.DataFrame(poster)
    display_df(resultat[["linje", "modell", "prediktion", "mål_tid", "pm25_senaste"]])
    append_prediktioner_log(cfg.prediktioner_log, resultat)

    log.info("Loggade %d live-prediktioner i %s.", len(resultat), cfg.prediktioner_log)
    return resultat



def folj_uppa(cfg, timmar_bak: int = 24 * 7):
    """
    Rättar loggade live-prediktioner mot verkliga PM2.5-mätningar och
    sammanställer MAE/RMSE/R²/Bias per linje + persistence-baseline.

    Returnerar sammanställningen (DataFrame), eller None om loggen saknas
    eller ingen prediktion hunnit realiseras ännu.
    """
    if not cfg.prediktioner_log.is_file():
        log.warning("Ingen prediktionslogg att följa upp: %s", cfg.prediktioner_log)
        return None

    logg = pd.read_csv(cfg.prediktioner_log)
    for kolumn in ["körningstid", "t_obs", "mål_tid"]:
        logg[kolumn] = pd.to_datetime(logg[kolumn], utc=True)

    # Verkliga värden, indexerade i UTC för enkel matchning mot mål_tid
    verkligt = hamta_senaste_pm25(cfg, timmar_bak=timmar_bak)["pm25"]
    verkligt.index = verkligt.index.tz_convert("UTC")
    logg["faktiskt"] = logg["mål_tid"].dt.tz_convert("UTC").map(verkligt)

    uppf = logg.dropna(subset=["faktiskt"]).copy()

    if uppf.empty:
        log.info("Ingen prediktion har hunnit realiseras ännu.")
        return None

    sammanstallning = sammanstall_live_uppfoljning(uppf)
    log.info("Uppföljning: %d rättade prediktioner.", len(uppf))
    display_df(sammanstallning)
    return sammanstallning