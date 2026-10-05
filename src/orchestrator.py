import pandas as pd
from src.extracting_data import (
    hamta_pm25,
    vader_data
)
from src.io import generate_csv, merge_df_and_generate_csv
from src.config import ProjectConfig

def orchestration(cfg: ProjectConfig):

    # Bygg ihop den fullständiga sökvägen till raw-data filerna
    # den mergade datan
    train_pm25_path = cfg.raw_dir / f"train_{cfg.pm25_station}.csv"
    train_vader_path = cfg.raw_dir / f"train_{cfg.vaderstation}.csv"
    train_merged_path = cfg.merged_dir/ "train_merged.csv"
    
    # Checka om raw data INTE finns
    # och om de inte finns så startar vi hämtningen av väder och pm2.5 data
    if not train_pm25_path.is_file():
        print(f"Saknar filen: {train_pm25_path}. Hämtar pm2.5 data...")
        train_pm_data = hamta_pm25(cfg.train_start, cfg.train_slut, cfg.pm25_tidsserie_id, cfg.luft_api)
        generate_csv(train_pm_data, train_pm25_path)
        print(f"Sparat {train_pm25_path}")

    if not train_vader_path.is_file():
        print(f"Saknar filen: {train_vader_path}. Hämtar väder data...")
        train_vader_data = vader_data(
            cfg.vader_parametrar, 
            cfg.train_start, 
            cfg.train_slut, 
            cfg.vaderstation_id, 
            cfg.vader_api
            )
        generate_csv(train_vader_data, train_vader_path)
        print(f"Sparat {train_vader_path}")

    # Checka om den mergade datan INTE finns
    # och om den ej finns så påbörjas merge mellan våra två raw-data filer
    if not train_merged_path.is_file():
        print(f"Saknar mergade raw-datan: {train_merged_path}. Sätter ihop {train_pm25_path} med {train_vader_path}")
        pm_df = pd.read_csv(train_pm25_path)
        vader_df = pd.read_csv(train_vader_path)
        merge_df_and_generate_csv(pm_df, vader_df, "tid", train_merged_path, False)
        print(f"Genererat {train_merged_path}")

    else:
        print("Alla datafiler finns")
        
