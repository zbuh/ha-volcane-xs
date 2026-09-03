# ha-volcane-xs

Home Assistant custom integration for the Cairox / France Air **Volcane XS 250**
heat-recovery ventilation unit, over Modbus TCP, built on the
[`modbus-connection`](https://home-assistant-libs.github.io/modbus-connection/)
library introduced in Home Assistant 2026.9. Target: publish to HACS as a
custom repository once stable (v0.1).

## Repo vs. live test instance

This repo is a git clone at `~/stuff/ha-volcane-xs`. It is **not** the same
checkout as the live test deployment, which lives on the Home Assistant
instance's config share at `/Volumes/config/custom_components/volcane_xs`
(that share is not a git repo — see its own `CLAUDE.md`). Changes get edited
in one place and copied to the other by hand (or `rsync`) — there is no
symlink or CI sync between them yet. Before publishing, always confirm both
copies match.

To push local repo changes to the live instance for testing:

```bash
rsync -av --exclude='__pycache__' \
  ~/stuff/ha-volcane-xs/custom_components/volcane_xs/ \
  /Volumes/config/custom_components/volcane_xs/
```

The live instance also runs `packages/vmc.yaml`, the original YAML Modbus
config for the same physical unit, in parallel — see
[Known quirks](#known-quirks--gotchas) about the double-writer risk this
creates. The plan is to retire that YAML package once this integration
reaches parity and is proven stable, but it has not been touched yet.

## The device

Cairox / France Air Volcane XS 250, this variant with **no CO2 sensor, no
humidity sensor, no electric heater** installed (those registers exist on
other hardware variants and are intentionally not implemented here).

Confirmed by testing with `mbpoll` against the real unit:

- Reads: function code **03** (holding register) only. Function code 04
  (input register) never answers — everything lives in the holding space.
- Writes: function code **06** (write single holding register).
- Addressing is 0-based.
- Serial parameters (behind the TCP gateway): 9600 baud, 8 data bits, parity
  None or Even (no observed difference), 1 stop bit.
- The gateway needed `message_wait_milliseconds: 250` under the classic
  Modbus YAML hub config to be reliable — carry this over as
  `message_spacing` on the connection/unit if the integration sees timeouts.

### Register map

Probe correspondence, confirmed against the LCD panel and board diagram:
register 12 = RA (return air), 13 = OA (outdoor air), 14 = EA (exhaust air),
15 = SA (supply air, also reused for defrost detection).

| Register | Access | Meaning | Notes |
|---|---|---|---|
| 2 | R/W | Bypass min temperature (X) | 5–30 °C. Bypass opens when outdoor temp is between X and X+Y |
| 3 | R/W | Bypass Y range | 2–15 °C. Real max = X + Y. Writing Y=0 or Y=1 is invalid (below device min of 2) |
| 9 | R/W | Power on/off | 0/1. The unit's real power switch |
| 10 | **write-only** | Supply fan speed | Never answers a read (confirmed) — codes below |
| 11 | R/W | Exhaust fan speed | Answers reads, unlike register 10 — codes below |
| 12 | R | Return air temperature | raw = temp + 40 (offset −40 to correct) |
| 13 | R | Outdoor air temperature | same offset |
| 14 | R | Exhaust air temperature | same offset |
| 15 | R | Supply air temperature | same offset |
| 16 | R | Boost active | Reflects an *external* dry-contact relay (e.g. a Shelly), **not** controllable via Modbus. Physically separate circuit from the unit's own fan speed control |
| 18 | R | Alarm bits (raw) | bit0 fire, bit1 bypass active, bit3 defrost |
| 20 | R | Error symbol bits (raw) | see table below |
| 23 | R (config) | Speed mode | Must be `1` for 3-speed mode — confirmed on this unit. Not exposed as an entity |
| 24 | **write-only** | Command register | `1` clears the dirty-filter alarm, `2` clears the weekly timers. **Not** a configuration parameter (an earlier reading of the manual wrongly assumed 24/25 configured an alarm interval in days — that was wrong) |
| 769 | R | Operating hours | uint16, scale 0.1, unit h |

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
| 4 | Filter alarm — **never confirmed against a real active alarm**. The translated manual's bit table skips from bit 3 to bit 5; this position was assumed from another model's documentation. If it's ever seen not to match reality, adjust or remove |
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
off at ~3 W) — an earlier reading that assumed code 0 left a "minimum idle
speed" running was an artifact of the other motor being non-zero during
that test, not real behavior.

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
- **Write-only registers** (this device: 10 and 24) have no equivalent to
  "exclude from reads but keep writable" inside one `Component` —
  `restrict_fields()` excludes a field from *both* reads and writes. The
  approach used here: put write-only registers in their **own `Component`
  subclass that is never passed to a coordinator's `async_update()` loop**
  — only `write()` is ever called on it, on demand, from an entity. This is
  a documented-by-inference pattern, not an explicit example in the
  library's docs; if writes on an unread component ever misbehave, that
  assumption is the first thing to revisit.
- `enum(address, EnumClass, writable=...)` decodes to an `IntEnum` member
  (unknown codes → `None`, warned once). `flags(address, FlagClass)`
  decodes to an `IntFlag` (unknown bits kept). Both are built on
  `NumberField`, so they accept the same `writable`/`signed`/`nan` options
  as `integer`.
- The custom integration owns its `ModbusConnection` indirectly: it asks
  the core `modbus` integration (a manifest `dependencies` entry) for a
  shared unit via `async_get_unit(hass, entry, params, unit_id)` in
  `async_setup_entry`, and `async_get_temporary_unit(...)` (async context
  manager) during config flow validation. This is how multiple integrations
  talking to the same physical link end up sharing one TCP connection
  instead of opening competing sockets — relevant here since the same unit
  is also addressed by `packages/vmc.yaml`'s YAML `modbus:` hub.
- Do **not** reload the config entry when the connection drops —
  reconnection is automatic on the next poll. `ModbusConnectionError` /
  `ModbusTimeoutError` / `ModbusExceptionError` all subclass `ModbusError`;
  catch `ModbusError` in the coordinator and raise `UpdateFailed`.

## Integration architecture

- `device.py` — the register map (`BypassSettings`, `DeviceStatus`,
  `SupplyFanSpeed`, `Commands` components) and the `VolcaneDevice` wrapper
  that groups them. `VolcaneDevice.async_update()` only updates the two
  readable components (`bypass`, `status`); `supply_fan` and `commands` are
  intentionally never polled (see write-only note above).
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

- **Double-writer risk while both integrations run.** `packages/vmc.yaml`
  (YAML `modbus:` hub) and this custom integration both currently target
  the same device and the same registers (2, 3, 9, 10, 11, 24). Until the
  YAML package is retired, avoid driving the same control from both sides
  at the same time (e.g. the old `input_number` bypass sliders and the new
  `number` entities).
- **Select entity `state` translations were not applying** to the option
  display text in initial testing (entity *names* translated fine, but
  `select.<key>.state.<option>` did not — e.g. "Speed 1" stayed in English
  under a Portuguese HA profile). Suspected frontend translation cache,
  since the translation files were brand new that session. Not yet
  confirmed fixed — check this again before release, ideally with a hard
  browser refresh or a private window.
- **Renaming `key=`/`translation_key` values on an `EntityDescription`
  changes the entity's `unique_id`.** Old entities become orphaned in the
  registry (visible as unavailable) and need manual removal via *Settings →
  Devices & Services → Entities*. This happened during the PT→EN
  identifier rename; expect it again for any future key rename.
- Brand images live at `custom_components/volcane_xs/brand/icon.png` +
  `icon@2x.png` (256×256 / 512×512, square, transparent background) — this
  is the HA 2026.3+ mechanism for custom integrations to ship their own
  icon without a PR to `home-assistant/brands`. No `logo.png` needed since
  it would just be the same square image.
- `manifest.json` declares `"dependencies": ["modbus"]` — this pulls in the
  core `modbus` integration for its `async_get_unit`/`async_get_temporary_unit`
  shared-connection helpers, independent of whether the user has any YAML
  `modbus:` config of their own.

## Testing workflow

When testing against the live unit, escalate by risk:

1. Read-only entities first (`sensor`, `binary_sensor`) — zero risk.
2. `switch` (power) — real effect, but simple and reversible.
3. `select` (fan speeds) and `button` (commands) last, one at a time,
   without touching the old YAML-driven controls at the same time.

## Status

Not yet pushed to `github.com/zbuh/ha-volcane-xs` (currently one local
commit). Waiting on a stable v0.1 — outstanding before then:

- [ ] Confirm the `select` state-translation issue above.
- [ ] Verify `write()` behaves correctly on the never-updated
      `SupplyFanSpeed`/`Commands` components under real use (see
      write-only-component caveat above).
- [ ] Decide whether to retire the YAML package once this is proven, and
      document the cutover.
