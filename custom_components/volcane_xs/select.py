"""Fan speed and filter interval selectors -- replace the input_select +
scripts + sync automations of the original YAML package."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator
from .device import FanSpeed, FilterAlarmInterval

OPTIONS: dict[FanSpeed, str] = {
    FanSpeed.OFF: "off",
    FanSpeed.SPEED_1: "speed_1",
    FanSpeed.SPEED_2: "speed_2",
    FanSpeed.SPEED_3: "speed_3",
}
OPTION_TO_SPEED = {option: speed for speed, option in OPTIONS.items()}

FILTER_INTERVAL_OPTIONS: dict[FilterAlarmInterval, str] = {
    FilterAlarmInterval.DAYS_45: "45_days",
    FilterAlarmInterval.DAYS_60: "60_days",
    FilterAlarmInterval.DAYS_90: "90_days",
    FilterAlarmInterval.DAYS_180: "180_days",
}
OPTION_TO_FILTER_INTERVAL = {
    option: interval for interval, option in FILTER_INTERVAL_OPTIONS.items()
}


class VolcaneFanSpeed(CoordinatorEntity[VolcaneCoordinator], SelectEntity):
    """Fan speed select for one of the two motors -- supply (register 10)
    or exhaust (register 11). Both read back, so both stay in sync with
    changes made outside Home Assistant."""

    _attr_has_entity_name = True
    _attr_options = list(OPTIONS.values())

    def __init__(self, coordinator: VolcaneCoordinator, field: str) -> None:
        super().__init__(coordinator)
        self._field = field
        self._attr_translation_key = field
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{field}"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        speed = getattr(self.coordinator.device.status, self._field)
        return None if speed is None else OPTIONS.get(speed)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.device.status.write(
            self._field, OPTION_TO_SPEED[option]
        )
        await self.coordinator.async_request_refresh()


class VolcaneFilterAlarmInterval(CoordinatorEntity[VolcaneCoordinator], SelectEntity):
    """Register 25 -- R/W, real bidirectional sync."""

    _attr_has_entity_name = True
    _attr_translation_key = "filter_alarm_interval"
    _attr_options = list(FILTER_INTERVAL_OPTIONS.values())

    def __init__(self, coordinator: VolcaneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_filter_alarm_interval"
        )
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        interval = self.coordinator.device.status.filter_alarm_interval
        return None if interval is None else FILTER_INTERVAL_OPTIONS.get(interval)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.device.status.write(
            "filter_alarm_interval", OPTION_TO_FILTER_INTERVAL[option]
        )
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            VolcaneFanSpeed(coordinator, "exhaust_speed"),
            VolcaneFanSpeed(coordinator, "supply_speed"),
            VolcaneFilterAlarmInterval(coordinator),
        ]
    )
