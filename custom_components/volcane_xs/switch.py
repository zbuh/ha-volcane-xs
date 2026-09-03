"""On/off switch for the unit (register 9).

NOTE: this is not the boost relay -- it is the unit's actual power switch.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator


class VolcaneSwitch(CoordinatorEntity[VolcaneCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "power"

    def __init__(self, coordinator: VolcaneCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_power"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        return self.coordinator.device.status.power

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.status.write("power", True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.status.write("power", False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([VolcaneSwitch(coordinator)])
