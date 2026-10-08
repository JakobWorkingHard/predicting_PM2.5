import pandas as pd
from src.extracting_data import (
    hamta_pm25,
    vader_data
)
from src.io import generate_csv, merge_df_and_generate_csv, forskjut_tid_csv
from src.config import ProjectConfig
from src.validate_process import preprocess_data

def orchestration(cfg: ProjectConfig):

    # Hämtar pm träningsdata alt. genererar en df om csv redan finns
    train_pm_data = hamta_pm25(cfg.train_start, cfg.train_slut, cfg.pm25_tidsserie_id, cfg.luft_api, cfg.train_pm25)
    generate_csv(train_pm_data, cfg.train_pm25)

    # Hämtar väderdata alt. genererar df om csv redan finns
    train_vader_data = vader_data(
        cfg.vader_parametrar,
        cfg.train_start,
        cfg.train_slut,
        cfg.vaderstation_id,
        cfg.vader_api,
        cfg.train_vader
        )
    generate_csv(train_vader_data, cfg.train_vader)

    # Mergar pm2.5 och väderdata (om mergad csv ej redan finns)
    merge_df_and_generate_csv(cfg.train_pm25, cfg.train_vader, "tid", cfg.train_merged, False)

    # Preprocessa den sammanfogade träningsdatan
    merged_df = pd.read_csv(cfg.train_merged)

    processed_df = preprocess_data(merged_df)

    # Spara den bearbetade datan
    if not cfg.train_processed.is_file():
        cfg.processed_dir.mkdir(parents=True, exist_ok=True)
        processed_df.to_csv(cfg.train_processed, index=False)


    # Förskjuter tidsserien med horisont om förskjuten tidsserie ej redan finns
    forskjut_tid_csv(cfg.train_vader, cfg.train_vader_forskjuten, cfg.horisont)
    # Mergar pm2.5 och Förskjuten väderdata (om mergad  csv ej redan finns)
    merge_df_and_generate_csv(cfg.train_pm25, cfg.train_vader_forskjuten, "tid", cfg.train_merged_forskjuten, False)

    

    