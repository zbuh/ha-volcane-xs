"""On/off switches (register 9 power on DeviceStatus, register 0
auto-restart on its own AutoRestartSetting component -- see device.py for
why that one is split out).

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
    """key doubles as the translation key and the unique_id suffix."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: VolcaneCoordinator, key: str, component: str, attr: str
    ) -> None:
        super().__init__(coordinator)
        self._component = component
        self._attr_field = attr
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    @property
    def _target(self):
        return getattr(self.coordinator.device, self._component)

    @property
    def is_on(self) -> bool | None:
        return getattr(self._target, self._attr_field)

    async def async_turn_on(self, **kwargs) -> None:
        await self._target.write(self._attr_field, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self._target.write(self._attr_field, False)
        await self.coordinator.async_request_refresh()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            VolcaneSwitch(coordinator, "power", "status", "power"),
            VolcaneSwitch(coordinator, "auto_restart", "auto_restart", "enabled"),
        ]
    )
