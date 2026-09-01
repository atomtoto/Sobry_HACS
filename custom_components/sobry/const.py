"""Constants for the Sobry integration."""

DOMAIN = "sobry"
NAME = "Sobry Energy"

CONF_SEGMENT = "segment"
CONF_TURPE = "turpe"
CONF_PROFIL = "profil"
CONF_DISPLAY = "display"
CONF_GRANULARITY = "granularity"

DEFAULT_SEGMENT = "C5"
DEFAULT_TURPE = "CU4"
DEFAULT_PROFIL = "particulier"
DEFAULT_DISPLAY = "TTC"
DEFAULT_GRANULARITY = "quarter_hourly"

PLATFORMS = ["sensor"]

API_BASE_URL = "https://api.sobry.co"
