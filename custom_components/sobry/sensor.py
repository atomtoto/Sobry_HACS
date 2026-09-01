"""Sensor platform for Sobry integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SobryDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Sobry sensor entities."""
    coordinator: SobryDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            SobryPriceSensor(coordinator, entry, "current_price", "Current price"),
            SobryPriceSensor(coordinator, entry, "next_price", "Next price"),
            SobryPriceSensor(coordinator, entry, "min_price", "Minimum price"),
            SobryPriceSensor(coordinator, entry, "max_price", "Maximum price"),
            SobryPriceSensor(coordinator, entry, "average_price", "Average price"),
        ]
    )


class SobryPriceSensor(CoordinatorEntity[SobryDataUpdateCoordinator], SensorEntity):
    """Representation of a Sobry price sensor."""

    _attr_native_unit_of_measurement = f"{CURRENCY_EURO}/kWh"
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: SobryDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"Sobry {name}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> float | None:
        """Return the sensor state."""
        value = self.coordinator.data.get(self._key)
        if value is None:
            return None
        return round(float(value), 6)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for the primary sensor."""
        if self._key != "current_price":
            return None

        current = self.coordinator.data.get("current", {})
        next_price = self.coordinator.data.get("next_price")
        prices = self.coordinator.data.get("prices", [])

        return {
            "current_timestamp": current.get("timestamp"),
            "current_date": current.get("date"),
            "current_time": current.get("time"),
            "price": current.get("price"),
            "spot_price": current.get("spot_price"),
            "spot_price_eur_kwh": current.get("spot_price_eur_kwh"),
            "price_ht_eur_kwh": current.get("price_ht_eur_kwh"),
            "price_ttc_eur_kwh": current.get("price_ttc_eur_kwh"),
            "next_price": next_price,
            "pricing_metadata": self.coordinator.data.get("pricing_metadata", {}),
            "statistics": self.coordinator.data.get("statistics", {}),
            "count": self.coordinator.data.get("count"),
            "all_prices": prices,
        }
