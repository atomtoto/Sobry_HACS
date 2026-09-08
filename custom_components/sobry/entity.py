"""Base entity shared by every Sobry price plan platform."""

from __future__ import annotations

from homeassistant.helpers.entity import Entity

from .plan import SobryPlan


class SobryPlanEntity(Entity):
    """An entity belonging to a Sobry price plan."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, plan: SobryPlan, key: str) -> None:
        """Attach the entity to its plan and device."""
        self._plan = plan
        self._attr_unique_id = f"{plan.unique_id}_{key}"
        self._attr_device_info = plan.device_info

    async def async_added_to_hass(self) -> None:
        """Refresh the entity whenever the plan is re-evaluated."""
        await super().async_added_to_hass()
        self.async_on_remove(self._plan.async_add_listener(self.async_write_ha_state))
