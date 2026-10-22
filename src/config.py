from dataclasses import dataclass
from pathlib import Path
import tomllib
import pandas as pd





@dataclass(frozen=True)
class ProjectConfig:
    # Mappar
    raw_dir: Path
    merged_dir: Path
    validated_dir: Path
    processed_dir: Path
    models_dir: Path
    champion_log: Path
    datakontroll_log: Path

    # Fullständiga sökvägar till specifika filer
    train_pm25: Path
    train_vader: Path
    train_merged: Path
    train_validated: Path
    train_processed: Path

    # Valideringsdata
    val_pm25: Path
    val_vader: Path
    val_merged: Path
    val_validated: Path
    val_processed: Path

    # Förskjuten modellinje (måltidsväder)
    train_processed_forskjuten: Path
    val_processed_forskjuten: Path
    forskjuten_log: Path
    jamfordelse_log: Path
    forskjuten_vaderkolumner: list
    forskjuten_antal_dagar_sedan: int

    
    # API:er
    luft_api: str
    vader_api: str

    # Modell
    horisont: int
    features: list
    selection_metric: str
    random_state: int
    target_column: str
    antal_dagar_sedan: int

    # Tidsperioder
    train_start: str
    train_slut: str
    validering_start: str
    validering_slut: str

    # PM2.5 Station
    pm25_station: str
    pm25_tidsserie_id: int
    pm25_lat: float
    pm25_lon: float

    # Väderstation
    vaderstation: str
    vaderstation_id: int
    vader_lat: float
    vader_lon: float
    vader_parametrar: dict

    # Live-prediktioner
    prognos_dir: Path
    prediktioner_log: Path
    prognos_url: str           # färdig formaterad: väderstationens lon/lat insatta
    prognos_arkiv_timmar: int   # ARKIV, EJ PREDIKTION: trimmad arkiv-CSV:n i prognos_dir
    max_alder_timmar: int
    idempotent: bool
    prognos_parametrar: dict

    # Testdata – sökvägar skapas när testperioden har beräknats
    test_pm25: Path | None = None
    test_vader: Path | None = None
    test_merged: Path | None = None
    test_validated: Path | None = None
    test_processed: Path | None = None
    

