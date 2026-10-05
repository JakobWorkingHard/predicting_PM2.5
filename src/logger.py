import logging
from pathlib import Path

def setup_logger(name: str = "pm25") -> logging.Logger:

    Path("logs").mkdir(exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(
        "logs/project.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger





#Test-sektion för logger

if __name__ == "__main__":
    logger = setup_logger()

    logger.debug("Detta är en debug-logg")
    logger.info("Detta är en info-logg")
    logger.warning("Detta är en warning-logg")
    logger.error("Detta är en error-logg")