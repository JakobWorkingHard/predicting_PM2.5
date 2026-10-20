# Hämtar PM2.5 samt väder och slår ihop dem. 
# Merged används på både train och val

from src.extracting_data import hamta_pm25, vader_data
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


