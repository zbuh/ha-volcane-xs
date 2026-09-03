"""Native number entities for the bypass -- what the classic Modbus YAML
platform cannot express."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator
from .device import BypassSettings


@dataclass(frozen=True, kw_only=True)
class VolcaneNumberDescription(NumberEntityDescription):
    attr: str
    value_fn: Callable[[BypassSettings], float | None]


DESCRIPTIONS: tuple[VolcaneNumberDescription, ...] = (
    VolcaneNumberDescription(
        key="bypass_min_temp",
        translation_key="bypass_min_temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=5,
        native_max_value=30,
        native_step=1,
        mode=NumberMode.SLIDER,
        attr="min_temp",
        value_fn=lambda bypass: bypass.min_temp,
    ),
    VolcaneNumberDescription(
        key="bypass_y_range",
        translation_key="bypass_y_range",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_min_value=2,
        native_max_value=15,
        native_step=1,
        mode=NumberMode.SLIDER,
        attr="y_range",
        value_fn=lambda bypass: bypass.y_range,
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
        return self.entity_description.value_fn(self.coordinator.device.bypass)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.device.bypass.write(self.entity_description.attr, int(value))
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
