# Hämtar PM2.5 samt väder och slår ihop dem. 
# Merged används på både train och val

from src.extracting_data import hamta_pm25, vader_data, hamta_testperiod, hamta_test_vader
from src.config import skapa_testvagar
from src.io import generate_csv, merge_df_and_generate_csv
from src.logger import setup_logger 


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


