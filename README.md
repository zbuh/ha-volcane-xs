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

## Connecting the unit to Home Assistant

The Volcane XS only exposes Modbus over an RS-485 connector on the board —
there's no Ethernet/WiFi on the unit itself. The recommended way to bridge
it to Home Assistant is a small RS-485-to-WiFi gateway such as the
**Elfin EW11**, wired directly to the Modbus connector already provided on
the board.

Configure the EW11 (or equivalent gateway) as follows, in its own web UI:

**Serial Port Settings**

| Setting | Value |
|---|---|
| Baud Rate | `4800` |
| Data Bit | `8` |
| Stop Bit | `1` |
| Parity | `None` |
| Flow Control | `Half Duplex` |
| Protocol | `Modbus` |

> The baud rate is set by a physical DIP switch on the unit's board
> (SW4-4): off = `4800` (default), on = `9600`. If the gateway can't get a
> response, check that switch before troubleshooting further — cut power
> to the unit before flipping it.

**Communication Settings** (the `netp` socket)

| Setting | Value |
|---|---|
| Protocol | `Tcp Server` |
| Local Port | `502` |
| Route | `Uart` |
| Security | `Disable` |

Once the gateway is on your network, use its IP address and the port above
(`502`) as the Host/Port when setting up the integration below. If you see
intermittent timeouts, increase the gateway's serial **Gap Time** (or the
equivalent `message_wait_milliseconds`/`message_spacing` setting) — some
gateways need extra spacing between requests to talk to this unit
reliably.

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
| `switch` | Auto-restart after power loss | |
| `select` | Exhaust fan speed | Off / Speed 1 / 2 / 3, live readback |
| `select` | Supply fan speed | Off / Speed 1 / 2 / 3, **write-only** (see below) |
| `select` | Filter alarm interval | 45 / 60 / 90 / 180 days, live readback |
| `number` | Bypass minimum temperature | 5-30 °C |
| `number` | Bypass range above minimum | 2-15 °C |
| `number` | Defrost check interval | 15-99 min |
| `number` | Defrost entry temperature | -9-5 °C |
| `number` | Defrost duration | 2-20 min |
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
