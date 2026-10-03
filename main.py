from pathlib import Path
from src.config import load_config
from src.orchestrator import orchestration

# Räkna ut projektets rotkatalog dynamiskt
PROJEKT_ROT = Path(__file__).resolve().parent

def main():
    cfg = load_config(PROJEKT_ROT / "config.toml", PROJEKT_ROT) 
    orchestration(cfg)

if __name__ == "__main__":
    main()