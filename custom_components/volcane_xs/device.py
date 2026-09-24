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


class FilterAlarmInterval(IntEnum):
    """Register 25 -- confirmed by testing: read/write round-trips for all
    four codes, firmware does not validate the range (a write of 4 was
    accepted verbatim, not rejected or clamped)."""

    DAYS_45 = 0
    DAYS_60 = 1
    DAYS_90 = 2
    DAYS_180 = 3


class BypassAlarm(IntFlag):
    """Bits of register 18 (raw)."""

    FIRE = 1
    BYPASS_ACTIVE = 2
    DEFROST = 8


class ErrorSymbol(IntFlag):
    """Bits of register 20 (raw).

    FILTER (bit 4) is likely wrong: an official manual surfaced later and
    its own bit table also has no bit 4 entry (jumps B3->B5, same gap),
    cross-referencing cleanly against the front-panel E1-E8 error codes
    with no bit to spare for a filter alarm. Kept for now since there's no
    way to force-trigger it for a real test -- see the register 20 note
    in CLAUDE.md.
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


class DefrostSettings(Component):
    """Automatic defrost cycle parameters (holding registers 4-6).

    Confirmed via mbpoll, including a case worth remembering: register 5's
    factory value read back as 39, not the manual's documented default of
    -1 -- until write-testing showed it uses the same +40 offset as the
    RA/OA/EA/SA temperature sensors (39 - 40 = -1). It's the first
    writable field in this codebase to combine `offset` with
    `writable=True`; reads were confirmed both ways (raw 39 <-> -1, raw 35
    <-> -5), but only through this field's own encode/decode, not by
    inspecting modbus_connection's internals -- if a write here ever
    lands on the wrong raw value, that symmetry assumption is the first
    thing to check.
    """

    interval = integer(4, writable=_clamp(15, 99))
    """Minutes between defrost checks, 15-99 min."""

    entry_temperature = integer(5, offset=-40, writable=_clamp(-9, 5))
    """EA temperature that triggers defrost, -9-5 °C."""

    duration = integer(6, writable=_clamp(2, 20))
    """Minutes the defrost cycle runs for once triggered, 2-20 min."""


class DeviceStatus(Component):
    """Sensors, alarms and exhaust fan control -- polled together."""

    auto_restart = boolean(0, writable=True)
    """Register 0. Powers the unit back on automatically after a power
    loss, when true. Confirmed via mbpoll: R/W, factory default 1."""

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

    filter_alarm_interval = enum(25, FilterAlarmInterval, writable=True)
    """Register 25. R/W, unlike register 24 right next to it -- see
    Commands below for how the two relate."""

    operating_hours = gauge(769, 0.1, unit="h")


class SupplyFanSpeed(Component):
    """Register 10 -- write-only, never answers reads (confirmed by
    testing). This component must never be passed to a coordinator/
    async_update(): a periodic poll would always fail on this register.
    """

    speed = integer(10, writable=True)


class Commands(Component):
    """Register 24 -- command register.

    1 -> clears the dirty filter alarm
    2 -> clears the weekly timers

    Not a configuration parameter -- that's register 25 (see
    DeviceStatus.filter_alarm_interval), a separate R/W register right
    next to this one. An earlier reading of the manual conflated the two
    and wrongly dismissed both as unrelated to the alarm interval; only
    24 was actually unrelated.

    Kept out of the polled components (like SupplyFanSpeed) even though a
    direct test showed it does answer reads (returned 0) -- unlike
    register 10, which never does. Polling it would just show whatever
    was last written, which resets on its own once the unit processes the
    command, so there's nothing meaningful to read back.
    """

    value = integer(24, writable=True)


class VolcaneDevice:
    """Groups the unit's sub-systems over the same Modbus unit."""

    def __init__(self, unit) -> None:
        self.bypass = BypassSettings(unit)
        self.defrost = DefrostSettings(unit)
        self.status = DeviceStatus(unit)
        self.supply_fan = SupplyFanSpeed(unit)
        self.commands = Commands(unit)

    async def async_update(self) -> None:
        """Update only the readable sub-systems (bypass, defrost, status)."""
        await self.bypass.async_update()
        await self.defrost.async_update()
        await self.status.async_update()
