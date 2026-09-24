# ha-volcane-xs

Home Assistant custom integration for the Cairox / France Air **Volcane XS 250**
heat-recovery ventilation unit, over Modbus TCP, built on the
[`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/)
library introduced in Home Assistant 2026.9.

## The device

Cairox / France Air Volcane XS 250, this variant with **no CO2 sensor, no
humidity sensor, no electric heater** installed (those registers exist on
other hardware variants and are intentionally not implemented here).

Confirmed by testing with `mbpoll` against a real unit:

- Reads: function code **03** (holding register) only. Function code 04
  (input register) never answers — everything lives in the holding space.
- Writes: function code **06** (write single holding register).
- Addressing is 0-based.
- Serial parameters (behind a TCP gateway): 8 data bits, parity None or
  Even (no observed difference), 1 stop bit. Baud rate is selected by a
  physical DIP switch on the board, **SW4-4**: off = 4800 (default), on =
  9600 (confirmed by the official manual — cut power before flipping it).
  This is why one unit tested at 9600 via `mbpoll` while an Elfin EW11 on
  another unit works at 4800 — it's just a switch position, not a
  unit/firmware difference. Check SW4-4 first if a gateway gets no
  response.
- Three other DIP switches on the same block (SW4-1 to SW4-3, per the
  official manual) are unrelated to Modbus: SW4-1 picks the defrost
  strategy (traditional EA-fan defrost vs. an OA-side electric preheater,
  only relevant below -15°C outdoor), SW4-2 disables the bypass function
  entirely when on, SW4-3 switches the forced-ventilation input between
  CO2-sensor and humidity+CO2-sensor mode (only meaningful with those
  sensors installed).
- Some TCP gateways need a spacing delay between requests (e.g.
  `message_wait_milliseconds: 250` under the classic Modbus YAML hub
  config) to be reliable — carry this over as `message_spacing` on the
  connection/unit if you see timeouts.

### Register map

Probe correspondence, confirmed against the LCD panel and board diagram:
register 12 = RA (return air), 13 = OA (outdoor air), 14 = EA (exhaust air),
15 = SA (supply air, also reused for defrost detection).

An official manual surfaced later (France Air "Manual de Instruções
Volcane XS", version JUL25/V1.0) and its section 10 ("Endereço ModBus
Eco-Smart") matches this device register-for-register against everything
already confirmed by testing. **Careful**: that PDF is a combined manual
covering multiple controller variants — its earlier section 3 (a
touch-screen controller, also nominally covering "XS 250, XS 350, XS
500") describes a *different, incompatible* register map at the same
addresses (e.g. power at register 0, temperatures on a −20 offset). Only
section 10's "Eco-Smart" table — the plain segment-LCD controller this
integration targets — has been cross-checked against real hardware. Don't
pull register info from that other section.

| Register | Access | Meaning | Notes |
|---|---|---|---|
| 0 | R/W | Auto-restart after power loss | 0/1, default 1. Confirmed via `mbpoll`: read/write round-trip |
| 2 | R/W | Bypass min temperature (X) | 5–30 °C. Bypass opens when outdoor temp is between X and X+Y |
| 3 | R/W | Bypass Y range | 2–15 °C. Real max = X + Y. Writing Y=0 or Y=1 is invalid (below device min of 2) |
| 4 | R/W | Defrost check interval | 15–99 min, default 30. Confirmed via `mbpoll` |
| 5 | R/W | Defrost entry temperature | −9–5 °C, default −1. Confirmed via `mbpoll` — and it uses the **same +40 offset** as the temperature sensors below (factory-read raw `39` = actual `−1`; this wasn't obvious at first, the raw value looked like unrelated garbage until write-testing a positive number worked but a negative one round-tripped wrong) |
| 6 | R/W | Defrost duration | 2–20 min, default 10. Confirmed via `mbpoll` |
| 9 | R/W | Power on/off | 0/1. The unit's real power switch |
| 10 | **write-only** | Supply fan speed | Never answers a read (confirmed) — codes below |
| 11 | R/W | Exhaust fan speed | Answers reads, unlike register 10 — codes below |
| 12 | R | Return air temperature | raw = temp + 40 (offset −40 to correct) |
| 13 | R | Outdoor air temperature | same offset |
| 14 | R | Exhaust air temperature | same offset |
| 15 | R | Supply air temperature | same offset |
| 16 | R | Boost active | Reflects an *external* dry-contact relay (e.g. a Shelly), **not** controllable via Modbus. Physically separate circuit from the unit's own fan speed control |
| 18 | R | Alarm bits (raw) | bit0 fire, bit1 bypass on, bit2 bypass off (unused — bit1's absence already means "not active"), bit3 defrost |
| 20 | R | Error symbol bits (raw) | see table below |
| 23 | R (config) | Speed mode | Must be `1` for 3-speed mode — confirmed on this unit. `0`=2-speed, `2`=10-speed (DC) are the same field on other variants. Not exposed as an entity |
| 24 | R/W (unpolled) | Command register | `1` clears the dirty-filter alarm, `2` clears the weekly timers. **Not** a configuration parameter — that's register 25, right next to it. A direct `mbpoll` read returned `0`, so it's not actually unreadable like register 10; it's just excluded from polling because there's nothing meaningful to read back (see `Commands` in `device.py`) |
| 25 | R/W | Filter alarm interval | `0`=45 days, `1`=60 days, `2`=90 days, `3`=180 days. Confirmed via `mbpoll`: write/read-back round-trips for all four codes. Firmware does not validate the range — writing `4` was accepted verbatim, not rejected or clamped, so range validation is left to the integration |
| 769 | R | Operating hours | uint16, scale 0.1, unit h |

Registers that exist per the official manual but are **intentionally not
implemented** (not tested on this unit, since the hardware they configure
isn't installed): 1 (electric heater enable), 7 (CO2 threshold), 8 (this
unit's own Modbus ID, 1–16 — deliberately not exposed as a writable
entity, since writing it would change the address you're talking to
mid-transaction), 17 (CO2 signal on/off), 19 (humidity setpoint), 21
(ERV model-correspondence code, factory/installer setting), 27 (heater
activation temperature), 768 (CO2 ppm), 770 (indoor humidity).

Fan speed codes (registers 10 and 11), confirmed with the unit in 3-speed
mode (register 23 = 1). Only these four codes are valid; others (1,4,6,7,
8-14) are not:

| Code | Meaning |
|---|---|
| 0 | Off |
| 2 | Speed 1 |
| 3 | Speed 2 |
| 5 | Speed 3 |

Error symbol bits (register 20):

| Bit | Meaning |
|---|---|
| 0 | Outdoor air (OA) sensor error |
| 1 | EEPROM error |
| 2 | Return air (RA) sensor error |
| 3 | Exhaust air (EA) sensor error |
| 4 | **Likely doesn't exist.** Previously mapped to "filter alarm" on a guess from another model's documentation, since the translated manual's bit table skipped from bit 3 to bit 5 with no explanation. The official manual's own table (see above) also has no bit 4 entry — it jumps B3→B5 the same way — and its bits cross-reference cleanly 1:1 against the front-panel E1-E8 error codes with no gap needed for a filter alarm. `ErrorSymbol.FILTER` (`device.py`) and the `filter_alarm` binary_sensor built on it are still shipped as of v0.2.0 but are now believed wrong; there's no way to force-trigger this bit for a real test, so this can't be fully confirmed short of it firing on its own one day |
| 5 | Supply air (SA) sensor error |
| 6 | Supply fan error |
| 7 | Exhaust fan error |

### Power measurements (for sanity-checking speed codes)

Confirmed with the two motors isolated (one fixed at code 0 while the other
varies):

- Baseline (both stopped, code 0 on both): ~4 W
- Exhaust motor alone: Speed 1 = 45 W, Speed 2 = 57 W, Speed 3 = 58 W
- Supply motor alone: Speed 1 = 45 W, Speed 2 = 52 W, Speed 3 = 55 W
- Combined (same level on both): 1-1 = 80 W, 2-2 = 101 W, 3-3 = 107 W
- Boost (external relay, register 16): ~105–110 W, physically separate
  circuit, not reachable through registers 10/11

Consumption is roughly additive (baseline + each motor's own contribution).
Code 0 really means stopped (~4 W total, matching the unit fully powered
off at ~3 W) — a reading that assumes code 0 leaves a "minimum idle speed"
running is an artifact of the other motor being non-zero during that test,
not real behavior.

## modbus-connection library notes

Library docs: <https://home-assistant-libs.github.io/modbus-connection/>.
Requires HA 2026.9+ (needs `homeassistant.components.modbus.async_get_unit`
/ `async_get_temporary_unit`, added that release) and Python 3.12+.

Key API points relevant to this integration:

- `modbus_connection.model.Component` — declare register/coil fields as
  class attributes (`integer`, `gauge`, `boolean`, `enum`, `flags`, `coil`,
  `discrete_input`, `bit`, `bits`, `raw_register`, `uint32`/`int32`/
  `uint64`/`int64`, `float32`/`float64`, `string`). Default register space
  is holding; set `register_space = "input"` on the class for input
  registers.
- Migrating a classic Modbus YAML entry is close to 1:1 — `address` matches
  directly, `input_type: holding` is the default space, `data_type: intNN`
  → `integer`/`uint32`/etc, `scale` → `gauge`, `offset` → `offset=`,
  `slave`/`device_address` is the **unit id**, passed to
  `connection.for_unit(...)` / `async_get_unit(...)`, not to a field.
- `Component.async_update()` pools neighbouring addresses into as few
  Modbus calls as possible, then decodes every declared field. Reading an
  attribute returns `T | None` (`None` before the first read, or when the
  raw value is a configured `nan` sentinel or an out-of-range enum/boolean
  code).
- `Component.write(field_name, value)` writes a single field by attribute
  name. Fields must be declared `writable=True` or `writable=<validator>`
  (a callable that raises `ValueError` to reject a value, otherwise returns
  the value to write).
- **Write-only registers** (register 10, the only one confirmed to never
  answer a read) have no equivalent to "exclude from reads but keep
  writable" inside one `Component` — `restrict_fields()` excludes a field
  from *both* reads and writes. The approach used here: put it in its
  **own `Component` subclass that is never passed to a coordinator's
  `async_update()` loop** — only `write()` is ever called on it, on
  demand, from an entity. This is a documented-by-inference pattern, not
  an explicit example in the library's docs; if writes on an unread
  component ever misbehave, that assumption is the first thing to
  revisit. Register 24 (`Commands`) uses the same unpolled pattern even
  though it does answer reads (confirmed by testing, returns `0`) — it's
  excluded because it's a momentary command trigger with nothing
  meaningful to poll, not because the read fails.
- `enum(address, EnumClass, writable=...)` decodes to an `IntEnum` member
  (unknown codes → `None`, warned once). `flags(address, FlagClass)`
  decodes to an `IntFlag` (unknown bits kept). Both are built on
  `NumberField`, so they accept the same `writable`/`signed`/`nan` options
  as `integer`.
- A custom integration built this way owns its `ModbusConnection`
  indirectly: it asks the core `modbus` integration (a manifest
  `dependencies` entry) for a shared unit via
  `async_get_unit(hass, entry, params, unit_id)` in `async_setup_entry`,
  and `async_get_temporary_unit(...)` (async context manager) during config
  flow validation. This is how multiple integrations talking to the same
  physical link end up sharing one TCP connection instead of opening
  competing sockets — relevant if the same device is also addressed by a
  classic YAML `modbus:` hub.
- Do **not** reload the config entry when the connection drops —
  reconnection is automatic on the next poll. `ModbusConnectionError` /
  `ModbusTimeoutError` / `ModbusExceptionError` all subclass `ModbusError`;
  catch `ModbusError` in the coordinator and raise `UpdateFailed`.

## Integration architecture

- `device.py` — the register map (`BypassSettings`, `DefrostSettings`,
  `DeviceStatus`, `SupplyFanSpeed`, `Commands` components) and the
  `VolcaneDevice` wrapper that groups them. `VolcaneDevice.async_update()`
  only updates the three readable components (`bypass`, `defrost`,
  `status`); `supply_fan` and `commands` are intentionally never polled
  (see write-only note above).
- `__init__.py` — `VolcaneCoordinator` (30s poll), shared `device_info`,
  `async_get_unit` wiring.
- `config_flow.py` — host/port/unit id form, validated with
  `async_get_temporary_unit` + a one-off `BypassSettings.async_update()`.
- `sensor.py`, `binary_sensor.py`, `switch.py`, `select.py`, `number.py`,
  `button.py` — one file per platform, each with an `EntityDescription`
  dataclass + `value_fn` lambda pattern, matching the modern
  `has_entity_name` + `translation_key` convention (no hardcoded display
  strings in code — see `strings.json` / `translations/`).
- `select.py`'s two entities are asymmetric: `VolcaneExhaustSpeed` is a
  normal `CoordinatorEntity` (register 11, real readback).
  `VolcaneSupplySpeed` is a bare `RestoreEntity` (register 10, no
  coordinator, no readback) — it remembers the last value **it** wrote
  across restarts, but has no way to detect an out-of-band change (physical
  panel, power loss). A brand new instance of this entity always starts at
  `unknown` until set once, by design — there's nothing to restore yet.

## Known quirks / gotchas

- **Double-writer risk when migrating from a classic YAML `modbus:`
  config.** If a device was previously set up via the YAML Modbus platform
  (hub + `input_number`/`input_select` + scripts driving the same
  registers), don't run both configs against the same registers at the
  same time — retire the YAML config once this integration is confirmed
  working, rather than leaving both active indefinitely.
- **Select entity `state` translations may not apply immediately** to the
  option display text after adding/changing translation files — entity
  *names* pick up new translations fine, but `select.<key>.state.<option>`
  can lag behind (e.g. an English option label surviving under a
  non-English HA profile). Likely a frontend translation cache; a hard
  browser refresh (or private window) is the first thing to try before
  assuming the translation JSON itself is wrong.
- **Renaming `key=`/`translation_key` values on an `EntityDescription`
  changes the entity's `unique_id`.** Old entities become orphaned in the
  registry (visible as unavailable) and need manual removal via *Settings →
  Devices & Services → Entities*.
- Brand images live at `custom_components/volcane_xs/brand/icon.png` +
  `icon@2x.png` (256×256 / 512×512, square, transparent background) — this
  is the HA 2026.3+ mechanism for custom integrations to ship their own
  icon without a PR to `home-assistant/brands`. No `logo.png` needed when
  it would just be the same square image.
- `manifest.json` declares `"dependencies": ["modbus"]` — this pulls in the
  core `modbus` integration for its `async_get_unit`/`async_get_temporary_unit`
  shared-connection helpers, independent of whether the user has any YAML
  `modbus:` config of their own.
