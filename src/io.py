import pandas as pd


def generate_csv(data, path_and_name_of_csv, index = True):
    "Tar emot data samt din output fil samt namn"
    "på vad du vill att din csv ska heta. "
    "Exempel: generate_csv(df, data/raw/joakim.csv)"

    return data.to_csv(path_and_name_of_csv, index=index)

def merge_df_and_generate_csv(df1, df2, on_column: str, path_and_name_of_csv, index, how = "outer"):
    " Tar emot två df filer och mergar ihop dessa baserat på"
    "kolumn: on_column"
    "genererar sedan en mergad csv"
    "NOTERING: Fungerar endast om kolumnamnen är detsamma i båda dfs:en"
    merged_df = pd.merge(df1, df2, on=on_column, how=how)
    return generate_csv(merged_df, path_and_name_of_csv, index)

    
