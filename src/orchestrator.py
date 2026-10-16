import pandas as pd

from src.extracting_data import (
    hamta_pm25,
    vader_data,
    hamta_testperiod,
    hamta_test_vader,
)
from src.io import (
    generate_csv,
    merge_df_and_generate_csv,
    save_champion_model,
    append_champion_log,
    champion_is_fresh,
    append_datakontroll_log,
)
from src.config import ProjectConfig, skapa_testvagar
from src.validate_process import validate_data
from src.features import (
    add_wind_features,
    add_time_features,
    ersatt_vader_med_maltidsvader,
)
from src.train_models import (
    load_train_val_data,
    build_model_registry,
    train_and_evaluate_models,
    persistence_baseline,
)
from src.metrics import (
    select_best_model,
    build_comparison_table,
    display_df,
    jamfor_championer,
)
from src.logger import setup_logger


log = setup_logger(__name__)


def orchestration(cfg: ProjectConfig):
    log.info("Startar projektets orchestration.")

    
    # 1. TESTDATA: Hämta och sammanfoga
    

    # 1A. Beräkna testperioden dynamiskt
    test_start, test_slut = hamta_testperiod(
        cfg.vaderstation_id,
        cfg.vader_api,
    )

    log.info(
        "Dynamisk testperiod: %s till %s",
        test_start,
        test_slut,
    )

    # 1B. Skapa sökvägar för testfilerna
    testvagar = skapa_testvagar(cfg, test_start, test_slut)

    # 1C. Hämta PM2.5-testdata
    test_pm_data = hamta_pm25(
        test_start,
        test_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        testvagar["test_pm25"],
    )

    generate_csv(test_pm_data, testvagar["test_pm25"])

    log.info("PM2.5-testdata har hämtats och sparats.")

    # 1D. Hämta vädertestdata
    test_vader_data = hamta_test_vader(
        parametrar=cfg.vader_parametrar,
        test_start=test_start,
        test_slut=test_slut,
        station_id=cfg.vaderstation_id,
        VADER_API=cfg.vader_api,
    )

    generate_csv(test_vader_data, testvagar["test_vader"])

    log.info("Vädertestdata har hämtats och sparats.")

    # 1E. Sammanfoga PM2.5- och väderdata för testperioden
    merge_df_and_generate_csv(
        testvagar["test_pm25"],
        testvagar["test_vader"],
        "tid",
        testvagar["test_merged"],
        False,
    )

    log.info("Testdata för PM2.5 och väder har sammanfogats.")

    
    # 2. TRÄNINGSDATA: Hämta och sammanfoga
    

    # 2A. Hämta PM2.5-träningsdata
    train_pm_data = hamta_pm25(
        cfg.train_start,
        cfg.train_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.train_pm25,
    )

    generate_csv(train_pm_data, cfg.train_pm25)

    log.info("Träningsdata för PM2.5 har hämtats och sparats.")

    # 2B. Hämta väderdata för träning
    train_vader_data = vader_data(
        cfg.vader_parametrar,
        cfg.train_start,
        cfg.train_slut,
        cfg.vaderstation_id,
        cfg.vader_api,
        cfg.train_vader,
    )

    generate_csv(train_vader_data, cfg.train_vader)

    log.info("Träningsdata för väder har hämtats och sparats.")

    # 2C. Sammanfoga träningsdata
    merge_df_and_generate_csv(
        cfg.train_pm25,
        cfg.train_vader,
        "tid",
        cfg.train_merged,
        False,
    )

    log.info("Träningsdata för PM2.5 och väder har sammanfogats.")

    
    # 3. VALIDERINGSDATA: Hämta och sammanfoga
    

    # 3A. Hämta PM2.5-valideringsdata
    val_pm_data = hamta_pm25(
        cfg.validering_start,
        cfg.validering_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.val_pm25,
    )

    generate_csv(val_pm_data, cfg.val_pm25)

    log.info("Valideringsdata för PM2.5 har hämtats och sparats.")

    # 3B. Hämta väderdata för validering
    val_vader_data = vader_data(
        cfg.vader_parametrar,
        cfg.validering_start,
        cfg.validering_slut,
        cfg.vaderstation_id,
        cfg.vader_api,
        cfg.val_vader,
    )

    generate_csv(val_vader_data, cfg.val_vader)

    log.info("Valideringsdata för väder har hämtats och sparats.")

    # 3C. Sammanfoga valideringsdata
    merge_df_and_generate_csv(
        cfg.val_pm25,
        cfg.val_vader,
        "tid",
        cfg.val_merged,
        False,
    )

    log.info("Valideringsdata för PM2.5 och väder har sammanfogats.")

    
    # 4. VALIDERING, FEATURE ENGINEERING OCH SPARANDE
    
    # Läs in de sammanfogade dataseten
    train_merged_df = pd.read_csv(cfg.train_merged)
    val_merged_df = pd.read_csv(cfg.val_merged)
    test_merged_df = pd.read_csv(testvagar["test_merged"])

    # Samla alla dataset som ska bearbetas. mal_vader=True innebär att
    # väderkolumnerna ersätts med måltidsväder: vädrets värde på rad T
    # kommer från T + horisont, dvs. när PM2.5-målet realiseras.
    merged_data = {
        (cfg.train_processed, False): train_merged_df,
        (cfg.val_processed, False): val_merged_df,
        (testvagar["test_processed"], False): test_merged_df,
        (cfg.train_processed_forskjuten, True): train_merged_df,
        (cfg.val_processed_forskjuten, True): val_merged_df,
        (testvagar["test_processed_forskjuten"], True): test_merged_df,
    }

    for (output_path, mal_vader), merged_df in merged_data.items():
        log.info("Bearbetar dataset: %s", output_path.name)

        antal_merged = len(merged_df)

        # Validera data
        df = validate_data(merged_df)

        antal_validerad = len(df)

        if mal_vader:
            # Vindriktning skiftas FÖRE add_wind_features, så att vind_sin/
            # vind_cos räknas ur måltids-vindriktningen. Skiftet använder
            # alltid horisonten: måltiden är T + horisont, samma som mål-
            # skiftet, så vädret och målet kan aldrig hamnar ur fas.
            df = ersatt_vader_med_maltidsvader(
                df,
                cfg.forskjuten_vaderkolumner,
                cfg.horisont,
            )

        # Skapa features
        df = add_wind_features(df)
        df = add_time_features(df, cfg.horisont)

        # Skapa målvariabel: PM2.5 ett antal timmar framåt
        df[cfg.target_column] = df["pm25"].shift(-cfg.horisont)

        # Behåll endast kompletta modellrader
        modellkolumner = list(cfg.features) + [cfg.target_column]
        saknade = df[modellkolumner].isna().sum()

        df = df.dropna(subset=modellkolumner)

        # Logga datakontroll
        append_datakontroll_log(
            cfg.datakontroll_log,
            output_path.name,
            antal_merged,
            antal_validerad,
            len(df),
            saknade,
        )

        # Spara bearbetat dataset
        cfg.processed_dir.mkdir(parents=True, exist_ok=True)
        generate_csv(df, output_path, index=False)

        log.info("Bearbetat dataset har sparats: %s", output_path.name)

    
    # 5. CHAMPION-CHECK
    

    if not champion_is_fresh(
        cfg.champion_log,
        cfg.antal_dagar_sedan,
    ):
        log.info(
            "Ingen tillräckligt aktuell champion finns. "
            "Startar modellträning. Gräns: %s dagar.",
            cfg.antal_dagar_sedan,
        )

        # 5A. Ladda tränings- och valideringsdata
        log.info("Laddar tränings- och valideringsdata för modellträning.")

        X_train, y_train, X_val, y_val = load_train_val_data(
            cfg.train_processed,
            cfg.val_processed,
            cfg.features,
            cfg.target_column,
        )

        # 5B. Skapa modellregister
        all_models = build_model_registry(cfg.random_state)

        # 5C. Träna och utvärdera modellerna
        results_df, trained_models = train_and_evaluate_models(
            all_models,
            X_train,
            y_train,
            X_val,
            y_val,
        )

        log.info("Modellträningen och utvärderingen är klar.")

        results_df = results_df.sort_values(
            by=cfg.selection_metric,
        )
        display_df(results_df)

        # 5D. Skapa baseline
        baseline_train, baseline_val = persistence_baseline(
            X_train,
            y_train,
            X_val,
            y_val,
        )

        # 5E. Jämför modellerna med baseline
        comparison_df = build_comparison_table(
            results_df,
            baseline_val,
            cfg.selection_metric,
        )

        comparison_df = comparison_df.sort_values(
            by=cfg.selection_metric,
        )
        display_df(comparison_df)

        # 5F. Välj bästa alternativ
        best_name, best_row = select_best_model(
            comparison_df,
            metric=cfg.selection_metric,
        )

        log.info(
            "Bästa alternativ: %s. Urvalsmått: %s. Score: %.4f.",
            best_name,
            cfg.selection_metric,
            best_row[cfg.selection_metric],
        )

        if best_name == "Persistence Baseline":
            log.info("Ingen modell slog baseline. Sparar ingen champion.")
            champion_row = best_row

        else:
            # Hämta modellens resultat för metadata
            full_row = results_df[
                results_df["Modell"] == best_name
            ].iloc[0]

            champion_row = full_row

            save_champion_model(
                model=trained_models[best_name],
                model_name=best_name,
                best_row=full_row,
                models_dir=cfg.models_dir,
                random_state=cfg.random_state,
                metric=cfg.selection_metric,
            )

            log.info("Champion-modellen %s har sparats.", best_name)

        champion_df = champion_row.to_frame().T

        log.info("Slutligt valt alternativ: %s", best_name)
        display_df(champion_df)

        # 5G. Logga vinnaren
        append_champion_log(
            log_path=cfg.champion_log,
            model_name=best_name,
            metric=cfg.selection_metric,
            score=champion_row[cfg.selection_metric],
        )

        log.info(
            "Champion-loggen har uppdaterats. "
            "Modell: %s, mått: %s, score: %.4f.",
            best_name,
            cfg.selection_metric,
            champion_row[cfg.selection_metric],
        )

    else:
        champion_log = pd.read_csv(cfg.champion_log)

        log.info(
            "En befintlig champion är fortfarande aktuell. "
            "Tidpunkt: %s | Modell: %s | Mått: %s | Score: %s",
            champion_log["timestamp"].iloc[-1],
            champion_log["modell"].iloc[-1],
            champion_log["metric"].iloc[-1],
            champion_log["score"].iloc[-1],
        )

    # 6. FÖRSKJUTEN MODELLINJE (måltidsväder T+6)
    #
    # Vädret på varje rad ersätts med observationen vid T + horisont,
    # dvs. vädret som råder när PM2.5-målet realiseras. Modellerna tävlar
    # separat och vinnaren sparas som förskjuten champion med en EGEN
    # logg (forskjuten_log). Championflödet ovan påverkas inte alls.
    # OBS för framtiden: vid live-prediktion ska väder-slotten fyllas med
    # en väderPROGNOS för T+6, inte en observation (se docs/evaluation.md).

    if not champion_is_fresh(
        cfg.forskjuten_log,
        cfg.forskjuten_antal_dagar_sedan,
    ):
        log.info(
            "Ingen tillräckligt aktuell förskjuten champion finns. "
            "Startar träning av förskjuten modellinje. Gräns: %s dagar.",
            cfg.forskjuten_antal_dagar_sedan,
        )

        # 6A. Modellturnering – samma register, mått och komponenter
        # som championflödet, men på måltidsväder-datan. Dataseten med
        # måltidsväder byggdes i steg 4.
        X_train, y_train, X_val, y_val = load_train_val_data(
            cfg.train_processed_forskjuten,
            cfg.val_processed_forskjuten,
            cfg.features,
            cfg.target_column,
        )

        all_models = build_model_registry(cfg.random_state)

        results_df, trained_models = train_and_evaluate_models(
            all_models,
            X_train,
            y_train,
            X_val,
            y_val,
        )

        log.info("Träningen av den förskjuna modellinjen är klar.")

        results_df = results_df.sort_values(
            by=cfg.selection_metric,
        )
        display_df(results_df)

        # 6B. Baseline och jämförelsetabell
        baseline_train, baseline_val = persistence_baseline(
            X_train,
            y_train,
            X_val,
            y_val,
        )

        comparison_df = build_comparison_table(
            results_df,
            baseline_val,
            cfg.selection_metric,
        )

        comparison_df = comparison_df.sort_values(
            by=cfg.selection_metric,
        )
        display_df(comparison_df)

        # 6C. Välj bästa alternativ
        best_name, best_row = select_best_model(
            comparison_df,
            metric=cfg.selection_metric,
        )

        log.info(
            "Bästa alternativ (måltidsväder): %s. Urvalsmått: %s. Score: %.4f.",
            best_name,
            cfg.selection_metric,
            best_row[cfg.selection_metric],
        )

        forskjuten_namn = f"{best_name} (T+6)"

        if best_name == "Persistence Baseline":
            log.info(
                "Ingen modell slog baseline på måltidsväder. "
                "Sparar ingen förskjuten champion."
            )
            champion_row = best_row

        else:
            # Hämta modellens resultat för metadata
            full_row = results_df[
                results_df["Modell"] == best_name
            ].iloc[0]

            champion_row = full_row

            save_champion_model(
                model=trained_models[best_name],
                model_name=forskjuten_namn,
                best_row=full_row,
                models_dir=cfg.models_dir,
                random_state=cfg.random_state,
                metric=cfg.selection_metric,
                filprefix="forskjuten_",
            )

            log.info("Förskjuten champion %s har sparats.", forskjuten_namn)

            # 6D. Head-to-head mot championen på TEST-data, på de
            # rader som är kompletta i båda varianterna
            # (informationellt – båda linjerna behålls och båda ska
            # användas för live-prediktioner senare).
            jamfor_championer(
                cfg,
                forskjuten_modell=trained_models[best_name],
                forskjuten_namn=forskjuten_namn,
                test_path_vanlig=testvagar["test_processed"],
                test_path_forskjuten=testvagar["test_processed_forskjuten"],
            )

        champion_df = champion_row.to_frame().T

        log.info("Slutligt valt alternativ (måltidsväder): %s", best_name)
        display_df(champion_df)

        # 6E. Logga vinnaren i den EGEN loggen för förskjuna championer.
        # Aldrig i champion_log – annars tror champion_is_fresh att
        # observations-championen är nytränad.
        append_champion_log(
            log_path=cfg.forskjuten_log,
            model_name=forskjuten_namn,
            metric=cfg.selection_metric,
            score=champion_row[cfg.selection_metric],
        )

        log.info(
            "Loggen för förskjuna championer har uppdaterats. "
            "Modell: %s, mått: %s, score: %.4f.",
            forskjuten_namn,
            cfg.selection_metric,
            champion_row[cfg.selection_metric],
        )

    else:
        forskjuten_log = pd.read_csv(cfg.forskjuten_log)

        log.info(
            "En befintlig förskjuten champion är fortfarande aktuell. "
            "Tidpunkt: %s | Modell: %s | Mått: %s | Score: %s",
            forskjuten_log["timestamp"].iloc[-1],
            forskjuten_log["modell"].iloc[-1],
            forskjuten_log["metric"].iloc[-1],
            forskjuten_log["score"].iloc[-1],
        )
