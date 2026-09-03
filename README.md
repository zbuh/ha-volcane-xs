# Volcane XS

Home Assistant integration for the Cairox / France Air **Volcane XS 250**
heat-recovery ventilation unit (Modbus TCP), built on the
[`modbus-connection`](https://github.com/home-assistant-libs/modbus-connection)
library introduced in Home Assistant 2026.9.

Fully configurable from the UI (no YAML), with native `number` and `select`
entities for controls the classic Modbus YAML platform cannot express.

## Requirements

- Home Assistant **2026.9.0** or newer.
- Network access to the unit's Modbus TCP interface (default port `502`).

## Installation

### HACS (custom repository)

1. HACS → the `⋮` menu → **Custom repositories**.
2. Add `https://github.com/zbuh/ha-volcane-xs`, category **Integration**.
3. Install **Volcane XS**, then restart Home Assistant.

### Manual

Copy `custom_components/volcane_xs` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

Settings → Devices & Services → **Add Integration** → search for "Volcane XS".

You will be asked for:

| Field | Description |
|---|---|
| Host | IP address of the Modbus TCP gateway |
| Port | Modbus TCP port (default `502`) |
| Modbus unit ID | Slave/unit address (default `1`) |

## Entities

| Platform | Entity | Notes |
|---|---|---|
| `sensor` | Return / outdoor / exhaust / supply air temperature | °C |
| `sensor` | Operating hours | |
| `binary_sensor` | Boost active, fire alarm, bypass active, defrost active | |
| `binary_sensor` | 8 error flags (sensors, EEPROM, filter, fans) | `device_class: problem` |
| `switch` | Power | The unit's real on/off switch |
| `select` | Exhaust fan speed | Off / Speed 1 / 2 / 3, live readback |
| `select` | Supply fan speed | Off / Speed 1 / 2 / 3, **write-only** (see below) |
| `number` | Bypass minimum temperature | 5-30 °C |
| `number` | Bypass range above minimum | 2-15 °C |
| `button` | Clear filter alarm, clear weekly timer | |

## Known limitations

- **Supply fan speed has no readback.** The unit's supply-fan register never
  answers a Modbus read on this hardware revision — confirmed by testing.
  If the speed changes another way (physical panel, power loss), the
  `select` entity has no way to detect it and may show a stale value until
  you change it again. It does restore its last commanded value across a
  Home Assistant restart.
- The dirty-filter and weekly-timer buttons write a command code to a
  write-only register; there is no confirmation that the operation
  succeeded beyond the Modbus write not raising an error.
- Only the temperature, ventilation and bypass sub-systems are covered.
  CO2, humidity and electric-heater registers exist on some hardware
  variants but are not implemented, since the reference unit doesn't have
  that hardware installed.

## License

[MIT](LICENSE)
