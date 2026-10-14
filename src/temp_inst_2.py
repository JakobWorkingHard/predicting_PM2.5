# Daniel, längst ned i io.py filen, efter champion_is_fresh funktionen, lägg till följande funktion:

def append_datakontroll_log(log_path, dataset, antal_merged, antal_validerad, antal_kvar, saknade):
    """
    Skriver ut hur många rader som togs bort av dropna, och appendar
    samma information som en rad i datakontroll-loggen (CSV).
    Skapar filen med rubrikrad om den saknas.

    Parametrar
    ----------
    log_path : Path
        Sökväg till loggfilen, t.ex. "logs/datakontroll.csv".
    dataset : str
        Namn på datasetet, t.ex. filnamnet för train eller val.
    antal_merged : int
        Antal rader i den mergade filen.
    antal_validerad : int
        Antal rader efter validate_data. Kan vara fler än antal_merged,
        eftersom saknade timmar läggs till som tomma rader.
    antal_kvar : int
        Antal rader efter dropna.
    saknade : pd.Series
        Antal saknade värden per feature/target-kolumn, före dropna.
        En rad kan sakna flera värden, så summan kan vara större än
        antalet borttagna rader.
    """
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    borttagna = antal_validerad - antal_kvar
    andel = borttagna / antal_validerad

    # Utskrift i terminalen
    print(f"\n--- Datakontroll: {dataset} ---")
    print(f"Rader i mergad fil:          {antal_merged}")
    print(f"Rader efter validate_data:   {antal_validerad}")
    print(f"Rader efter dropna:          {antal_kvar}")
    print(f"Borttagna rader:             {borttagna} ({andel:.1%})")
    print("Saknade värden per kolumn (en rad kan sakna flera):")
    print(saknade[saknade > 0].to_string())

    # En rad i loggen. Alla kolumner tas med, även de med 0 saknade,
    # så att loggen har samma kolumner vid varje körning.
    rad = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "dataset": dataset,
        "rader_merged": antal_merged,
        "rader_validerad": antal_validerad,
        "rader_kvar": antal_kvar,
        "borttagna": borttagna,
        "andel_borttagna": round(andel, 4),
    }
    for kolumn, antal in saknade.items():
        rad[f"saknade_{kolumn}"] = int(antal)

    header = not log_path.is_file()
    pd.DataFrame([rad]).to_csv(log_path, mode="a", header=header, index=False)
    print(f"Loggade datakontroll i: {log_path}")

# Och i i config.toml, lägg till följande rad under [paths],
# direkt under raden champion_log = ...
# Raden måste ligga FÖRE rubriken [paths.filenames], annars hittas den inte.

datakontroll_log = "logs/datakontroll.csv"

# Därefter, i src/config.py, lägg till datakontroll_log på tre ställen,
# alltid direkt under champion_log:

# 1. I klassen ProjectConfig, under champion_log: Path
    datakontroll_log: Path

# 2. I load_config, under champion_log = PATH_PROJECT_ROOT / p["champion_log"]
    datakontroll_log = PATH_PROJECT_ROOT / p["datakontroll_log"]

# 3. I return ProjectConfig(...), under #Mappar och under champion_log=champion_log,
        datakontroll_log=datakontroll_log,

