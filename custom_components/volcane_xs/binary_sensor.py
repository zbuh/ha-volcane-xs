"""Binary sensors decoded from the bit registers (18 and 20), plus boost."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator
from .device import BypassAlarm, DeviceStatus, ErrorSymbol


@dataclass(frozen=True, kw_only=True)
class VolcaneBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[DeviceStatus], bool | None]


def _flag_fn(attr: str, flag) -> Callable[[DeviceStatus], bool | None]:
    def value_fn(status: DeviceStatus) -> bool | None:
        value = getattr(status, attr)
        return None if value is None else flag in value

    return value_fn


DESCRIPTIONS: tuple[VolcaneBinarySensorDescription, ...] = (
    VolcaneBinarySensorDescription(
        key="boost_active",
        translation_key="boost_active",
        value_fn=lambda status: status.boost_active,
    ),
    VolcaneBinarySensorDescription(
        key="fire_alarm",
        translation_key="fire_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("alarms", BypassAlarm.FIRE),
    ),
    VolcaneBinarySensorDescription(
        key="bypass_active",
        translation_key="bypass_active",
        value_fn=_flag_fn("alarms", BypassAlarm.BYPASS_ACTIVE),
    ),
    VolcaneBinarySensorDescription(
        key="defrost_active",
        translation_key="defrost_active",
        value_fn=_flag_fn("alarms", BypassAlarm.DEFROST),
    ),
    VolcaneBinarySensorDescription(
        key="outdoor_sensor_error",
        translation_key="outdoor_sensor_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.OUTDOOR_SENSOR),
    ),
    VolcaneBinarySensorDescription(
        key="eeprom_error",
        translation_key="eeprom_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.EEPROM),
    ),
    VolcaneBinarySensorDescription(
        key="return_sensor_error",
        translation_key="return_sensor_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.RETURN_SENSOR),
    ),
    VolcaneBinarySensorDescription(
        key="exhaust_sensor_error",
        translation_key="exhaust_sensor_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.EXHAUST_SENSOR),
    ),
    VolcaneBinarySensorDescription(
        key="filter_alarm",
        translation_key="filter_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.FILTER),
    ),
    VolcaneBinarySensorDescription(
        key="supply_sensor_error",
        translation_key="supply_sensor_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.SUPPLY_SENSOR),
    ),
    VolcaneBinarySensorDescription(
        key="supply_fan_error",
        translation_key="supply_fan_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.SUPPLY_FAN),
    ),
    VolcaneBinarySensorDescription(
        key="exhaust_fan_error",
        translation_key="exhaust_fan_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_flag_fn("error_flags", ErrorSymbol.EXHAUST_FAN),
    ),
)


class VolcaneBinarySensor(CoordinatorEntity[VolcaneCoordinator], BinarySensorEntity):
    entity_description: VolcaneBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VolcaneCoordinator,
        description: VolcaneBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        return self.entity_description.value_fn(self.coordinator.device.status)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        VolcaneBinarySensor(coordinator, description) for description in DESCRIPTIONS
    )
