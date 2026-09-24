"""Speed selectors -- replace the input_select + scripts + 4 sync
automations of the original YAML package.

The supply fan (register 10) is write-only (never answers reads, confirmed
by testing), so there is no CoordinatorEntity or bidirectional sync for it,
only RestoreEntity to remember the last requested value across restarts,
same as the original input_select did.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
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


class VolcaneExhaustSpeed(CoordinatorEntity[VolcaneCoordinator], SelectEntity):
    """Register 11 -- answers reads, real bidirectional sync."""

    _attr_has_entity_name = True
    _attr_translation_key = "exhaust_speed"
    _attr_options = list(OPTIONS.values())

    def __init__(self, coordinator: VolcaneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_exhaust_speed"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        speed = self.coordinator.device.status.exhaust_speed
        return None if speed is None else OPTIONS.get(speed)

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.device.status.write(
            "exhaust_speed", OPTION_TO_SPEED[option]
        )
        await self.coordinator.async_request_refresh()


class VolcaneSupplySpeed(RestoreEntity, SelectEntity):
    """Register 10 -- write-only. No readback: if the speed changes another
    way (physical panel, power loss), this entity has no way to know and
    may go stale -- the same limitation the original input_select had."""

    _attr_has_entity_name = True
    _attr_translation_key = "supply_speed"
    _attr_options = list(OPTIONS.values())
    _attr_should_poll = False

    def __init__(self, coordinator: VolcaneCoordinator) -> None:
        self._coordinator = coordinator
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_supply_speed"
        self._attr_device_info = coordinator.device_info
        self._attr_current_option = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in self._attr_options:
            self._attr_current_option = last_state.state

    async def async_select_option(self, option: str) -> None:
        await self._coordinator.device.supply_fan.write(
            "speed", OPTION_TO_SPEED[option]
        )
        self._attr_current_option = option
        self.async_write_ha_state()


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
            VolcaneExhaustSpeed(coordinator),
            VolcaneSupplySpeed(coordinator),
            VolcaneFilterAlarmInterval(coordinator),
        ]
    )
