import argparse
from pathlib import Path

from src.config import load_config
from src.logger import setup_logger
from src.predict_pipeline import kor_live_prediktion, folj_uppa


log = setup_logger(__name__)

# Räkna ut projektets rotkatalog dynamiskt
PROJEKT_ROT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Live-prediktioner för PM2.5")
    parser.add_argument(
        "--uppföljning",
        action="store_true",
        help="Rätta loggade prediktioner mot verkliga mätningar (steg 11)",
    )
    args = parser.parse_args()

    log.info("Startar live-prediktion")
    cfg = load_config(PROJEKT_ROT / "config.toml", PROJEKT_ROT)

    if args.uppföljning:
        folj_uppa(cfg)
    else:
        kor_live_prediktion(cfg)

    log.info("Live-körningen är klar")


if __name__ == "__main__":
    main()