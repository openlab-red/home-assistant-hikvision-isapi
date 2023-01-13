"""This component encapsulates the Hikvision ISAPI."""
from __future__ import annotations

from collections.abc import Mapping
import logging
import attr
from typing import Any

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import format_mac
from hikvision_isapi_cli.client import DigestAuthClient
from hikvision_isapi_cli.api.isapi import usercheck, deviceinfo
from hikvision_isapi_cli.models import (
    RootTypeForXMLDeviceInfo,
    RootTypeForXMLDeviceInfoDeviceInfo,
)
from .const import CONF_VERIFY_SSL, DEFAULT_TIMEOUT, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class HikvisionHost:
    """The implementation of the Hikvision Host class."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: Mapping[str, Any],
        options: Mapping[str, Any],
    ) -> None:
        """Initialize Hikvision Host."""
        self._hass: HomeAssistant = hass
        self._unique_id: str = ""
        self._device_info: RootTypeForXMLDeviceInfoDeviceInfo
        self._base_url = config[CONF_HOST] + ":" + str(config[CONF_PORT])

        self._api = DigestAuthClient(
            base_url=self._base_url,
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
            verify_ssl=config[CONF_VERIFY_SSL],
            timeout=DEFAULT_TIMEOUT,
        )

    @property
    def unique_id(self) -> str:
        """Create the unique ID, base for all entities."""
        return self._unique_id

    @property
    def api(self):
        """Return the API object."""
        return self._api

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info object."""

        return DeviceInfo(
            configuration_url=self._base_url,
            identifiers={self._unique_id},
            connections={(CONNECTION_NETWORK_MAC, self._unique_id)},
            name=self._device_info.device_name,
            manufacturer=MANUFACTURER,
            model=self._device_info.model,
            sw_version=self._device_info.firmware_version
            + "_"
            + self._device_info.firmware_released_date,
        )

    async def async_init(self) -> bool:
        """Connect to Hikvision host."""

        if not await usercheck.asyncio(client=self._api):
            return False

        device: RootTypeForXMLDeviceInfo = await deviceinfo.asyncio(client=self._api)

        _LOGGER.info(device)

        if device.device_info.mac_address is None:
            return False

        self._unique_id = format_mac(device.device_info.mac_address)
        self._device_info = device.device_info

        return True

    async def stop(self) -> bool:
        """Not implemented (yet)"""
        return True

    async def update_states(self) -> bool:
        """Not implemented Check if there is endpoint for Hikvision states."""
        return True
