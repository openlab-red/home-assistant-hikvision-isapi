import dataclasses
import logging
import async_timeout
from datetime import timedelta


from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from hikvision_isapi_cli.errors import UnexpectedStatus

from .const import DOMAIN, MANUFACTURER, PLATFORMS
from .host import HikvisionHost

PLATFORMS = [Platform.LOCK, Platform.CAMERA, Platform.SENSOR]
DEVICE_UPDATE_INTERVAL = 30

_LOGGER = logging.getLogger(__name__)


@dataclass
class HikvisionData:
    """Data for the Hikvision integration."""

    host: HikvisionHost
    device_coordinator: DataUpdateCoordinator


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hikvision from a config entry."""
    host = HikvisionHost(hass, config_entry.data, config_entry.options)

    try:
        if not await host.async_init():
            raise ConfigEntryNotReady(
                f"Error while trying to setup {host.api.base_url}: "
                "failed to obtain data from device."
            )
    except (UnexpectedStatus,) as err:
        raise ConfigEntryNotReady(
            f'Error while trying to setup {host.api.base_url}: "{str(err)}".'
        ) from err

    config_entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, host.stop)
    )

    async def async_device_config_update():
        """Update the host state cache."""
        async with async_timeout.timeout(host.api.timeout):
            await host.update_states()

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=f"{MANUFACTURER}.{host.device_info['name']}",
        update_method=async_device_config_update,
        update_interval=timedelta(seconds=DEVICE_UPDATE_INTERVAL),
    )
    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = HikvisionData(
        host=host, device_coordinator=coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(
        config_entry.add_update_listener(entry_update_listener)
    )

    return True


async def entry_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Update the configuration of the host entity."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    host: HikvisionHost = hass.data[DOMAIN][config_entry.entry_id].host

    await host.stop()

    if unload_ok := await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    ):
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok
