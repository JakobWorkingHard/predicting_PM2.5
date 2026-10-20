# Hämtar PM2.5 samt väder och slår ihop dem. 
# Merged används på både train och val

import pandas as pd

from src.extracting_data import hamta_pm25, vader_data, hamta_testperiod, hamta_test_vader
from src.config import skapa_testvagar
from src.io import generate_csv, merge_df_and_generate_csv, append_datakontroll_log
from src.logger import setup_logger 
from src.validate_process import validate_data 
from src.features import ( 
    add_wind_features, 
    add_time_features,
    ersatt_vader_med_maltidsvader, 
    )
 

log = setup_logger(__name__)

def fetch_and_merge(cfg, start, end, pm25_path, vader_path, merged_path, label): 
    """ Hämtar PM2.5 och väderdata för en period och slår ihop dem. Används för både tränings- 
    och valideringsdata. Om filerna redan finns läses de istället för att hämtas på nytt. label 
    används bara i loggmeddelandena, t.ex. "Träningsdata". """

    #Hämta PM2.5 
    pm_data = hamta_pm25(start, 
                         end, 
                         cfg.pm25_tidsserie_id, 
                         cfg.luft_api, pm25_path, 
                         )
    
    generate_csv(pm_data, pm25_path) 
    log.info("%s för PM2.5 har hämtats och sparats.", label)
 
    # Hämta väder 
    vader = vader_data( 
                cfg.vader_parametrar, 
                start, 
                end, 
                cfg.vaderstation_id, 
                cfg.vader_api, 
                vader_path, 
                )
    
    generate_csv(vader, vader_path) 
    
    log.info("%s för väder har hämtats och sparats.", label)

    # Slå ihop PM2.5 och väder 
    merge_df_and_generate_csv( 
        pm25_path, 
        vader_path, 
        "tid", 
        merged_path, 
        False, 
        )
    
    log.info("%s för PM2.5 och väder har sammanfogats.", label)





def fetch_and_merge_test(cfg): 
    """ Hämtar PM2.5 och väderdata för den dynamiska testperioden och slår ihop dem. 
    Testperioden går från första tidpunkten i SMHI:s latest-months fram till nu minus 
    fyra timmar. Returnerar testvagar, en dict med sökvägarna till testfilerna. """ 
    
    # Beräkna testperioden och sökvägarna till testfilerna 
    test_start, test_slut = hamta_testperiod(cfg.vaderstation_id, cfg.vader_api) 
    
    log.info("Dynamisk testperiod: %s till %s", test_start, test_slut)
    
    testvagar = skapa_testvagar(cfg, test_start, test_slut)

    # Hämta PM2.5 
    test_pm_data = hamta_pm25( 
        test_start, 
        test_slut, 
        cfg.pm25_tidsserie_id, 
        cfg.luft_api,testvagar["test_pm25"], 
        ) 
    
    generate_csv(test_pm_data, testvagar["test_pm25"]) 
    
    log.info("PM2.5-testdata har hämtats och sparats.")
 
    # Hämta väder (latest-months) 
    test_vader_data = hamta_test_vader( 
        parametrar=cfg.vader_parametrar,
        test_start=test_start, 
        test_slut=test_slut, 
        station_id=cfg.vaderstation_id, 
        VADER_API=cfg.vader_api, 
        )
    
    generate_csv(test_vader_data, testvagar["test_vader"]) 
    
    log.info("Vädertestdata har hämtats och sparats.")

    # Slå ihop PM2.5 och väder 
    merge_df_and_generate_csv( 
        testvagar["test_pm25"], 
        testvagar["test_vader"], 
        "tid",
        testvagar["test_merged"], 
        False, 
        ) 
    
    log.info("Testdata för PM2.5 och väder har sammanfogats.") 
    return testvagar


def build_processed_dataset(cfg, merged_df, output_path, mal_vader):
    """
    Bearbetar ett sammanslaget dataset: validering, features, target och
    dropna. Loggar en datakontroll och sparar resultatet i output_path.
    mal_vader=True innebär att väderkolumnerna ersätts med måltidsväder:
    vädrets värde på rad T kommer från T + horisont, dvs. när PM2.5-målet
    realiseras. Används för den förskjutna modellinjen.
    """

    log.info("Bearbetar dataset: %s", output_path.name)
 
    antal_merged = len(merged_df)
 
    # Validera data
    df = validate_data(merged_df)
    antal_validerad = len(df)
 
    if mal_vader:
        # Vindriktning skiftas FÖRE add_wind_features, så att vind_sin/
        # vind_cos räknas ur måltids-vindriktningen. Skiftet använder
        # alltid horisonten: måltiden är T + horisont, samma som mål-
        # skiftet, så vädret och målet kan aldrig hamna ur fas.

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
 
 
def build_processed_datasets(cfg, testvagar):
    """
    Bygger de sex bearbetade dataseten: train, val och test, både för den
    vanliga linjen och för den förskjutna linjen (måltidsväder).
    """

    # Läs in de sammanfogade dataseten
    train_merged_df = pd.read_csv(cfg.train_merged)
    val_merged_df = pd.read_csv(cfg.val_merged)
    test_merged_df = pd.read_csv(testvagar["test_merged"])
 
    # (sökväg att spara till, måltidsväder?) -> sammanslaget dataset

    merged_data = {
        (cfg.train_processed, False): train_merged_df,
        (cfg.val_processed, False): val_merged_df,
        (testvagar["test_processed"], False): test_merged_df,
        (cfg.train_processed_forskjuten, True): train_merged_df,
        (cfg.val_processed_forskjuten, True): val_merged_df,
        (testvagar["test_processed_forskjuten"], True): test_merged_df,
    }
 
    for (output_path, mal_vader), merged_df in merged_data.items():
        build_processed_dataset(cfg, merged_df, output_path, mal_vader)
 
