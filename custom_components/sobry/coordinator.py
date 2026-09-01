"""Data coordinator for Sobry integration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from statistics import mean
from typing import Any

from aiohttp import ClientError

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    API_BASE_URL,
    CONF_DISPLAY,
    CONF_GRANULARITY,
    CONF_PROFIL,
    CONF_SEGMENT,
    CONF_TURPE,
    DEFAULT_DISPLAY,
    DEFAULT_GRANULARITY,
    DEFAULT_PROFIL,
    DEFAULT_SEGMENT,
    DEFAULT_TURPE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class SobryDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Manage Sobry API data updates."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Sobry API."""
        data = {**self.entry.data, **self.entry.options}
        segment = data.get(CONF_SEGMENT, DEFAULT_SEGMENT)
        params = {
            "start": date.today().isoformat(),
            "end": (date.today() + timedelta(days=1)).isoformat(),
            "granularity": data.get(CONF_GRANULARITY, DEFAULT_GRANULARITY),
            "segment": segment,
            "turpe": data.get(CONF_TURPE, DEFAULT_TURPE),
            "profil": data.get(CONF_PROFIL, DEFAULT_PROFIL),
            "display": data.get(CONF_DISPLAY, DEFAULT_DISPLAY),
        }

        if segment == "C4":
            params["profil"] = "pro"
            params["display"] = "HT"

        url = f"{API_BASE_URL}/api/prices/raw"
        session = async_get_clientsession(self.hass)

        try:
            async with session.get(url, params=params, timeout=20) as response:
                if response.status != 200:
                    body = await response.text()
                    raise UpdateFailed(f"Sobry API error {response.status}: {body}")

                payload = await response.json()
        except (ClientError, TimeoutError, ValueError) as err:
            raise UpdateFailed(f"Could not fetch Sobry data: {err}") from err

        prices = payload.get("data", [])
        if not prices:
            raise UpdateFailed("Sobry API returned no pricing data")

        now = dt_util.utcnow()

        def _entry_dt(item: dict[str, Any]) -> datetime | None:
            raw_ts = item.get("timestamp")
            if not raw_ts:
                return None
            try:
                parsed = datetime.fromisoformat(raw_ts)
            except ValueError:
                return None
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=dt_util.UTC)
            return parsed.astimezone(dt_util.UTC)

        sorted_prices = sorted(
            (item for item in prices if _entry_dt(item) is not None),
            key=lambda item: _entry_dt(item) or now,
        )
        if not sorted_prices:
            raise UpdateFailed("Sobry API returned only invalid timestamps")

        current = sorted_prices[0]
        for item in sorted_prices:
            item_ts = _entry_dt(item)
            if item_ts and item_ts <= now:
                current = item
            else:
                break

        next_item = next((item for item in sorted_prices if (_entry_dt(item) or now) > now), None)

        def _price_value(item: dict[str, Any] | None) -> float | None:
            if item is None:
                return None
            if "price_ttc_eur_kwh" in item:
                return float(item["price_ttc_eur_kwh"])
            if "price_ht_eur_kwh" in item:
                return float(item["price_ht_eur_kwh"])
            if "spot_price_eur_kwh" in item:
                return float(item["spot_price_eur_kwh"])
            if "spot_price" in item:
                return float(item["spot_price"]) / 1000.0
            return None

        values = [value for value in (_price_value(item) for item in sorted_prices) if value is not None]
        if not values:
            raise UpdateFailed("Sobry API returned no usable price values")

        return {
            "raw_payload": payload,
            "prices": sorted_prices,
            "current": current,
            "next": next_item,
            "current_price": _price_value(current),
            "next_price": _price_value(next_item),
            "min_price": min(values),
            "max_price": max(values),
            "average_price": mean(values),
            "statistics": payload.get("statistics", {}),
            "count": payload.get("count", len(sorted_prices)),
            "pricing_metadata": payload.get("pricing_metadata", {}),
        }
