import pandas as pd
from src.extracting_data import (
    hamta_pm25,
    vader_data
)
from src.io import (
    generate_csv,
    merge_df_and_generate_csv,
    forskjut_tid_csv,
    save_champion_model,
    append_champion_log,
    champion_is_fresh,
)
from src.config import ProjectConfig
from src.validate_process import validate_data
from src.features import add_wind_features, add_time_features
from src.train_models import (
    load_train_val_data,
    build_model_registry,
    train_and_evaluate_models,
    persistence_baseline,
)
from src.metrics import select_best_model, build_comparison_table, display_df



def orchestration(cfg: ProjectConfig):

    # = 1 TRÄNINGSDATA: Hämtar, validerar och transformerar

    #   ==-- 1A Hämtar pm2.5 träningsdata alt. genererar en df om csv redan finns
    train_pm_data = hamta_pm25(
        cfg.train_start,
        cfg.train_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.train_pm25,
    )
    generate_csv(train_pm_data, cfg.train_pm25)

    #    ==-- 1B Hämtar tränings-väderdata alt. genererar df om csv redan finns
    train_vader_data = vader_data(
        cfg.vader_parametrar,
        cfg.train_start,
        cfg.train_slut,
        cfg.vaderstation_id,
        cfg.vader_api,
        cfg.train_vader
    )
    generate_csv(train_vader_data, cfg.train_vader)

    #    ==-- 1C Mergar träningsdata pm2.5 och väderdata (om mergad csv ej redan finns)
    merge_df_and_generate_csv(
        cfg.train_pm25,
        cfg.train_vader,
        "tid",
        cfg.train_merged,
        False
    )

    # = 2 VALIDERINGSDATA: Hämtar, validerar och transformerar

    #   ==-- 2A Hämtar pm2.5 valideringsdata alt. genererar en df om csv redan finns
    val_pm_data = hamta_pm25(
        cfg.validering_start,
        cfg.validering_slut,
        cfg.pm25_tidsserie_id,
        cfg.luft_api,
        cfg.val_pm25
    )
    generate_csv(val_pm_data, cfg.val_pm25)

    #   ==-- 2B Hämtar validerings-väderdata alt. genererar df om csv redan finns
    val_vader_data = vader_data(
        cfg.vader_parametrar,
        cfg.validering_start,
        cfg.validering_slut,
        cfg.vaderstation_id,
        cfg.vader_api,
        cfg.val_vader
    )
    generate_csv(val_vader_data, cfg.val_vader)

    #    ==-- 2C Mergar valideringsdata pm2.5 och väderdata (om mergad csv ej redan finns)
    merge_df_and_generate_csv(
        cfg.val_pm25,
        cfg.val_vader,
        "tid",
        cfg.val_merged,
        False
    )

    # = 3 VALIDERAR, TRANSFORMERAR OCH SPARAR TRÄNINGSDATA OCH VALIDERINGSDATA

    #    ==-- 3A Läser in mergad data
    train_merged_df = pd.read_csv(cfg.train_merged)
    val_merged_df = pd.read_csv(cfg.val_merged)

    #    ==--3B Validerar, transformerar och sparar processad data
    merged_data = {
        cfg.train_processed: train_merged_df,
        cfg.val_processed: val_merged_df
    }

    for key, value in merged_data.items():
        df = validate_data(value)
        df = add_wind_features(df)
        df = add_time_features(df, cfg.horisont)
        df[cfg.target_column] = df["pm25"].shift(-cfg.horisont)
        df = df.dropna()
        cfg.processed_dir.mkdir(parents=True, exist_ok=True)
        generate_csv(df, key, index=False)

    # = 3C CHAMPION-CHECK: hoppa över träning om champion tränats nyligen

    if not champion_is_fresh(cfg.champion_log, cfg.antal_dagar_sedan):
        print(f"Vi har ingen aktiv ml modell sedan {cfg.antal_dagar_sedan} - börjar träna en ny champion")

    # = 4 TRÄNAR MODELLER

        #   ==-- 4A Delar upp träningsdata och valideringsdata i X och y
        X_train, y_train, X_val, y_val = load_train_val_data(
            cfg.train_processed,
            cfg.val_processed,
            cfg.features,
            cfg.target_column,
        )

        #   ==-- 4B Hämtar alla våra valda modeller
        all_models = build_model_registry(cfg.random_state)

        #   ==-- 4C Låter våra modeller möta varann
        results_df, trained_models = train_and_evaluate_models(
            all_models,
            X_train,
            y_train,
            X_val,
            y_val,
        )
        results_df = results_df.sort_values(by=cfg.selection_metric)
        display_df(results_df)

        #   ==-- 4D Skapar vår baseline
        baseline_train, baseline_val = persistence_baseline(
            X_train, y_train, X_val, y_val
        )

        #   ==-- 4E Champion vs baseline - bygg först, välj sen
        comparison_df = build_comparison_table(results_df, baseline_val, cfg.selection_metric)
        comparison_df = comparison_df.sort_values(by=cfg.selection_metric)
        display_df(comparison_df)

        #   ==-- 4F Välj vinnare bland modeller OCH baseline
        best_name, best_row = select_best_model(
            comparison_df, metric=cfg.selection_metric
        )

        if best_name == "Persistence Baseline":
            print("Ingen modell slog baseline - sparar ingen champion.")
            champion_row = best_row
        else:
            # Hämta fullständig rad från results_df för metadata
            full_row = results_df[results_df["Modell"] == best_name].iloc[0]
            champion_row = full_row
            save_champion_model(
                model=trained_models[best_name],
                model_name=best_name,
                best_row=full_row,
                models_dir=cfg.models_dir,
                random_state=cfg.random_state,
                metric=cfg.selection_metric,
            )
        champion_df = champion_row.to_frame().T
        print(f"\nVinnare: {best_name}")
        display_df(champion_df)

        # = 4G Logga vinnaren (även Persistence Baseline räknas som en giltig körning)
        append_champion_log(
            log_path=cfg.champion_log,
            model_name=best_name,
            metric=cfg.selection_metric,
            score=champion_row[cfg.selection_metric],
        )
    else:
        champion_log = pd.read_csv(cfg.champion_log)
        print(f"Finns redan ml modell från {champion_log['timestamp'].iloc[-1]}\nModellnamn: {champion_log['modell'].iloc[-1]}\nValideringsmetod: {champion_log['metric'].iloc[-1]}\nScore: {champion_log['score'].iloc[-1]}")


