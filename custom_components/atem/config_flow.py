"""Config flow for the Blackmagic ATEM integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_NAME

from .const import DEFAULT_NAME, DOMAIN
from .coordinator import async_probe

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_NAME): str,
    }
)


class AtemConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Blackmagic ATEM."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host: str = user_input[CONF_HOST]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            try:
                model = await async_probe(self.hass, host)
            except Exception:  # noqa: BLE001 - library raises broad errors
                _LOGGER.debug("Cannot connect to ATEM at %s", host, exc_info=True)
                errors["base"] = "cannot_connect"
            else:
                title = user_input.get(CONF_NAME) or model or DEFAULT_NAME
                return self.async_create_entry(
                    title=title,
                    data={CONF_HOST: host, CONF_NAME: title},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
