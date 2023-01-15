from http import HTTPStatus
import logging
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import HikvisionData
from hikvision_isapi_cli.errors import UnexpectedStatus
from hikvision_isapi_cli.types import Response
from hikvision_isapi_cli.api.isapi import door
from hikvision_isapi_cli.models import (
    RootTypeForXMLRemoteControlDoor,
    RootTypeForXMLRemoteControlDoorRemoteControlDoor,
)
from .const import DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class HikvisionCoordinatorEntity(CoordinatorEntity):
    """Parent class for Hikvision Entities."""

    def __init__(
        self,
        hikvision_data: HikvisionData,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize HikvisionCoordinatorEntity."""
        coordinator = hikvision_data.device_coordinator
        super().__init__(coordinator)

        self._host = hikvision_data.host


class HikvisionLock(HikvisionCoordinatorEntity, LockEntity):
    """
    Represents a single door lock for Hikvision device.
    """

    def __init__(
        self,
        hikvision_data: HikvisionData,
        config_entry: ConfigEntry,
        lock: int,
        latch: int,
    ) -> None:
        """Initialize Hikvision door channel."""
        HikvisionCoordinatorEntity.__init__(self, hikvision_data, config_entry)
        LockEntity.__init__(self)
        self._attr_supported_features = LockEntityFeature(1)
        self._attr_is_locked = True
        self._lock = lock
        self._latch = latch

    async def async_open(self, **kwargs: Any) -> None:
        self.unlock(**kwargs)

    async def _lock_delay(self, _now):
        self._attr_is_locking = True
        self.async_write_ha_state()
        await self.async_lock()

    async def _locked(self, _now, **kwargs):
        """Set Lock Entity status to locked."""
        self._attr_is_locking = False
        self._attr_is_locked = True
        self.async_write_ha_state()

    async def async_lock(self, **kwargs: Any) -> None:
        if self._latch > 0:
            if self._attr_is_locked:
                await self.async_unlock(**kwargs)
            else:
                async_call_later(self.hass, delay=self._latch, action=self._locked)

    async def async_unlock(self, **kwargs: Any) -> None:
        try:
            self._attr_is_unlocking = True
            self.async_write_ha_state()
            request = RootTypeForXMLRemoteControlDoor()
            request.remote_control_door = (
                RootTypeForXMLRemoteControlDoorRemoteControlDoor()
            )
            request.remote_control_door.cmd = "open"
            request.remote_control_door.version = "2.0"
            request.remote_control_door.xmlns = "http://www.isapi.org/ver20/XMLSchema"

            response: Response = await door.asyncio_detailed(
                door_id=self._lock, client=self._host.api, json_body=request
            )

            if response.status_code == HTTPStatus.OK:
                self._attr_is_unlocking = False
                self._attr_is_locked = False
                self.async_write_ha_state()
                if self._latch > 0:
                    async_call_later(
                        self.hass, delay=self._latch, action=self._lock_delay
                    )
            else:
                self._attr_is_locked = True
                _LOGGER.error(response.content)

        except (UnexpectedStatus, Exception) as err:
            raise ConfigEntryError(
                f'Error while trying to unlock door: {self._lock} host: {self._host.api.base_url}: "{str(err)}".'
            ) from err

    @property
    def name(self):
        name = f"{self._host.device_info['name']} "
        if self._lock is not None:
            name += f" {self._lock}"
        return name

    @property
    def unique_id(self):
        return "-".join(
            (
                DOMAIN,
                self._host.unique_id,
                str(self._lock),
            )
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info object."""

        return DeviceInfo(
            configuration_url=self._host.api.base_url,
            identifiers={self.unique_id},
            connections=self._host.device_info["connections"],
            name=self.name,
            manufacturer=MANUFACTURER,
            model=self._host.device_info["model"],
            hw_version=self._host.device_info["hw_version"],
            sw_version=self._host.device_info["sw_version"],
            via_device=(DOMAIN, self._host.unique_id),
        )

    @property
    def assumed_state(self):
        return True

    @property
    def icon(self):
        return "mdi:lock"
