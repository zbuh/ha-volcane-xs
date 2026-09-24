"""On/off switches on DeviceStatus (register 9 power, register 0
auto-restart).

NOTE: "power" is not the boost relay -- it is the unit's actual power
switch.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VolcaneConfigEntry, VolcaneCoordinator


class VolcaneSwitch(CoordinatorEntity[VolcaneCoordinator], SwitchEntity):
    """key doubles as the translation key and the DeviceStatus attr name --
    true for both switches in this integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: VolcaneCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        return getattr(self.coordinator.device.status, self._key)

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.device.status.write(self._key, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.device.status.write(self._key, False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            VolcaneSwitch(coordinator, "power"),
            VolcaneSwitch(coordinator, "auto_restart"),
        ]
    )
