"""This component provides support for Hikvision IP cameras."""
from __future__ import annotations
from calendar import c

import logging

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from hikvision_isapi_cli.api.isapi import get_isapi_streaming_channels as streaming
from hikvision_isapi_cli.models import (
    RootTypeForXMLStreamingChannelListStreamingChannelList,
    RootTypeForXMLStreamingChannel,
)
from hikvision_isapi_sk.snap import RtspClient

from . import HikvisionData
from .const import DOMAIN, MANUFACTURER
from .entity import HikvisionCoordinatorEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up a Hikvision IP Camera."""
    hikvision_data: HikvisionData = hass.data[DOMAIN][config_entry.entry_id]
    host = hikvision_data.host

    cameras = []
    channels: RootTypeForXMLStreamingChannelListStreamingChannelList = (
        await streaming.asyncio(client=host.api)
    )
    for channel in channels.streaming_channel_list.streaming_channel:
        cameras.append(HikvisionCamera(hikvision_data, config_entry, channel))

    async_add_entities(cameras, update_before_add=True)


class HikvisionCamera(HikvisionCoordinatorEntity, Camera):
    """An implementation of a Hikvision IP camera."""

    _attr_supported_features: CameraEntityFeature = CameraEntityFeature.STREAM
    _attr_has_entity_name = True

    def __init__(
        self,
        hikvision_data: HikvisionData,
        config_entry: ConfigEntry,
        channel: RootTypeForXMLStreamingChannel,
    ) -> None:
        """Initialize Hikvision camera stream."""
        HikvisionCoordinatorEntity.__init__(self, hikvision_data, config_entry)
        Camera.__init__(self)

        self._stream = channel
        self._attr_name = f"{channel.channel_name}_{channel.video.constant_bit_rate}"
        self._attr_unique_id = (
            f"{self._host.unique_id}_{channel.id}_{channel.channel_name}"
        )
        self._attr_entity_registry_enabled_default = bool(channel.enabled)
        self._rtsp = RtspClient(
            client=self._host.api,
            rtsp_port=554,
            path=f"ISAPI/streaming/channels/{self._stream.video.video_input_channel_id}",
        )

    async def stream_source(self) -> str | None:
        """Return the source of the stream."""
        return self._rtsp.stream_source()

    # async def async_camera_image(
    #     self, width: int | None = None, height: int | None = None
    # ) -> bytes | None:
    #     """Return a still image response from the camera."""
    #     return await self._rtsp.get_snapshot()
    async def async_camera_image(self, width: int | None = None, height: int | None = None) -> bytes | None:
        return self._rtsp.get_snapshot(self._stream.id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info object."""

        return DeviceInfo(
            configuration_url=self._host.api.base_url,
            identifiers={self._attr_unique_id},
            connections=self._host.device_info["connections"],
            name=self._attr_name,
            manufacturer=MANUFACTURER,
            model=self._host.device_info["model"],
            sw_version=self._host.device_info["sw_version"],
            hw_version=self._host.device_info["hw_version"],
            via_device=(DOMAIN, self._host.unique_id),
        )
