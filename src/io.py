import pandas as pd


def generate_csv(data, path_and_name_of_csv, index = True):
    """Försöker spara en DataFrame till en CSV-fil. 
    Om filen redan existerar, görs ingenting.
    """
    try:
        # mode='x' gör att pandas kastar ett FileExistsError om filen redan finns
        data.to_csv(path_and_name_of_csv, mode='x', index=index)
        print(f"Skapade och fyllde ny fil: {path_and_name_of_csv,}")
        
    except FileExistsError:
        # Filen finns redan, vi avbryter tyst
        pass

def merge_df_and_generate_csv(data1_path, data2_path, on_column: str, path_and_name_of_csv, index, how = "outer"):
    """ Tar emot två df filer och mergar ihop dessa baserat på
    kolumn: on_column
    genererar sedan en mergad csv
    NOTERING: Fungerar endast om kolumnamnen är detsamma i båda dfs:en"""
    if path_and_name_of_csv.is_file():
        return None

    df1 = pd.read_csv(data1_path)
    df2 = pd.read_csv(data2_path)
    merged_df = pd.merge(df1, df2, on=on_column, how=how)
    return generate_csv(merged_df, path_and_name_of_csv, index)


def forskjut_tid_csv(input_path, output_path, hours=-6):
    "Läser en CSV med tidskolumnen 'tid', förskjuter tiden med 'hours' timmar och sparar ny CSV."
    if output_path.is_file():
        return pd.read_csv(output_path)

    hours = hours * (-1)
    df = pd.read_csv(input_path)
    df["tid"] = (
        pd.to_datetime(df["tid"], utc=True)
          .dt.tz_convert("Europe/Stockholm")
          + pd.Timedelta(hours=hours)
    )
    df.set_index("tid").to_csv(output_path, index=True)

