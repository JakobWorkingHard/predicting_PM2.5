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
    forskjut_tid_csv,
    save_champion_model,
    append_champion_log,
    champion_is_fresh,
    append_datakontroll_log,
)
from src.config import ProjectConfig, skapa_testvagar
from src.validate_process import validate_data
from src.features import add_wind_features, add_time_features
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
)
from src.logger import setup_logger


log = setup_logger(__name__)


def orchestration(cfg: ProjectConfig):
    log.info("Startar projektets orchestration.")

    # 1. Beräkna testperioden dynamiskt
    test_start, test_slut = hamta_testperiod(
        cfg.vaderstation_id,
        cfg.vader_api,
    )

    log.info(
        "Dynamisk testperiod: %s till %s",
        test_start,
        test_slut,
    )

    # 2. Skapa sökvägar för testfilerna
    testvagar = skapa_testvagar(cfg, test_start, test_slut)

    # 3. Hämta PM2.5-testdata
    test_pm_data = hamta_pm25(
        test_start,
        test_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        testvagar["test_pm25"],
    )

    generate_csv(test_pm_data, testvagar["test_pm25"])

    log.info("PM2.5-testdata har hämtats och sparats.")

    # 4. Hämta vädertestdata
    test_vader_data = hamta_test_vader(
        parametrar=cfg.vader_parametrar,
        test_start=test_start,
        test_slut=test_slut,
        station_id=cfg.vaderstation_id,
        VADER_API=cfg.vader_api,
    )

    generate_csv(test_vader_data, testvagar["test_vader"])

    log.info("Vädertestdata har hämtats och sparats.")

    # 5. Sammanfoga PM2.5- och väderdata för testperioden
    merge_df_and_generate_csv(
        testvagar["test_pm25"],
        testvagar["test_vader"],
        "tid",
        testvagar["test_merged"],
        False,
    )

    log.info("Testdata för PM2.5 och väder har sammanfogats.")

    
    # 6. TRÄNINGSDATA: Hämta och sammanfoga
    

    # 6A. Hämta PM2.5-träningsdata
    train_pm_data = hamta_pm25(
        cfg.train_start,
        cfg.train_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.train_pm25,
    )

    generate_csv(train_pm_data, cfg.train_pm25)

    log.info("Träningsdata för PM2.5 har hämtats och sparats.")

    # 6B. Hämta väderdata för träning
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

    # 6C. Sammanfoga träningsdata
    merge_df_and_generate_csv(
        cfg.train_pm25,
        cfg.train_vader,
        "tid",
        cfg.train_merged,
        False,
    )

    log.info("Träningsdata för PM2.5 och väder har sammanfogats.")

    
    # 7. VALIDERINGSDATA: Hämta och sammanfoga
    

    # 7A. Hämta PM2.5-valideringsdata
    val_pm_data = hamta_pm25(
        cfg.validering_start,
        cfg.validering_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.val_pm25,
    )

    generate_csv(val_pm_data, cfg.val_pm25)

    log.info("Valideringsdata för PM2.5 har hämtats och sparats.")

    # 7B. Hämta väderdata för validering
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

    # 7C. Sammanfoga valideringsdata
    merge_df_and_generate_csv(
        cfg.val_pm25,
        cfg.val_vader,
        "tid",
        cfg.val_merged,
        False,
    )

    log.info("Valideringsdata för PM2.5 och väder har sammanfogats.")

    
    # 8. VALIDERING, FEATURE ENGINEERING OCH SPARANDE
    
    # Läs in de sammanfogade dataseten
    train_merged_df = pd.read_csv(cfg.train_merged)
    val_merged_df = pd.read_csv(cfg.val_merged)
    test_merged_df = pd.read_csv(testvagar["test_merged"])

    # Samla alla dataset som ska bearbetas
    merged_data = {
        cfg.train_processed: train_merged_df,
        cfg.val_processed: val_merged_df,
        testvagar["test_processed"]: test_merged_df,
    }

    for output_path, merged_df in merged_data.items():
        log.info("Bearbetar dataset: %s", output_path.name)

        antal_merged = len(merged_df)

        # Validera data
        df = validate_data(merged_df)

        antal_validerad = len(df)

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

    
    # 9. CHAMPION-CHECK
    

    if not champion_is_fresh(
        cfg.champion_log,
        cfg.antal_dagar_sedan,
    ):
        log.info(
            "Ingen tillräckligt aktuell champion finns. "
            "Startar modellträning. Gräns: %s dagar.",
            cfg.antal_dagar_sedan,
        )

        # 9A. Ladda tränings- och valideringsdata
        log.info("Laddar tränings- och valideringsdata för modellträning.")

        X_train, y_train, X_val, y_val = load_train_val_data(
            cfg.train_processed,
            cfg.val_processed,
            cfg.features,
            cfg.target_column,
        )

        # 9B. Skapa modellregister
        all_models = build_model_registry(cfg.random_state)

        # 9C. Träna och utvärdera modellerna
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

        # 9D. Skapa baseline
        baseline_train, baseline_val = persistence_baseline(
            X_train,
            y_train,
            X_val,
            y_val,
        )

        # 9E. Jämför modellerna med baseline
        comparison_df = build_comparison_table(
            results_df,
            baseline_val,
            cfg.selection_metric,
        )

        comparison_df = comparison_df.sort_values(
            by=cfg.selection_metric,
        )
        display_df(comparison_df)

        # 9F. Välj bästa alternativ
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

        # 9G. Logga vinnaren
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
