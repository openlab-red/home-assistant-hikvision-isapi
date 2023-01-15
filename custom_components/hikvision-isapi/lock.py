from http import HTTPStatus
from .const import CONF_DOOR_LATCH, DOMAIN

from datetime import timedelta
import logging
from httpx import TimeoutException

from homeassistant.exceptions import ConfigEntryNotReady

from . import HikvisionData

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from hikvision_isapi_cli.api.isapi import door_capabilities
from hikvision_isapi_cli.types import Response
from hikvision_isapi_cli.models import (
    RootTypeForXMLCapRemoteControlDoor,
)
from hikvision_isapi_cli.errors import UnexpectedStatus

from .entity import HikvisionLock

SCAN_INTERVAL = timedelta(seconds=30)
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hikvision Door Lock."""
    hikvision_data: HikvisionData = hass.data[DOMAIN][config_entry.entry_id]
    host = hikvision_data.host
    config = config_entry.data

    async def async_device_config_update():

        response: Response = await door_capabilities.asyncio_detailed(client=host.api)
        if response.status_code == HTTPStatus.OK:
            door_cap: RootTypeForXMLCapRemoteControlDoor = response.parsed
            doors = int(door_cap.remote_control_door.door_no.max_)
            _LOGGER.info(
                "Found %s Hikvision Door, for %s device",
                doors,
                host.device_info["name"],
            )

            locks = []
            for lock in range(doors):
                locks.append(
                    HikvisionLock(
                        hikvision_data,
                        config_entry,
                        lock + 1,
                        config[CONF_DOOR_LATCH],
                    )
                )

            if locks:
                async_add_entities(locks)
        else:
            _LOGGER.error(response)

    try:
        await async_device_config_update()
    except (UnexpectedStatus, TimeoutException) as err:
        raise ConfigEntryNotReady(
            f'Error while trying to setup {host.api.base_url}: "{str(err)}".'
        ) from err

    return True
