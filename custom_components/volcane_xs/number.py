"""Native number entities for the bypass and defrost settings -- what the
classic Modbus YAML platform cannot express."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator
from .device import VolcaneDevice


@dataclass(frozen=True, kw_only=True)
class VolcaneNumberDescription(NumberEntityDescription):
    component: str
    """Attribute name on VolcaneDevice holding the target Component."""

    attr: str
    """Attribute name on that Component for read and write."""

    value_fn: Callable[[VolcaneDevice], float | None]


DESCRIPTIONS: tuple[VolcaneNumberDescription, ...] = (
    VolcaneNumberDescription(
        key="bypass_min_temp",
        translation_key="bypass_min_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        component="bypass",
        attr="min_temp",
        value_fn=lambda device: device.bypass.min_temp,
    ),
    VolcaneNumberDescription(
        key="bypass_y_range",
        translation_key="bypass_y_range",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=2,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.SLIDER,
        component="bypass",
        attr="y_range",
        value_fn=lambda device: device.bypass.y_range,
    ),
    VolcaneNumberDescription(
        key="defrost_interval",
        translation_key="defrost_interval",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=15,
        native_max_value=99,
        native_step=1,
        mode=NumberMode.SLIDER,
        component="defrost",
        attr="interval",
        value_fn=lambda device: device.defrost.interval,
    ),
    VolcaneNumberDescription(
        key="defrost_entry_temperature",
        translation_key="defrost_entry_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=-9,
        native_max_value=5,
        native_step=1,
        mode=NumberMode.SLIDER,
        component="defrost",
        attr="entry_temperature",
        value_fn=lambda device: device.defrost.entry_temperature,
    ),
    VolcaneNumberDescription(
        key="defrost_duration",
        translation_key="defrost_duration",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        native_min_value=2,
        native_max_value=20,
        native_step=1,
        mode=NumberMode.SLIDER,
        component="defrost",
        attr="duration",
        value_fn=lambda device: device.defrost.duration,
    ),
)


class VolcaneNumber(CoordinatorEntity[VolcaneCoordinator], NumberEntity):
    entity_description: VolcaneNumberDescription
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: VolcaneCoordinator, description: VolcaneNumberDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value_fn(self.coordinator.device)

    async def async_set_native_value(self, value: float) -> None:
        component = getattr(self.coordinator.device, self.entity_description.component)
        await component.write(self.entity_description.attr, int(value))
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        VolcaneNumber(coordinator, description) for description in DESCRIPTIONS
    )
