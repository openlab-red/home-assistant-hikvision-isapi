from typing import Final

DOMAIN: Final = "hikvision-isapi"
MANUFACTURER: Final = "Hikvision"
PLATFORMS: Final = ["lock", "sensor", "camera"]
BASE_URL: Final = "http://192.0.0.65:8000"

CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_DOOR_LATCH: Final = "latch"
CONF_KEEPALIVE: Final = "keepalive"

DEFAULT_TIMEOUT: Final = 30
DEFAULT_USERNAME: Final = "admin"
DEFAULT_HOST: Final = "http://192.0.0.65"
DEFAULT_PORT: Final = "8000"
DEFAULT_VERIFY_SSL: Final = False
DEFAULT_DOOR_LATCH: Final = 0
DEFAULT_KEEPALIVE: Final = 5
