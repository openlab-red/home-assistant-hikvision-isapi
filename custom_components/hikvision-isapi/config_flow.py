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
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
)

from .const import (
    CONF_VERIFY_SSL,
    CONF_DOOR_LATCH,
    DOMAIN,
    CONF_KEEPALIVE,
    DEFAULT_USERNAME,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_VERIFY_SSL,
    DEFAULT_DOOR_LATCH,
    DEFAULT_KEEPALIVE,
)

from .host import HikvisionHost

_LOGGER = logging.getLogger(__name__)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): cv.positive_int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_DOOR_LATCH, default=DEFAULT_DOOR_LATCH): cv.positive_int,
        vol.Optional(CONF_KEEPALIVE, default=DEFAULT_KEEPALIVE): cv.positive_int,
    }
)
OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(OPTIONS_SCHEMA),
}


class HikvisionOptionsFlow(config_entries.OptionsFlow):
    """Handle options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            errors = {}
            placeholders = {}
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
            return self.async_create_entry(
                title=str(host.device_info["name"]), data=user_input
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=self.config_entry.options.get(
                            CONF_USERNAME,
                            self.config_entry.data.get(CONF_USERNAME, DEFAULT_USERNAME),
                        ),
                    ): cv.string,
                    vol.Required(
                        CONF_PASSWORD,
                        default=self.config_entry.options.get(
                            CONF_PASSWORD,
                            self.config_entry.data.get(CONF_PASSWORD),
                        ),
                    ): cv.string,
                    vol.Required(
                        CONF_HOST,
                        default=self.config_entry.options.get(
                            CONF_HOST,
                            self.config_entry.data.get(CONF_HOST, DEFAULT_HOST),
                        ),
                    ): cv.string,
                    vol.Required(
                        CONF_PORT,
                        default=self.config_entry.options.get(
                            CONF_PORT,
                            self.config_entry.data.get(CONF_PORT, DEFAULT_PORT),
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_VERIFY_SSL,
                        default=self.config_entry.options.get(
                            CONF_VERIFY_SSL,
                            self.config_entry.data.get(
                                CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL
                            ),
                        ),
                    ): cv.boolean,
                    vol.Optional(
                        CONF_DOOR_LATCH,
                        default=self.config_entry.options.get(
                            CONF_DOOR_LATCH,
                            self.config_entry.data.get(CONF_DOOR_LATCH, DEFAULT_DOOR_LATCH),
                        ),
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_KEEPALIVE,
                        default=str(
                            self.config_entry.options.get(
                                CONF_KEEPALIVE,
                                self.config_entry.data.get(CONF_KEEPALIVE, DEFAULT_KEEPALIVE),
                            ),
                        ),
                    ): cv.positive_int,
                }
            ),
        )


class HikvisionFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hikvision device."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return HikvisionOptionsFlow(config_entry)

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

        return self.async_show_form(
            step_id="user",
            data_schema=OPTIONS_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )


async def async_obtain_host_settings(
    hass: core.HomeAssistant, user_input: dict
) -> HikvisionHost:
    """Initialize the Hikvision host and get the host information."""
    host = HikvisionHost(hass, user_input, {})
    if not await host.async_init():
        raise CannotConnect
    return host


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class CredentialsInvalidError(exceptions.HomeAssistantError):
    """Error to indicate invalid credentials."""