def load_config(PATH_CONFIG_TOML: Path, PATH_PROJECT_ROOT: Path ) -> ProjectConfig:
    from src.extracting_data import hamta_senaste_arkivtid

    with open(PATH_CONFIG_TOML, "rb") as f:
        raw = tomllib.load(f)

    p = raw["paths"]
    fn = raw["paths"]["filenames"]
    api = raw["api"]
    mod = raw["model"]
    fork = raw["model"]["forskjuten"]
    t = raw["time"]
    pm25 = raw["station"]["pm25"]
    vader = raw["station"]["vader"]
    live = raw["live"]

    # Baskataloger
    raw_dir = PATH_PROJECT_ROOT / p["raw_dir"]
    merged_dir = PATH_PROJECT_ROOT / p["merged_dir"]
    validated_dir = PATH_PROJECT_ROOT / p["validated_dir"]                      
    processed_dir = PATH_PROJECT_ROOT / p["processed_dir"]
    models_dir=PATH_PROJECT_ROOT / p["models_dir"]

    # Skapa datakatalogerna (inkl. data/) om de saknas – t.ex. vid fresh
    # clone, eftersom data/ är gitignored. parents=True skapar huvudkatalogen
    # data/ automatiskt. Sker innan något API-anrop görs (se hamta_senaste_arkivtid
    # längre ner), så katalogerna finns på plats oavsett hur API-hämtningen går.
    for katalog in (raw_dir, merged_dir, validated_dir, processed_dir):
        katalog.mkdir(parents=True, exist_ok=True)
    champion_log = PATH_PROJECT_ROOT / p["champion_log"]
    forskjuten_log = PATH_PROJECT_ROOT / p["forskjuten_log"]
    datakontroll_log = PATH_PROJECT_ROOT / p["datakontroll_log"]
    jamfordelse_log = PATH_PROJECT_ROOT / p["jamfordelse_log"]

    # Live-prediktioner
    prognos_dir = PATH_PROJECT_ROOT / live["prognos_dir"]
    prediktioner_log = PATH_PROJECT_ROOT / live["prediktioner_log"]
    prognos_url = live["prognos_url"].format(LON=vader["lon"], LAT=vader["lat"])
    prognos_parametrar = live["prognos_parametrar"]

    # Sanity: prognosparametrarna måste mappa samma väderkolumner som
    # träningen använder, annars glider live och träning isär.
    for kalla, kolumner in (
        ("[model.forskjuten].vaderkolumner", fork["vaderkolumner"]),
        ("[station.vader].parametrar", list(vader["parametrar"])),
    ):
        if sorted(prognos_parametrar) != sorted(kolumner):
            raise ValueError(
                f"[live].prognos_parametrar matchar inte {kalla}: "
                f"{sorted(prognos_parametrar)} != {sorted(kolumner)}"
            )

    # Råvärden
    pm25_station = pm25["namn"]
    vaderstation = vader["namn"]

    # Fast startdatum för PM2.5-serien
    train_start = t["train_start"]

    # Stations- och tidsserie-ID
    pm25_tidsserie_id = pm25["tidsserie_id"]
    vaderstation_id = vader["id"]

    # Hämta senaste tillgängliga arkivtidpunkt
    senaste_arkivtid = hamta_senaste_arkivtid(
        parametrar=vader["parametrar"],
        station_id=vaderstation_id,
        VADER_API=api["vader"],
    )

    # Beräkna dynamiska tränings- och valideringsperioder
    perioder = berakna_tranings_och_valideringsperiod(
        senaste_arkivtid=senaste_arkivtid,
        train_start=train_start,
    )

    train_slut = perioder["train_slut"]
    validering_start = perioder["validering_start"]
    validering_slut = perioder["validering_slut"]

    logiska_datum = {
        "train_start": train_start,
        "train_slut": train_slut,
        "validering_start": validering_start,
        "validering_slut": validering_slut,
    }

    print("\nDynamiskt beräknade datum:")
    for namn, datum in logiska_datum.items():
        print(f"{namn}: {datum}")

    # Värden för filnamnsmallar (stationsnamn sanerade, övriga oförändrade)
    fmt = {
        "pm25_station": pm25_station.replace(" ", "_"),
        "vaderstation": vaderstation.replace(" ", "_"),
        "train_start": train_start,
        "train_slut": train_slut,
        "pm25_tidsserie_id": pm25_tidsserie_id,
        "vaderstation_id": vaderstation_id,
        "horisont": mod["horisont"],
        "validering_start": validering_start,
        "validering_slut": validering_slut,
    }






    return ProjectConfig(
        # Mappar
        raw_dir=raw_dir,
        merged_dir=merged_dir,
        validated_dir=validated_dir,
        processed_dir=processed_dir,
        models_dir = models_dir,
        champion_log=champion_log,
        datakontroll_log=datakontroll_log,

        # Fullständiga sökvägar till träningsdata
        train_pm25=raw_dir / fn["train_pm25"].format(**fmt),
        train_vader=raw_dir / fn["train_vader"].format(**fmt),
        train_merged=merged_dir / fn["train_merged"].format(**fmt),
        train_validated=validated_dir / fn["train_validated"].format(**fmt),
        train_processed=processed_dir / fn["train_processed"].format(**fmt),

        # Fullständiga sökvägar till valideringsdata
        val_pm25=raw_dir / fn["val_pm25"].format(**fmt),
        val_vader=raw_dir / fn["val_vader"].format(**fmt),
        val_merged=merged_dir / fn["val_merged"].format(**fmt),
        val_validated=validated_dir / fn["val_validated"].format(**fmt),
        val_processed=processed_dir / fn["val_processed"].format(**fmt),

        # Förskjuten modellinje (måltidsväder)
        train_processed_forskjuten=processed_dir / fn["train_processed_forskjuten"].format(**fmt),
        val_processed_forskjuten=processed_dir / fn["val_processed_forskjuten"].format(**fmt),
        forskjuten_log=forskjuten_log,
        jamfordelse_log=jamfordelse_log,
        forskjuten_vaderkolumner=fork["vaderkolumner"],
        forskjuten_antal_dagar_sedan=fork["antal_dagar_sedan"],

        # API:er
        luft_api=api["luft"],
        vader_api=api["vader"],

        # Modell
        horisont=mod["horisont"],
        features=mod["features"]["columns"],
        selection_metric=mod["selection_metric"],
        random_state=mod["random_state"],
        target_column=mod["target_column"],
        antal_dagar_sedan=mod["antal_dagar_sedan"],

        # Tidsperioder
        train_start=train_start,
        train_slut=train_slut,
        validering_start=validering_start,
        validering_slut=validering_slut,
        

        # PM2.5 Station
        pm25_station=pm25_station,
        pm25_tidsserie_id=pm25_tidsserie_id,
        pm25_lat=pm25["lat"],
        pm25_lon=pm25["lon"],

        # Väderstation
        vaderstation=vaderstation,
        vaderstation_id=vaderstation_id,
        vader_lat=vader["lat"],
        vader_lon=vader["lon"],
        vader_parametrar=vader["parametrar"],

        # Live-prediktioner
        prognos_dir=prognos_dir,
        prediktioner_log=prediktioner_log,
        prognos_url=prognos_url,
        prognos_arkiv_timmar=live["prognos_arkiv_timmar"],
        max_alder_timmar=live["max_alder_timmar"],
        idempotent=live["idempotent"],
        prognos_parametrar=prognos_parametrar,
    )

