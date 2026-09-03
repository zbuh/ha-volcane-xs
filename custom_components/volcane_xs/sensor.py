"""Temperature and operating-hours sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator
from .device import DeviceStatus


@dataclass(frozen=True, kw_only=True)
class VolcaneSensorDescription(SensorEntityDescription):
    value_fn: Callable[[DeviceStatus], float | None]


DESCRIPTIONS: tuple[VolcaneSensorDescription, ...] = (
    VolcaneSensorDescription(
        key="return_air_temperature",
        translation_key="return_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.return_air_temperature,
    ),
    VolcaneSensorDescription(
        key="outdoor_air_temperature",
        translation_key="outdoor_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.outdoor_air_temperature,
    ),
    VolcaneSensorDescription(
        key="exhaust_air_temperature",
        translation_key="exhaust_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.exhaust_air_temperature,
    ),
    VolcaneSensorDescription(
        key="supply_air_temperature",
        translation_key="supply_air_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda status: status.supply_air_temperature,
    ),
    VolcaneSensorDescription(
        key="operating_hours",
        translation_key="operating_hours",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda status: status.operating_hours,
    ),
)


class VolcaneSensor(CoordinatorEntity[VolcaneCoordinator], SensorEntity):
    entity_description: VolcaneSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: VolcaneCoordinator, description: VolcaneSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.device.status)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        VolcaneSensor(coordinator, description) for description in DESCRIPTIONS
    )
