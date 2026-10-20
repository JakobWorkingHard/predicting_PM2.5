import pandas as pd

from src.io import (
    generate_csv,
    save_champion_model,
    append_champion_log,
    champion_is_fresh,
    append_datakontroll_log,
)
from src.config import ProjectConfig
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
    evaluate_model
)
from src.logger import setup_logger

from src.champion import load_latest_champion, compete_with_champion

from src.data_pipeline import fetch_and_merge, fetch_and_merge_test, build_processed_datasets

log = setup_logger(__name__)


def orchestration(cfg: ProjectConfig):
    log.info("Startar projektets orchestration.")

    
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
        # Ingen modell sparas när baseline vinner, så det finns ingen sökväg att logga
        if best_name == "Persistence Baseline":
            log.info("Ingen modell slog baseline. Sparar ingen champion.")
            champion_row = best_row
            modell_sokvag = None

        else:
            # Hämta modellens resultat för metadata
            full_row = results_df[
                results_df["Modell"] == best_name
            ].iloc[0]

            # Låt dagens bästa modell tävla mot den tidigare championen
            # på samma testdata. Den tidigare championen tränas inte om.
            old_model, old_name, old_file = load_latest_champion(
                cfg.champion_log,
                cfg.models_dir,
            )

            winner, _ = compete_with_champion(
                new_model=trained_models[best_name],
                new_name=best_name,
                old_model=old_model,
                old_name=old_name,
                test_path=testvagar["test_processed"],
                features=cfg.features,
                target=cfg.target_column,
                metric=cfg.selection_metric,
            )

            if winner == "new":
                # Dagens modell vann och sparas som ny champion
                champion_row = full_row

                # save_champion_model returnerar sökvägen till .joblib-filen.
                # Den loggas, så att championen kan läsas in igen senare.
                modell_sokvag = save_champion_model(
                    model=trained_models[best_name],
                    model_name=best_name,
                    best_row=full_row,
                    models_dir=cfg.models_dir,
                    random_state=cfg.random_state,
                    metric=cfg.selection_metric,
                )

                log.info("Champion-modellen %s har sparats.", best_name)

            else:
                # Den tidigare championen vann. Ingen ny modell sparas, men
                # championen loggas igen med dagens datum, så att
                # champion_is_fresh inte tränar om vid varje körning.
                best_name = old_name
                modell_sokvag = old_file

                # Räkna ut den tidigare championens resultat på dagens
                # valideringsdata, så att poängen i loggen går att jämföra.
                # Hit kommer vi bara om det fanns en tidigare champion,
                # eftersom compete_with_champion annars returnerar "new".
                assert old_model is not None
                old_val = evaluate_model(y_val, old_model.predict(X_val))
                champion_row = pd.Series({
                    "Modell": old_name,
                    "Validation MAE": old_val["MAE"],
                    "Validation RMSE": old_val["RMSE"],
                    "Validation R²": old_val["R2"],
                    "Validation Bias": old_val["Bias"],
                })

                log.info("Den tidigare championen %s behålls.", old_name)

        champion_df = champion_row.to_frame().T

        log.info("Slutligt valt alternativ: %s", best_name)
        display_df(champion_df)

        # 5G. Logga vinnaren, inklusive sökvägen till modellfilen
        # (tom om baslinjen vann)
        append_champion_log(
            log_path=cfg.champion_log,
            model_name=best_name,
            metric=cfg.selection_metric,
            score=champion_row[cfg.selection_metric],
            sokvag = modell_sokvag
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
            # Ingen modell sparas, så det finns ingen sökväg att logga
            modell_sokvag = None

        else:
            # Hämta modellens resultat för metadata
            full_row = results_df[
                results_df["Modell"] == best_name
            ].iloc[0]

            # Låt dagens bästa förskjutna modell tävla mot den tidigare
            # förskjutna championen på samma testdata. Den tidigare
            # championen tränas inte om.
            old_model, old_name, old_file = load_latest_champion(
                cfg.forskjuten_log,
                cfg.models_dir,
            )

            winner, _ = compete_with_champion(
                new_model=trained_models[best_name],
                new_name=forskjuten_namn,
                old_model=old_model,
                old_name=old_name,
                test_path=testvagar["test_processed_forskjuten"],
                features=cfg.features,
                target=cfg.target_column,
                metric=cfg.selection_metric,
            )

            if winner == "new":
                # Dagens modell vann och sparas som ny förskjuten champion
                champion_row = full_row
                forskjuten_modell = trained_models[best_name]

                # save_champion_model returnerar sökvägen till .joblib-filen.
                # Den loggas, så att championen kan läsas in igen senare.
                modell_sokvag = save_champion_model(
                    model=forskjuten_modell,
                    model_name=forskjuten_namn,
                    best_row=full_row,
                    models_dir=cfg.models_dir,
                    random_state=cfg.random_state,
                    metric=cfg.selection_metric,
                    filprefix="forskjuten_",
                )

                log.info("Förskjuten champion %s har sparats.", forskjuten_namn)

            else:
                # Den tidigare förskjutna championen vann. Ingen ny modell
                # sparas, men championen loggas igen med dagens datum, så att
                # champion_is_fresh inte tränar om vid varje körning.
                # Hit kommer vi bara om det fanns en tidigare champion,
                # eftersom compete_with_champion annars returnerar "new".
                assert old_model is not None
                best_name = old_name
                forskjuten_namn = old_name
                forskjuten_modell = old_model
                modell_sokvag = old_file

                # Räkna ut den tidigare championens resultat på dagens
                # valideringsdata, så att poängen i loggen går att jämföra.
                old_val = evaluate_model(y_val, old_model.predict(X_val))
                champion_row = pd.Series({
                    "Modell": old_name,
                    "Validation MAE": old_val["MAE"],
                    "Validation RMSE": old_val["RMSE"],
                    "Validation R²": old_val["R2"],
                    "Validation Bias": old_val["Bias"],
                })

                log.info("Den tidigare förskjutna championen %s behålls.", old_name)

            # 6D. Head-to-head mot championen på TEST-data, på de
            # rader som är kompletta i båda varianterna
            # (informationellt – båda linjerna behålls och båda ska
            # användas för live-prediktioner senare).
            
            # Den vanliga championen läses in via sökvägen i loggen.
            # Den förskjutna championen är den som vann tävlingen ovan.
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
            sokvag=modell_sokvag
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
