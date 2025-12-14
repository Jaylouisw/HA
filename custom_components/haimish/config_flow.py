"""Config flow for HAM Network Map integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_DISPLAY_NAME,
    CONF_PUBLIC_URL,
    CONF_DISCOVERY_SERVER,
    CONF_SHARE_LOCATION,
    DEFAULT_DISCOVERY_SERVER,
)

_LOGGER = logging.getLogger(__name__)


def _get_schema(hass: HomeAssistant, user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Get the data schema with defaults from Home Assistant config."""
    user_input = user_input or {}
    
    return vol.Schema({
        vol.Required(
            CONF_DISPLAY_NAME,
            default=user_input.get(CONF_DISPLAY_NAME, hass.config.location_name or "My Home")
        ): str,
        vol.Required(
            CONF_LATITUDE,
            default=user_input.get(CONF_LATITUDE, hass.config.latitude)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-90,
                max=90,
                step=0.000001,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Required(
            CONF_LONGITUDE,
            default=user_input.get(CONF_LONGITUDE, hass.config.longitude)
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=-180,
                max=180,
                step=0.000001,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Optional(
            CONF_PUBLIC_URL,
            default=user_input.get(CONF_PUBLIC_URL, "")
        ): str,
        vol.Required(
            CONF_DISCOVERY_SERVER,
            default=user_input.get(CONF_DISCOVERY_SERVER, DEFAULT_DISCOVERY_SERVER)
        ): str,
        vol.Required(
            CONF_SHARE_LOCATION,
            default=user_input.get(CONF_SHARE_LOCATION, True)
        ): bool,
    })


class HAMNetworkConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HAM Network Map."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate the discovery server URL
            if not user_input.get(CONF_DISCOVERY_SERVER, "").startswith(("http://", "https://")):
                errors[CONF_DISCOVERY_SERVER] = "invalid_url"
            
            if not errors:
                # Check for existing entry
                await self.async_set_unique_id(f"haimish_{user_input[CONF_DISPLAY_NAME]}")
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=user_input[CONF_DISPLAY_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_get_schema(self.hass, user_input),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HAMNetworkOptionsFlowHandler:
        """Get the options flow for this handler."""
        return HAMNetworkOptionsFlowHandler(config_entry)


class HAMNetworkOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for HAM Network Map."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_SHARE_LOCATION,
                    default=self.config_entry.data.get(CONF_SHARE_LOCATION, True)
                ): bool,
                vol.Required(
                    CONF_DISCOVERY_SERVER,
                    default=self.config_entry.data.get(CONF_DISCOVERY_SERVER, DEFAULT_DISCOVERY_SERVER)
                ): str,
            }),
        )
