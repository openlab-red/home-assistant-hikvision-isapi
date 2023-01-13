import logging

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from . import HikvisionData
from hikvision_isapi_cli.errors import UnexpectedStatus
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
        self._lock = lock
        self._latch = latch
        self._is_locked = True

    def lock(self, **kwargs):
        _LOGGER.warning("Locking not implemented")

    def unlock(self, **kwargs):
        _LOGGER.warning("Unlocking not implemented")

    def open(self, **kwargs):
        raise NotImplementedError()

    async def async_lock(self, **kwargs):
        self._is_locked = True
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        try:
            request = RootTypeForXMLRemoteControlDoor()
            request.remote_control_door = (
                RootTypeForXMLRemoteControlDoorRemoteControlDoor()
            )
            request.remote_control_door.cmd = "open"
            request.remote_control_door.version = "2.0"
            request.remote_control_door.xmlns = "http://www.isapi.org/ver20/XMLSchema"

            await door.asyncio(
                door_id=self._lock, client=self._host.api, json_body=request
            )

            async def _lock_later(_now):
                await self.async_lock()

            self._is_locked = False
            async_call_later(self.hass, delay=self._latch, action=_lock_later)
            self.async_write_ha_state()
        except (UnexpectedStatus, Exception) as err:
            raise ConfigEntryError(
                f'Error while trying to unlock door: {self._lock} host: {self._host.api.base_url}: "{str(err)}".'
            ) from err

    async def async_open(self, **kwargs):
        return await self.async_unlock()

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
            identifiers={self.unique_id},
            connections=self._host.device_info["connections"],
            name=self.name,
            manufacturer=MANUFACTURER,
            model=self._host.device_info["model"],
            sw_version=self._host.device_info["sw_version"],
            via_device=(DOMAIN, self._host.unique_id),
        )

    @property
    def assumed_state(self):
        return True

    @property
    def icon(self):
        return "mdi:lock"
