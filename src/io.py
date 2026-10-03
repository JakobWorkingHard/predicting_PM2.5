import pandas as pd


def generate_csv(data, path_and_name_of_csv):
    "Tar emot data samt din output fil samt namn"
    "på vad du vill att din csv ska heta. "
    "Exempel: generate_csv(df, data/raw/joakim.csv)"

    return data.to_csv(path_and_name_of_csv, index=True)