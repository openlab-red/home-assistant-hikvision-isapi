"""Config flow for the Hikvision component."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries, core, exceptions
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_VERIFY_SSL, DOMAIN
from .host import HikvisionHost

_LOGGER = logging.getLogger(__name__)


class HikvisionOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Hikvision options."""

    def __init__(self, config_entry):
        """Initialize HikvisionOptionsFlowHandler."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the Hikvision options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
        )


class HikvisionFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hikvision device."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HikvisionOptionsFlowHandler:
        """Options callback for Hikvision."""
        return HikvisionOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            try:
                host = await async_obtain_host_settings(self.hass, user_input)
            except CannotConnect:
                errors[CONF_HOST] = "cannot_connect"
            except CredentialsInvalidError:
                errors[CONF_HOST] = "invalid_auth"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                placeholders["error"] = str(err)
                errors[CONF_HOST] = "unknown"

            if not errors:
                await self.async_set_unique_id(host.unique_id, raise_on_progress=False)
                self._abort_if_unique_id_configured(updates=user_input)

                return self.async_create_entry(
                    title=str(host.device_info["name"]),
                    data=user_input,
                    options={},
                )

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME, default="admin"): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_HOST, default="http://192.0.0.65"): str,
                vol.Optional(CONF_PORT, default=8000): cv.positive_int,
                vol.Optional(CONF_VERIFY_SSL, default=False): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders=placeholders,
        )


async def async_obtain_host_settings(
    hass: core.HomeAssistant, user_input: dict
) -> HikvisionHost:
    """Initialize the Hikvision host and get the host information."""
    host = HikvisionHost(hass, user_input, {})

    try:
        if not await host.async_init():
            raise CannotConnect
    finally:
        await host.stop()

    return host


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class CredentialsInvalidError(exceptions.HomeAssistantError):
    """Error to indicate invalid credentials."""