def berakna_tranings_och_valideringsperiod(
    senaste_arkivtid: pd.Timestamp,
    train_start: str,
) -> dict[str, str]:
    """
    Beräknar dynamiska tränings- och valideringsperioder.

    Valideringen består av de tre senaste fullständiga
    kalendermånaderna före den månad som latest_arcives tid tillhör.

    Träningen slutar dagen före valideringsperiodens start.
    """

    # Början av månaden för den senaste arkivtidpunkten
    aktuell_manad = senaste_arkivtid.normalize().replace(
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    # Valideringsperioden omfattar de tre föregående hela månaderna
    validering_slut = aktuell_manad - pd.Timedelta(days=1)
    validering_start = (
        aktuell_manad - pd.DateOffset(months=6)
    ).normalize()

    # Träningen slutar dagen före valideringen börjar
    train_slut = validering_start - pd.Timedelta(days=1)

    return {
        "train_start": train_start,
        "train_slut": train_slut.strftime("%Y-%m-%d"),
        "validering_start": validering_start.strftime("%Y-%m-%d"),
        "validering_slut": validering_slut.strftime("%Y-%m-%d"),
    }




def skapa_testvagar(
    cfg: ProjectConfig,
    test_start: pd.Timestamp,
    test_slut: pd.Timestamp,
) -> dict[str, Path]:
    """Skapar sökvägar för testfiler baserat på den dynamiska testperioden."""

    test_start_str = test_start.strftime("%Y-%m-%d")
    test_slut_str = test_slut.strftime("%Y-%m-%d")

    return {
        "test_pm25": cfg.raw_dir / (
            f"test_{cfg.pm25_station.replace(' ', '_')}_"
            f"{test_start_str}_{test_slut_str}_"
            f"pm25tidsserie_{cfg.pm25_tidsserie_id}.csv"
        ),
        "test_vader": cfg.raw_dir / (
            f"test_{cfg.vaderstation.replace(' ', '_')}_"
            f"{test_start_str}_{test_slut_str}_"
            f"vaderstationid_{cfg.vaderstation_id}.csv"
        ),
        "test_merged": cfg.merged_dir / (
            f"test_merged_{test_start_str}_{test_slut_str}_"
            f"pm25tidsserie_{cfg.pm25_tidsserie_id}_"
            f"vaderstationid_{cfg.vaderstation_id}.csv"
        ),
        "test_validated": cfg.validated_dir / (
            f"test_validated_{test_start_str}_{test_slut_str}.csv"
        ),
        "test_processed": cfg.processed_dir / (
            f"test_processed_{test_start_str}_{test_slut_str}.csv"
        ),
        "test_processed_forskjuten": cfg.processed_dir / (
            f"test_processed_forskjuten_{test_start_str}_{test_slut_str}"
            f"_h{cfg.horisont}.csv"
        ),
    }
