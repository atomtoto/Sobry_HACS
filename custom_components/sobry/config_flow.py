"""Config flow for Sobry integration."""

from __future__ import annotations

from typing import Any
import uuid

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_API_KEY,
    CONF_DISPLAY,
    CONF_GRANULARITY,
    CONF_HOURS,
    CONF_MAX_PRICE,
    CONF_MODE,
    CONF_PLAN_ID,
    CONF_PLANS,
    CONF_PROFIL,
    CONF_REQUIRE_COMPLETE_DATA,
    CONF_SEGMENT,
    CONF_TARGET_ENTITY,
    CONF_TAX_MODE,
    CONF_THRESHOLD_PRICE,
    CONF_TURPE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_DISPLAY,
    DEFAULT_GRANULARITY,
    DEFAULT_HOURS,
    DEFAULT_PROFIL,
    DEFAULT_REQUIRE_COMPLETE_DATA,
    DEFAULT_SEGMENT,
    DEFAULT_TAX_MODE,
    DEFAULT_THRESHOLD_PRICE,
    DEFAULT_TURPE,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
    MAX_HOURS,
    MAX_PRICE_LIMIT,
    MODE_CHEAPEST_SLOTS,
    NAME,
    PLAN_MODES,
)

SEGMENTS = ["C5", "C4"]
TURPE_C5 = ["CU", "CU4", "MU4", "MUDT", "LU"]
TURPE_C4 = ["CU", "LU"]
PROFILS = ["particulier", "pro"]
DISPLAYS = ["TTC", "HT"]
GRANULARITIES = ["quarter_hourly", "hourly"]
TAX_MODES = ["ttc", "ht"]

# Domains a plan can drive with homeassistant.turn_on / turn_off.
CONTROLLABLE_DOMAINS = [
    "switch",
    "input_boolean",
    "light",
    "climate",
    "water_heater",
    "humidifier",
    "fan",
]

PRICE_SELECTOR = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=-MAX_PRICE_LIMIT,
        max=MAX_PRICE_LIMIT,
        step=0.001,
        mode=selector.NumberSelectorMode.BOX,
        unit_of_measurement="€/kWh",
    )
)


