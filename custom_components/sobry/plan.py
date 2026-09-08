"""Runtime object turning the Sobry price series into device control."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    CONF_NAME,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import (
    CONF_HOURS,
    CONF_MAX_PRICE,
    CONF_MODE,
    CONF_PLAN_ID,
    CONF_PLANS,
    CONF_REQUIRE_COMPLETE_DATA,
    CONF_TARGET_ENTITY,
    CONF_THRESHOLD_PRICE,
    CONF_WINDOW_END,
    CONF_WINDOW_START,
    DEFAULT_HOURS,
    DEFAULT_REQUIRE_COMPLETE_DATA,
    DEFAULT_THRESHOLD_PRICE,
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    DOMAIN,
    MODE_CHEAPEST_SLOTS,
    MODE_THRESHOLD,
    NAME,
)
from .coordinator import SobryDataUpdateCoordinator
from .planner import PlanResult, build_plan

_LOGGER = logging.getLogger(__name__)


def local_timezone():
    """Return the Home Assistant time zone, across supported HA versions."""
    getter = getattr(dt_util, "get_default_time_zone", None)
    if getter is not None:
        return getter()
    return dt_util.DEFAULT_TIME_ZONE


def parse_time(value: Any, default: str) -> time:
    """Parse a ``HH:MM(:SS)`` option, falling back to ``default``."""
    parsed = dt_util.parse_time(str(value)) if value is not None else None
    if parsed is None:
        parsed = dt_util.parse_time(default)
    return parsed or time(0, 0)


def _as_float(value: Any, default: float | None = None) -> float | None:
    """Return ``value`` as a float, or ``default`` when it is not usable."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class SobryPlan:
    """Decide when a single appliance should run, and drive it."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: SobryDataUpdateCoordinator,
        config: dict[str, Any],
    ) -> None:
        """Initialise the plan from its stored configuration."""
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self.config = config
        self.plan_id: str = config[CONF_PLAN_ID]
        self.name: str = config.get(CONF_NAME) or NAME
        self.mode: str = config.get(CONF_MODE, MODE_CHEAPEST_SLOTS)
        self.target_entity: str | None = config.get(CONF_TARGET_ENTITY) or None
        self.window_start = parse_time(config.get(CONF_WINDOW_START), DEFAULT_WINDOW_START)
        self.window_end = parse_time(config.get(CONF_WINDOW_END), DEFAULT_WINDOW_END)
        self.max_price = _as_float(config.get(CONF_MAX_PRICE))
        self.require_complete_data = bool(
            config.get(CONF_REQUIRE_COMPLETE_DATA, DEFAULT_REQUIRE_COMPLETE_DATA)
        )

        # Configured values are kept apart: they are the reference the
        # tunable entities compare their restored value against.
        self.configured_hours = _as_float(config.get(CONF_HOURS), DEFAULT_HOURS) or 0.0
        self.configured_threshold_price = _as_float(
            config.get(CONF_THRESHOLD_PRICE), DEFAULT_THRESHOLD_PRICE
        )
        self._hours = self.configured_hours
        self._threshold_price = self.configured_threshold_price
        self._control_enabled = True
        self._control_started = False
        self._applied_state: bool | None = None
        self._last_control_error: str | None = None
        self._active: bool | None = None
        self._listeners: list[Callable[[], None]] = []

        self.result: PlanResult | None = None

    # -- Identity ---------------------------------------------------------

    @property
    def unique_id(self) -> str:
        """Return the base unique id of the plan entities."""
        return f"{self.entry.entry_id}_{self.plan_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device grouping every entity of the plan."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.unique_id)},
            name=self.name,
            manufacturer=NAME,
            model="Price plan",
        )

    # -- Tunable settings -------------------------------------------------

    @property
    def hours(self) -> float:
        """Return the daily runtime the plan schedules."""
        return self._hours

    @property
    def threshold_price(self) -> float | None:
        """Return the price under which the appliance may run."""
        return self._threshold_price

    @property
    def control_enabled(self) -> bool:
        """Return whether the plan is allowed to drive its target entity."""
        return self._control_enabled

    @property
    def is_active(self) -> bool | None:
        """Return whether the appliance should be running right now."""
        return self._active

    @property
    def available(self) -> bool:
        """Return whether a price series is known."""
        return self.coordinator.data is not None

    async def async_set_hours(self, hours: float) -> None:
        """Change the scheduled runtime."""
        self._hours = float(hours)
        await self.async_update()

    async def async_set_threshold_price(self, price: float) -> None:
        """Change the price threshold."""
        self._threshold_price = float(price)
        await self.async_update()

    async def async_set_control_enabled(self, enabled: bool) -> None:
        """Enable or disable the automatic control of the target entity."""
        self._control_enabled = bool(enabled)
        if enabled:
            # Re-apply immediately so the appliance matches the plan again.
            self._applied_state = None
        await self.async_update()

    @callback
    def async_restore_settings(
        self,
        *,
        hours: float | None = None,
        threshold_price: float | None = None,
        control_enabled: bool | None = None,
    ) -> None:
        """Apply values restored by the entities, before control starts."""
        if hours is not None:
            self._hours = float(hours)
        if threshold_price is not None:
            self._threshold_price = float(threshold_price)
        if control_enabled is not None:
            self._control_enabled = bool(control_enabled)
        self.async_recalculate()

    # -- Listeners --------------------------------------------------------

    @callback
    def async_add_listener(self, update_callback: Callable[[], None]) -> Callable[[], None]:
        """Register an entity callback, and return the removal callable."""
        self._listeners.append(update_callback)

        @callback
        def _remove() -> None:
            if update_callback in self._listeners:
                self._listeners.remove(update_callback)

        return _remove

    @callback
    def async_notify_listeners(self) -> None:
        """Push the current state to every entity of the plan."""
        for update_callback in list(self._listeners):
            update_callback()

    # -- Planning ---------------------------------------------------------

    @callback
    def async_recalculate(self, now: datetime | None = None) -> None:
        """Recompute the schedule from the latest prices."""
        moment = now or dt_util.utcnow()
        slots = self.coordinator.price_slots
        if not slots:
            self.result = None
            self._active = None
            return

        self.result = build_plan(
            slots,
            moment,
            local_timezone(),
            mode=self.mode,
            hours=self._hours,
            window_start=self.window_start,
            window_end=self.window_end,
            max_price=self.max_price,
            threshold_price=self._threshold_price,
            require_complete_data=self.require_complete_data,
        )
        self._active = self.result.is_active(moment)

    async def async_update(self, now: datetime | None = None) -> None:
        """Recompute the schedule, drive the target and refresh the entities."""
        self.async_recalculate(now)
        await self.async_apply_control()
        self.async_notify_listeners()

    async def async_start_control(self) -> None:
        """Start driving the target entity once the entities are set up."""
        self._control_started = True
        await self.async_update()

    async def async_apply_control(self) -> None:
        """Turn the target entity on or off when the plan says so."""
        if not self._control_started or not self.control_enabled:
            return
        if not self.target_entity or self._active is None:
            return
        if self._active is self._applied_state:
            return

        service = SERVICE_TURN_ON if self._active else SERVICE_TURN_OFF
        try:
            await self.hass.services.async_call(
                "homeassistant",
                service,
                {ATTR_ENTITY_ID: self.target_entity},
                blocking=True,
            )
        except (HomeAssistantError, ValueError) as err:
            message = str(err)
            if message != self._last_control_error:
                _LOGGER.warning(
                    "Sobry plan %s could not call %s on %s: %s",
                    self.name,
                    service,
                    self.target_entity,
                    err,
                )
                self._last_control_error = message
            # Leave the applied state unknown so the call is retried.
            self._applied_state = None
            return

        self._last_control_error = None
        self._applied_state = self._active
        _LOGGER.debug(
            "Sobry plan %s called %s on %s", self.name, service, self.target_entity
        )

    # -- Presentation -----------------------------------------------------

    @property
    def next_start(self) -> datetime | None:
        """Return the start of the next planned run."""
        if self.result is None:
            return None
        window = self.result.next_window(dt_util.utcnow())
        return window.start if window else None

    @property
    def next_end(self) -> datetime | None:
        """Return the end of the running window, else of the next one."""
        if self.result is None:
            return None
        now = dt_util.utcnow()
        current = self.result.current_window(now)
        if current is not None:
            return current.end
        window = self.result.next_window(now)
        return window.end if window else None

    @property
    def average_price(self) -> float | None:
        """Return the average price of the planned slots."""
        return self.result.average_price if self.result else None

    def as_attributes(self) -> dict[str, Any]:
        """Return the plan details exposed on the binary sensor."""
        tz = local_timezone()
        attributes: dict[str, Any] = {
            "mode": self.mode,
            "control_enabled": self._control_enabled,
            "target_entity": self.target_entity,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "requested_hours": round(self._hours, 3),
        }
        if self.mode == MODE_THRESHOLD:
            attributes["threshold_price"] = self._threshold_price
        else:
            attributes["max_price"] = self.max_price

        if self.result is None:
            attributes["reason"] = "no_prices"
            return attributes

        result = self.result
        next_start = self.next_start
        next_end = self.next_end
        attributes.update(
            {
                "period_start": result.period_start.astimezone(tz).isoformat(),
                "period_end": result.period_end.astimezone(tz).isoformat(),
                "data_complete": result.data_complete,
                "planned_hours": round(result.selected_hours, 3),
                "planned_average_price": (
                    round(result.average_price, 6)
                    if result.average_price is not None
                    else None
                ),
                "next_start": next_start.astimezone(tz).isoformat() if next_start else None,
                "next_end": next_end.astimezone(tz).isoformat() if next_end else None,
                "slots": [slot.as_dict(tz) for slot in result.selected],
                "windows": [window.as_dict(tz) for window in result.windows],
            }
        )
        if result.reason:
            attributes["reason"] = result.reason
        return attributes


def plan_configs(entry: ConfigEntry) -> list[dict[str, Any]]:
    """Return the plan configurations stored in the config entry options."""
    plans = entry.options.get(CONF_PLANS) or []
    return [dict(plan) for plan in plans if isinstance(plan, dict) and plan.get(CONF_PLAN_ID)]


@dataclass
class SobryRuntimeData:
    """Everything a config entry keeps alive while it is loaded."""

    coordinator: SobryDataUpdateCoordinator
    plans: list[SobryPlan]

    def plan(self, plan_id: str) -> SobryPlan | None:
        """Return a plan by id."""
        return next((plan for plan in self.plans if plan.plan_id == plan_id), None)

    @callback
    def async_handle_coordinator_update(self) -> None:
        """Replan as soon as new prices are available."""
        for plan in self.plans:
            plan.async_recalculate()
            plan.async_notify_listeners()
        if self.plans:
            self.coordinator.hass.async_create_task(self.async_apply_control())

    async def async_apply_control(self) -> None:
        """Drive every target entity towards its planned state."""
        for plan in self.plans:
            await plan.async_apply_control()

    async def async_tick(self, now: datetime) -> None:
        """Re-evaluate every plan, called once a minute."""
        for plan in self.plans:
            await plan.async_update(now)

    async def async_start_control(self) -> None:
        """Let the plans drive their target entity."""
        for plan in self.plans:
            await plan.async_start_control()
