import pandas as pd

from src.config import ProjectConfig
from src.metrics import jamfor_championer, display_df
from src.logger import setup_logger
from src.champion import load_latest_champion
from src.data_pipeline import fetch_and_merge, fetch_and_merge_test, build_processed_datasets
from src.model_pipeline import run_model_line
from src.io import champion_is_fresh

log = setup_logger(__name__)


def orchestration(cfg: ProjectConfig):
    log.info("Startar projektets orchestration.")

    # Suffix i champion-namnen. Horisonten (" (T+6)") finns på BÅDA linjerna
    # — det är målets förskjutning och champion_is_fresh:s skydd mot tysta
    # horisontbyten (filtret matchar på att namnet slutar med suffixet).
    # Linjerna markeras symmetriskt: "SVR vanlig (T+6)" resp.
    # "SVR forskjuten (T+6)". Stavningen "forskjuten" följer projektets
    # konvention (forskjuten_log, filprefix) och håller filnamnen ASCII-rena.
    vanlig_suffix = f" vanlig (T+{cfg.horisont})"
    forskjuten_suffix = f" forskjuten (T+{cfg.horisont})"

    # Endast den VANLIGA championen styr: är den färsk (tränad inom
    # antal_dagar_sedan) körs inte pipelinen alls — då visas bara det
    # senaste jämförelseresultatet ur jamfordelse-loggen (se else-grenen).
    # Fail-safe i champion_is_fresh: saknas logg, matchande rad eller
    # giltig timestamp returneras False, så att en full träning tvingas fram.
    if not champion_is_fresh(
        cfg.champion_log,
        cfg.antal_dagar_sedan,
        namn_suffix=vanlig_suffix,
    ):
        # 1. TESTDATA: Hämta och sammanfoga
        testvagar = fetch_and_merge_test(cfg)

        # 2. Hämta och sammanfoga data
        fetch_and_merge(
            cfg,
            cfg.train_start,
            cfg.train_slut,
            cfg.train_pm25,
            cfg.train_vader,
            cfg.train_merged,
            "Träningsdata",
        )

        fetch_and_merge(
            cfg,
            cfg.validering_start,
            cfg.validering_slut,
            cfg.val_pm25,
            cfg.val_vader,
            cfg.val_merged,
            "Valideringsdata",
        )

        # 3. VALIDERING, FEATURE ENGINEERING OCH SPARANDE
        build_processed_datasets(cfg, testvagar=testvagar)

        # 4. VANLIG MODELLINJE
        run_model_line(
            cfg,
            line_label="vanlig",
            train_path=cfg.train_processed,
            val_path=cfg.val_processed,
            test_path=testvagar["test_processed"],
            log_path=cfg.champion_log,
            antal_dagar=cfg.antal_dagar_sedan,
            name_suffix=vanlig_suffix,
        )

        # 5. FÖRSKJUTEN MODELLINJE (måltidsväder, T + horisont)
        # Vädret på varje rad ersätts med observationen vid T + horisont.
        # OBS för framtiden: vid live-prediktion ska väder-slotten fyllas med
        # en väderPROGNOS för måltiden (T + horisont), inte en observation
        # (se docs/evaluation.md).

        forskjuten = run_model_line(
            cfg,
            line_label="förskjuten",
            train_path=cfg.train_processed_forskjuten,
            val_path=cfg.val_processed_forskjuten,
            test_path=testvagar["test_processed_forskjuten"],
            log_path=cfg.forskjuten_log,
            antal_dagar=cfg.forskjuten_antal_dagar_sedan,
            name_suffix=forskjuten_suffix,
            filprefix="forskjuten_",
        )

        # 6. Jämför de två championerna på testdatan (informationellt).
        # Körs efter en full pipeline-körning när en förskjuten
        # champion-modell finns. När den vanliga championen är färsk och
        # pipelinen hoppats över visas istället det senaste loggade
        # jämförelseresultatet (se else-grenen nedan).
        if forskjuten is not None:
            forskjuten_modell, forskjuten_namn = forskjuten
            champion_modell, champion_namn, _ = load_latest_champion(
                cfg.champion_log,
                cfg.models_dir,
            )
            jamfor_championer(
                cfg,
                champion_modell=champion_modell,
                champion_namn=champion_namn,
                forskjuten_modell=forskjuten_modell,
                forskjuten_namn=forskjuten_namn,
                test_path_vanlig=testvagar["test_processed"],
                test_path_forskjuten=testvagar["test_processed_forskjuten"],
            )
    else:
        # Vanlig champion är färsk: hoppa över HELA pipelinen (ingen
        # datahämtning, ingen omträning) och visa det senaste
        # jämförelseresultatet ur logs/jamforelse_champion.csv.
        # En head-to-head-körning loggas med tre rader (champion,
        # förskjuten modell, baseline) som delar samma timestamp.
        log.info(
            "Den vanliga championen är fortfarande färsk (gräns: %s dagar). "
            "Pipelinen hoppas över — visar senaste jämförelseresultat.",
            cfg.antal_dagar_sedan,
        )

        if cfg.jamfordelse_log.is_file():
            jamdf = pd.read_csv(cfg.jamfordelse_log)
            senaste_tid = jamdf["timestamp"].iloc[-1]
            display_df(jamdf[jamdf["timestamp"] == senaste_tid])
        else:
            log.info(
                "Ingen tidigare jämförelse finns i %s — inget att visa.",
                cfg.jamfordelse_log,
            )
