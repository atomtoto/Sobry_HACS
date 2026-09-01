"""Config flow for Sobry integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_API_KEY,
    CONF_DISPLAY,
    CONF_GRANULARITY,
    CONF_PROFIL,
    CONF_SEGMENT,
    CONF_TAX_MODE,
    CONF_TURPE,
    DEFAULT_DISPLAY,
    DEFAULT_GRANULARITY,
    DEFAULT_PROFIL,
    DEFAULT_SEGMENT,
    DEFAULT_TAX_MODE,
    DEFAULT_TURPE,
    DOMAIN,
    NAME,
)

SEGMENTS = ["C5", "C4"]
TURPE_C5 = ["CU", "CU4", "MU4", "MUDT", "LU"]
TURPE_C4 = ["CU", "LU"]
PROFILS = ["particulier", "pro"]
DISPLAYS = ["TTC", "HT"]
GRANULARITIES = ["quarter_hourly", "hourly"]
TAX_MODES = ["ttc", "ht"]


class SobryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sobry."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if api_key:
                user_input[CONF_API_KEY] = api_key
            else:
                user_input.pop(CONF_API_KEY, None)

            if user_input[CONF_SEGMENT] == "C4":
                if user_input[CONF_TURPE] not in TURPE_C4:
                    user_input[CONF_TURPE] = "CU"
                user_input[CONF_PROFIL] = "pro"
                user_input[CONF_DISPLAY] = "HT"

            await self.async_set_unique_id("sobry")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=NAME, data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_SEGMENT, default=DEFAULT_SEGMENT): vol.In(SEGMENTS),
                vol.Required(CONF_TURPE, default=DEFAULT_TURPE): vol.In(TURPE_C5),
                vol.Required(CONF_PROFIL, default=DEFAULT_PROFIL): vol.In(PROFILS),
                vol.Required(CONF_DISPLAY, default=DEFAULT_DISPLAY): vol.In(DISPLAYS),
                vol.Required(CONF_GRANULARITY, default=DEFAULT_GRANULARITY): vol.In(GRANULARITIES),
                vol.Required(CONF_TAX_MODE, default=DEFAULT_TAX_MODE): vol.In(TAX_MODES),
                vol.Optional(CONF_API_KEY, default=""): str,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return SobryOptionsFlow(config_entry)


class SobryOptionsFlow(config_entries.OptionsFlow):
    """Sobry options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if api_key:
                user_input[CONF_API_KEY] = api_key
            else:
                user_input.pop(CONF_API_KEY, None)
            return self.async_create_entry(title="", data=user_input)

        data = {**self.config_entry.data, **self.config_entry.options}
        segment = data.get(CONF_SEGMENT, DEFAULT_SEGMENT)
        turpe_options = TURPE_C4 if segment == "C4" else TURPE_C5

        schema = vol.Schema(
            {
                vol.Required(CONF_SEGMENT, default=segment): vol.In(SEGMENTS),
                vol.Required(CONF_TURPE, default=data.get(CONF_TURPE, DEFAULT_TURPE)): vol.In(turpe_options),
                vol.Required(CONF_PROFIL, default=data.get(CONF_PROFIL, DEFAULT_PROFIL)): vol.In(PROFILS),
                vol.Required(CONF_DISPLAY, default=data.get(CONF_DISPLAY, DEFAULT_DISPLAY)): vol.In(DISPLAYS),
                vol.Required(
                    CONF_GRANULARITY,
                    default=data.get(CONF_GRANULARITY, DEFAULT_GRANULARITY),
                ): vol.In(GRANULARITIES),
                vol.Required(CONF_TAX_MODE, default=data.get(CONF_TAX_MODE, DEFAULT_TAX_MODE)): vol.In(TAX_MODES),
                vol.Optional(CONF_API_KEY, default=data.get(CONF_API_KEY, "")): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
