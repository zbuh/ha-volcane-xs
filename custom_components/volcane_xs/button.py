"""Command buttons (register 24, write-only)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import VolcaneConfigEntry, VolcaneCoordinator


class VolcaneCommandButton(ButtonEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VolcaneCoordinator,
        key: str,
        translation_key: str,
        command: int,
    ) -> None:
        self._coordinator = coordinator
        self._command = command
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._attr_device_info = coordinator.device_info

    async def async_press(self) -> None:
        await self._coordinator.device.commands.write("value", self._command)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: VolcaneConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            VolcaneCommandButton(
                coordinator,
                "clear_filter_alarm",
                "clear_filter_alarm",
                1,
            ),
            VolcaneCommandButton(
                coordinator,
                "clear_weekly_timer",
                "clear_weekly_timer",
                2,
            ),
        ]
    )
