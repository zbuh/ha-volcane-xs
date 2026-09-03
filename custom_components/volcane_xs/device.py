"""Modbus register map for the Cairox / France Air Volcane XS 250.

Direct translation of the manufacturer's Modbus register map into
modbus_connection.model. Registers were reverse-engineered and confirmed
with mbpoll against a real unit:

- Reads: function code 03 (holding register), 0-based addressing.
- Writes: function code 06 (write single holding register).
- The unit never answers function code 04 (input register) -- everything
  lives in the holding space.

CO2, humidity and electric heater registers are intentionally omitted:
this unit variant does not have that hardware installed.
"""

from enum import IntEnum, IntFlag

from modbus_connection.model import Component, boolean, enum, flags, gauge, integer


class FanSpeed(IntEnum):
    """Valid speed codes in 3-speed mode (register 23 == 1, confirmed)."""

    OFF = 0
    SPEED_1 = 2
    SPEED_2 = 3
    SPEED_3 = 5


class BypassAlarm(IntFlag):
    """Bits of register 18 (raw)."""

    FIRE = 1
    BYPASS_ACTIVE = 2
    DEFROST = 8


class ErrorSymbol(IntFlag):
    """Bits of register 20 (raw).

    Bit 4 (FILTER) is missing from the translated manual's bit table (it
    jumps from bit 3 to bit 5) and has never been confirmed against a real
    active alarm -- assumed from another model's documentation.
    """

    OUTDOOR_SENSOR = 1
    EEPROM = 2
    RETURN_SENSOR = 4
    EXHAUST_SENSOR = 8
    FILTER = 16
    SUPPLY_SENSOR = 32
    SUPPLY_FAN = 64
    EXHAUST_FAN = 128


def _clamp(minimum: int, maximum: int):
    def validator(value: int) -> int:
        if not minimum <= value <= maximum:
            raise ValueError(f"{value} is outside [{minimum}, {maximum}]")
        return value

    return validator


class BypassSettings(Component):
    """Bypass opening parameters (holding registers 2 and 3).

    The bypass opens when the outdoor temperature is between X and X+Y.
    Confirmed limits: X in [5, 30] °C, Y in [2, 15] °C.
    """

    min_temp = integer(2, writable=_clamp(5, 30))
    """Minimum outdoor temperature to open the bypass (X), 5-30 °C."""

    y_range = integer(3, writable=_clamp(2, 15))
    """Range above the minimum (Y), 2-15 °C. Real max = min_temp + y_range."""


class DeviceStatus(Component):
    """Sensors, alarms and exhaust fan control -- polled together."""

    power = boolean(9, writable=True)
    """Register 9. The unit's real on/off switch."""

    exhaust_speed = enum(11, FanSpeed, writable=True)
    """Register 11 -- answers reads, unlike register 10 (supply fan)."""

    return_air_temperature = integer(12, offset=-40, unit="°C")
    outdoor_air_temperature = integer(13, offset=-40, unit="°C")
    exhaust_air_temperature = integer(14, offset=-40, unit="°C")
    supply_air_temperature = integer(15, offset=-40, unit="°C")

    boost_active = boolean(16)
    """Reflects the boost triggered externally through a dry contact relay
    (not the unit's own fan speed control); not controllable from here."""

    alarms = flags(18, BypassAlarm)
    error_flags = flags(20, ErrorSymbol)

    operating_hours = gauge(769, 0.1, unit="h")


class SupplyFanSpeed(Component):
    """Register 10 -- write-only, never answers reads (confirmed by
    testing). This component must never be passed to a coordinator/
    async_update(): a periodic poll would always fail on this register.
    """

    speed = integer(10, writable=True)


class Commands(Component):
    """Register 24 -- command register, write-only, never read.

    1 -> clears the dirty filter alarm
    2 -> clears the weekly timers

    It is not a configuration parameter, despite an earlier misreading of
    the manual that suggested it configured the alarm interval in days.
    """

    value = integer(24, writable=True)


class VolcaneDevice:
    """Groups the unit's sub-systems over the same Modbus unit."""

    def __init__(self, unit) -> None:
        self.bypass = BypassSettings(unit)
        self.status = DeviceStatus(unit)
        self.supply_fan = SupplyFanSpeed(unit)
        self.commands = Commands(unit)

    async def async_update(self) -> None:
        """Update only the readable sub-systems (bypass and status)."""
        await self.bypass.async_update()
        await self.status.async_update()
