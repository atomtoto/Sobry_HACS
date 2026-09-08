"""Binary sensor telling whether a Sobry plan wants its device running."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import SobryPlanEntity
from .plan import SobryPlan, SobryRuntimeData


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up one binary sensor per configured plan."""
    runtime: SobryRuntimeData = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(SobryPlanBinarySensor(plan) for plan in runtime.plans)


class SobryPlanBinarySensor(SobryPlanEntity, BinarySensorEntity):
    """On while the plan schedules the appliance to run."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_name = None

    def __init__(self, plan: SobryPlan) -> None:
        """Initialise the main entity of the plan device."""
        super().__init__(plan, "active")

    @property
    def available(self) -> bool:
        """Return whether prices are known."""
        return self._plan.available

    @property
    def is_on(self) -> bool | None:
        """Return whether the appliance should be running now."""
        return self._plan.is_active

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the planned slots and the plan settings."""
        return self._plan.as_attributes()
