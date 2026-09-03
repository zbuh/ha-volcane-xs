"""Custom integration for the Cairox / France Air Volcane XS 250, built on
modbus-connection."""

from __future__ import annotations

import logging
from datetime import timedelta

from modbus_connection import ModbusError, ModbusTcpParams

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_UNIT_ID, DOMAIN
from .device import VolcaneDevice

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]
SCAN_INTERVAL = timedelta(seconds=30)


class VolcaneCoordinator(DataUpdateCoordinator[None]):
    """Polls bypass + status every 30s. Supply fan speed and commands are
    never read (write-only registers) -- see device.py."""

    def __init__(self, hass: HomeAssistant, entry: "VolcaneConfigEntry", device: VolcaneDevice) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device

    async def _async_update_data(self) -> None:
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name="Volcane XS",
            manufacturer="Cairox / France Air",
            model="Volcane XS 250",
        )


type VolcaneConfigEntry = ConfigEntry[VolcaneCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: VolcaneConfigEntry) -> bool:
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    device = VolcaneDevice(unit)

    coordinator = VolcaneCoordinator(hass, entry, device)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: VolcaneConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
