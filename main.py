from pathlib import Path

from src.config import load_config
from src.orchestrator import orchestration
from src.logger import setup_logger

log = setup_logger(__name__)

# Räkna ut projektets rotkatalog dynamiskt
PROJEKT_ROT = Path(__file__).resolve().parent


def main():
    log.info("Startar PM2.5-projektets pipeline")

    cfg = load_config(PROJEKT_ROT / "config.toml", PROJEKT_ROT)

    log.info("Konfigurationen har laddats")

    orchestration(cfg)

    log.info("PM2.5-projektets pipeline har slutförts")


if __name__ == "__main__":
    main()