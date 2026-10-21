import pandas as pd 

from src.io import ( 
    champion_is_fresh, 
    save_champion_model, 
    append_champion_log, ) 

from src.train_models import ( 
    load_train_val_data, 
    build_model_registry, 
    train_and_evaluate_models, 
    persistence_baseline, )

from src.metrics import ( 
    select_best_model, 
    build_comparison_table, 
    display_df, evaluate_model, 
    ) 
from src.champion import load_latest_champion, compete_with_champion 

from src.logger import setup_logger 

log = setup_logger(__name__)


def _validation_row(model, name, X_val, y_val): 
    """ Räknar ut en modells resultat på valideringsdatan, i samma format som 
    raderna i results_df. Används när den tidigare championen vinner, så att 
    poängen i loggen går att jämföra med de andra raderna. """ 
    
    resultat = evaluate_model(y_val, model.predict(X_val)) 
    
    return pd.Series({ 
        "Modell": name, 
        "Validation MAE": resultat["MAE"], 
        "Validation RMSE": resultat["RMSE"], 
        "Validation R²": resultat["R2"], 
        "Validation Bias":resultat["Bias"], })


def run_model_line( cfg, line_label, train_path, val_path, test_path, log_path, antal_dagar, name_suffix="", filprefix="", ):
 
    """ Kör hela modellflödet för en modellinje (vanlig eller förskjuten): 
    1. Hoppar över allt om championen (med linjens horisont-suffix i
    namnet) är yngre än antal_dagar. 
    2. Tränar alla modeller och jämför dem med baslinjen på valideringsdatan. 
    3. Låter dagens bästa modell tävla mot den tidigare championen på testdatan. 
    Den tidigare championen behålls om den är minst lika bra. 
    4. Loggar vinnaren i log_path, med sökvägen till modellfilen. 
    Returnerar (champion_modell, champion_namn) om linjen tränades och enmodell blev champion. 
    Returnerar None om linjen hoppades över eller om baslinjen vann. """ 
 
    # 1. Är championen fortfarande färsk? 
    # Suffixet kopplar färskheten till rätt horisont — en " (T+1)"-rad
    # kvalar aldrig in som färsk " (T+6)"-champion.
    if champion_is_fresh(log_path, antal_dagar, namn_suffix=name_suffix): 
        champion_log = pd.read_csv(log_path) 
        log.info( "En befintlig %s champion är fortfarande aktuell. " 
                 "Tidpunkt: %s | Modell: %s | Mått: %s | Score: %s", 
                 line_label,
                 champion_log["timestamp"].iloc[-1], 
                 champion_log["modell"].iloc[-1], 
                 champion_log["metric"].iloc[-1],
                 champion_log["score"].iloc[-1], ) 
        return None 
 
    log.info( "Ingen tillräckligt aktuell %s champion finns. " 
             "Startar modellträning. Gräns: %s dagar.", 
             line_label, 
             antal_dagar, 
             )

    # 2. Träna och utvärdera alla modeller på valideringsdatan 
    X_train, y_train, X_val, y_val = load_train_val_data(train_path, 
                                                         val_path, 
                                                         cfg.features, 
                                                         cfg.target_column, 
                                                         ) 
    
    all_models = build_model_registry(cfg.random_state) 
    results_df,trained_models = train_and_evaluate_models( 
        all_models, 
        X_train, 
        y_train, 
        X_val, 
        y_val, 
        ) 
    
    log.info("Träningen av den %s modellinjen är klar.", line_label) 
    
    # Jämför modellerna med baslinjen. build_comparison_table sorterar 
    # redan tabellen så att den bästa modellen hamnar överst. 
    
    baseline_train, baseline_val = persistence_baseline( X_train, y_train, X_val,y_val, ) 
    comparison_df = build_comparison_table( results_df, baseline_val, cfg.selection_metric, )
    
    display_df(comparison_df) 
    
    best_name, best_row = select_best_model( comparison_df, metric=cfg.selection_metric, )
    
    log.info( "Bästa alternativ (%s): %s. Urvalsmått: %s. Score: %.4f.", 
             line_label, 
             best_name, 
             cfg.selection_metric,
             best_row[cfg.selection_metric], 
             )
    
    champion_namn = f"{best_name}{name_suffix}"
    champion_modell = None

    # 3. Vem blir champion? 
    if best_name == "Persistence Baseline": 
        # Ingen modell slog baslinjen. Ingen modell sparas, så det finns ingen sökväg att logga. 
        log.info("Ingen modell slog baseline (%s). Sparar ingen champion.", line_label)
        
        champion_row = best_row 
        modell_sokvag = None 
        
    else: 
        # Hämta modellens resultat för metadata 
        full_row = results_df[results_df["Modell"] == best_name].iloc[0] 
        # Låt dagens bästa modell tävla mot den tidigare championen 
        # # på samma testdata. Den tidigare championen tränas inte om. 

        old_model, old_name, old_file = load_latest_champion(log_path, cfg.models_dir, ) 
        
        winner, _ = compete_with_champion( 
            new_model=trained_models[best_name],
            new_name=champion_namn, 
            old_model=old_model, 
            old_name=old_name, 
            test_path=test_path, 
            features=cfg.features,
            target=cfg.target_column, 
            metric=cfg.selection_metric, ) 
        
        if winner == "new":
             # Dagens modell vann och sparas som ny champion. 
             # # save_champion_model returnerar sökvägen till .joblib-filen. 
             
             champion_row = full_row 
             champion_modell = trained_models[best_name] 

             modell_sokvag = save_champion_model( model=champion_modell,
                                                 model_name=champion_namn, 
                                                 best_row=full_row, 
                                                 models_dir=cfg.models_dir, 
                                                 random_state=cfg.random_state,
                                                 metric=cfg.selection_metric, 
                                                 filprefix=filprefix, ) 
             
             log.info("Champion %s har sparats.", champion_namn) 
             
        else: 
            # Den tidigare championen vann. Ingen ny modell sparas, men 
            # championen loggas igen med dagens datum, så att
            # champion_is_fresh inte tränar om vid varje körning. 
            # Hit kommer vi bara om det fanns en tidigare champion, 
            # eftersom compete_with_champion annars returnerar "new". 
            
            assert old_model is not None 
            champion_namn = old_name
            champion_modell = old_model 
            modell_sokvag = old_file 
            champion_row = _validation_row(old_model, old_name,X_val, y_val)
            
            log.info("Den tidigare championen %s behålls.", old_name) 
            
    log.info("Slutligt valt alternativ (%s): %s",line_label, champion_namn) 
    
    display_df(champion_row.to_frame().T)


    # 4. Logga vinnaren, inklusive sökvägen till modellfilen 
    # (tom om baslinjen vann)
    append_champion_log(log_path=log_path, 
                        model_name=champion_namn, 
                        metric=cfg.selection_metric,
                        score=champion_row[cfg.selection_metric], 
                        sokvag=modell_sokvag, ) 
    
    log.info("Champion-loggen (%s) har uppdaterats. Modell: %s, mått: %s, score: %.4f.", 
             line_label, 
             champion_namn, 
             cfg.selection_metric,
             champion_row[cfg.selection_metric],
            ) 
    
    if champion_modell is None: 
        return None 
    
    return champion_modell, champion_namn


 
 
 