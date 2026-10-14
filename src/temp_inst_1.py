#Daniel, först, lägg till 

append_datakontroll_log, 

till nedanstående import högst upp i orchestrator.py
 
from src.io import (
    generate_csv,
    merge_df_and_generate_csv,
    forskjut_tid_csv,
    save_champion_model,
    append_champion_log,
    champion_is_fresh,
)

# Och istället för nedanstående kod i orchestrator.py (under 3B)

   for key, value in merged_data.items():
        df = validate_data(value)
        df = add_wind_features(df)
        df = add_time_features(df, cfg.horisont)
        df[cfg.target_column] = df["pm25"].shift(-cfg.horisont)
        df = df.dropna()
        cfg.processed_dir.mkdir(parents=True, exist_ok=True)
        generate_csv(df, key, index=False)


# så skriver du in: 

    for key, value in merged_data.items():
        antal_merged = len(value)

        df = validate_data(value)
        antal_validerad = len(df)

        df = add_wind_features(df)
        df = add_time_features(df, cfg.horisont)
        df[cfg.target_column] = df["pm25"].shift(-cfg.horisont)

        # Kolumnerna som modellen faktiskt använder
        modellkolumner = list(cfg.features) + [cfg.target_column]
        saknade = df[modellkolumner].isna().sum()

        df = df.dropna(subset=modellkolumner)

        append_datakontroll_log(
            cfg.datakontroll_log, key.name,
            antal_merged, antal_validerad, len(df), saknade,
        )

        cfg.processed_dir.mkdir(parents=True, exist_ok=True)
        generate_csv(df, key, index=False)