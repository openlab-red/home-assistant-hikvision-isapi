"""This component encapsulates the Hikvision ISAPI."""
from __future__ import annotations

from collections.abc import Mapping
from http import HTTPStatus
import logging
from typing import Any
from urllib.parse import urlparse

from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.device_registry import format_mac
from hikvision_isapi_cli.client import Client
from hikvision_isapi_sk.session import Session
from hikvision_isapi_cli.api.default import session_heartbeat
from hikvision_isapi_cli.api.isapi import usercheck, deviceinfo
from hikvision_isapi_cli.models import (
    RootTypeForXMLDeviceInfo,
    RootTypeForXMLDeviceInfoDeviceInfo,
)
from .const import CONF_VERIFY_SSL, MANUFACTURER, DEFAULT_TIMEOUT

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
        self._hostname = urlparse(config[CONF_HOST]).hostname

        self._api = Client(
            base_url=self._base_url,
            username=config[CONF_USERNAME],
            password=config[CONF_PASSWORD],
            verify_ssl=config[CONF_VERIFY_SSL],
            timeout=DEFAULT_TIMEOUT,
        )
        self._session = Session(self._api)

    @property
    def unique_id(self) -> str:
        """Create the unique ID, base for all entities."""
        return self._unique_id

    @property
    def api(self):
        """Return the API object."""
        return self._api

    @property
    def hostname(self):
        """Return the device Hostname."""
        return self._hostname

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
            hw_version=self._device_info.hardware_version,
            sw_version=self._device_info.firmware_version
            + "_"
            + self._device_info.firmware_released_date,
        )

    async def async_init(self) -> bool:
        """Connect to Hikvision host."""

        if not await usercheck.asyncio(client=self._api):
            return False

        self._session.start()
        device: RootTypeForXMLDeviceInfo = await deviceinfo.asyncio(client=self._api)

        if device.device_info.mac_address is None:
            return False

        self._unique_id = format_mac(device.device_info.mac_address)
        self._device_info = device.device_info

        _LOGGER.info("Device initialized %s", self.device_info["name"])

        return True

    async def stop(self) -> bool:
        """Stop the Hikvision session"""
        self._session.stop()
        return True

    async def update_states(self) -> bool:
        """Keep Hikvision alive ."""
        return await self._session.heartbeat()