def _plan_schema() -> vol.Schema:
    """Return the schema describing a device control plan."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): selector.TextSelector(),
            vol.Required(CONF_MODE, default=MODE_CHEAPEST_SLOTS): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=PLAN_MODES,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="plan_mode",
                )
            ),
            vol.Optional(CONF_TARGET_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=CONTROLLABLE_DOMAINS)
            ),
            vol.Required(CONF_HOURS, default=DEFAULT_HOURS): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=MAX_HOURS,
                    step=0.25,
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement="h",
                )
            ),
            vol.Required(CONF_WINDOW_START, default=DEFAULT_WINDOW_START): selector.TimeSelector(),
            vol.Required(CONF_WINDOW_END, default=DEFAULT_WINDOW_END): selector.TimeSelector(),
            vol.Optional(CONF_MAX_PRICE): PRICE_SELECTOR,
            vol.Required(
                CONF_THRESHOLD_PRICE, default=DEFAULT_THRESHOLD_PRICE
            ): PRICE_SELECTOR,
            vol.Required(
                CONF_REQUIRE_COMPLETE_DATA, default=DEFAULT_REQUIRE_COMPLETE_DATA
            ): selector.BooleanSelector(),
        }
    )


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
    """Sobry options flow: API settings and device control plans."""

    def __init__(self, config_entry):
        # Kept under a private name: assigning ``self.config_entry`` is
        # deprecated in recent Home Assistant releases.
        self._entry = config_entry
        self._plan_id: str | None = None

    # -- Helpers ----------------------------------------------------------

    @property
    def _plans(self) -> list[dict[str, Any]]:
        """Return a copy of the configured plans."""
        return [dict(plan) for plan in self._entry.options.get(CONF_PLANS, [])]

    def _save(self, **changes: Any):
        """Persist the options, keeping the untouched keys."""
        return self.async_create_entry(title="", data={**self._entry.options, **changes})

    @staticmethod
    def _clean_plan(user_input: dict[str, Any], plan_id: str) -> dict[str, Any]:
        """Return a stored plan from the values submitted in the form."""
        plan = {key: value for key, value in user_input.items() if value not in (None, "")}
        plan[CONF_PLAN_ID] = plan_id
        plan[CONF_NAME] = str(user_input.get(CONF_NAME, "")).strip()
        plan[CONF_REQUIRE_COMPLETE_DATA] = bool(
            user_input.get(CONF_REQUIRE_COMPLETE_DATA, DEFAULT_REQUIRE_COMPLETE_DATA)
        )
        return plan

    def _plan_options(self) -> list[dict[str, str]]:
        """Return the plan list as select options."""
        return [
            {"value": plan[CONF_PLAN_ID], "label": plan.get(CONF_NAME) or plan[CONF_PLAN_ID]}
            for plan in self._plans
        ]

    # -- Steps ------------------------------------------------------------

    async def async_step_init(self, user_input=None):
        """Offer the settings and the plan management."""
        menu_options = ["settings", "add_plan"]
        if self._plans:
            menu_options.extend(["edit_plan", "remove_plan"])
        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_settings(self, user_input=None):
        """Edit the pricing settings of the integration."""
        if user_input is not None:
            api_key = (user_input.get(CONF_API_KEY) or "").strip()
            if api_key:
                user_input[CONF_API_KEY] = api_key
            else:
                user_input.pop(CONF_API_KEY, None)
            return self._save(**user_input)

        data = {**self._entry.data, **self._entry.options}
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
        return self.async_show_form(step_id="settings", data_schema=schema)

    async def async_step_add_plan(self, user_input=None):
        """Create a device control plan."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if not str(user_input.get(CONF_NAME, "")).strip():
                errors[CONF_NAME] = "name_required"
            else:
                plans = self._plans
                plans.append(self._clean_plan(user_input, uuid.uuid4().hex))
                return self._save(**{CONF_PLANS: plans})

        return self.async_show_form(
            step_id="add_plan",
            data_schema=self.add_suggested_values_to_schema(
                _plan_schema(), user_input or {}
            ),
            errors=errors,
        )

    async def async_step_edit_plan(self, user_input=None):
        """Pick the plan to edit."""
        if user_input is not None:
            self._plan_id = user_input[CONF_PLAN_ID]
            return await self.async_step_plan_settings()

        schema = vol.Schema(
            {
                vol.Required(CONF_PLAN_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._plan_options(),
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="edit_plan", data_schema=schema)

    async def async_step_plan_settings(self, user_input=None):
        """Edit the selected plan."""
        plans = self._plans
        current = next(
            (plan for plan in plans if plan[CONF_PLAN_ID] == self._plan_id), None
        )
        if current is None:
            return await self.async_step_init()

        errors: dict[str, str] = {}
        if user_input is not None:
            if not str(user_input.get(CONF_NAME, "")).strip():
                errors[CONF_NAME] = "name_required"
            else:
                updated = self._clean_plan(user_input, current[CONF_PLAN_ID])
                plans = [
                    updated if plan[CONF_PLAN_ID] == current[CONF_PLAN_ID] else plan
                    for plan in plans
                ]
                return self._save(**{CONF_PLANS: plans})

        return self.async_show_form(
            step_id="plan_settings",
            data_schema=self.add_suggested_values_to_schema(
                _plan_schema(), user_input or current
            ),
            errors=errors,
            description_placeholders={"name": current.get(CONF_NAME, "")},
        )

    async def async_step_remove_plan(self, user_input=None):
        """Delete one or several plans."""
        if user_input is not None:
            removed = set(user_input.get(CONF_PLANS, []))
            plans = [plan for plan in self._plans if plan[CONF_PLAN_ID] not in removed]
            return self._save(**{CONF_PLANS: plans})

        schema = vol.Schema(
            {
                vol.Required(CONF_PLANS, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=self._plan_options(),
                        mode=selector.SelectSelectorMode.LIST,
                        multiple=True,
                    )
                )
            }
        )
        return self.async_show_form(step_id="remove_plan", data_schema=schema)
