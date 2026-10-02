"""Gemensamma inställningar för projektet."""

# Datakällor
LUFT_API = "https://datavardluft.smhi.se/52North/api"
VADER_API = "https://opendata-download-metobs.smhi.se/api/version/1.0"

# Prognoshorisont i timmar
HORISONT = 6

# Tidsperioder
TRAIN_START = "2023-05-26"  # när PM2.5-tidsserien startade
TRAIN_SLUT = "2025-12-31"
VALIDERING_START = "2026-01-01"
VALIDERING_SLUT = "2026-04-30"
TEST_START = "2026-05-01"  # hämtas inte under utvecklingen

# Det är ca 4 km mellan stationerna, men ingen mätstation närmare Malmö A mäter PM2.5
# Luftkvalitetsstation
PM25_STATION = "Malmö Dalaplan"
PM25_TIDSSERIE_ID = 6247  # aktiv sedan 2023-05-26, täcker hela perioden
PM25_LAT = 55.584747
PM25_LON = 13.006230

# Väderstation
VADERSTATION = "Malmö A"
VADERSTATION_ID = 52350  # SMHI CORE-station, data sedan 1990
VADER_LAT = 55.5715
VADER_LON = 13.0708