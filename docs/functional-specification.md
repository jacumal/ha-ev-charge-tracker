# Functional specification

**Project:** Home Assistant EV Charge Tracker  
**Status:** Draft — architecture and sensor contract  
**Scope:** Multi-vehicle, multi-charger EV charging session tracking.

## 1. Goals

The integration tracks charging sessions for electric vehicles independently of vehicle or charger brand. It consumes existing Home Assistant entities selected by the user; it does not require a specific cloud integration, wallbox integration, vehicle API, or entity naming convention.

The first reference setup is a Leapmotor C10 with a V2C charger, but no vehicle- or charger-specific assumptions should be embedded in the core.

The integration should provide:
- Session start/end detection.
- Energy delivered per session.
- Battery state of charge (SOC) at start, maximum observed during charging, and finalization.
- Optional odometer-based confirmation after the vehicle is driven.
- Session duration and electricity cost.
- Persistent history and recovery after Home Assistant restarts.
- Multiple vehicles and multiple chargers, including an explicit vehicle-to-charger assignment.
- Diagnostics for missing, unavailable, stale, invalid, or inconsistent source data.

## 2. Core concepts

- **Vehicle:** the EV whose battery, SOC and odometer are tracked.
- **Charger:** the charging station supplying energy and/or reporting charging state.
- **Charging profile:** configuration joining one vehicle to one or more compatible chargers and mapping Home Assistant entities to semantic inputs.
- **Session:** one continuous charging event associated with a vehicle and charger.
- **Finalization:** the point at which a session is considered complete and its immutable summary is written to history.

A charger must not be silently associated with two vehicles that could charge simultaneously. The configuration should make assignment explicit and warn about ambiguous assignments.

## 3. Sensor contract

Entity IDs are user-selectable and must never be hard-coded. Each selected entity is validated against its semantic role, state, device class where available, and unit of measurement.

### 3.1 Session detection inputs

At least one detection method must be configured:

| Method | Entity | Expected meaning | Accepted values / units |
|---|---|---|---|
| Charging state | `binary_sensor` | `on` means actively charging; `off` means not charging | `on`, `off`; `unknown`/`unavailable` are indeterminate |
| Charging power | `sensor` | Instantaneous power delivered to the vehicle | W, kW |
| Session energy delta | `sensor` | Energy delivered in the current session; may reset between sessions | Wh, kWh |
| Cumulative energy meter | `sensor` | Monotonic total energy counter from the charger/meter | Wh, kWh |

Power-based and energy-based detection require configurable thresholds and debounce/dwell times to avoid false starts from standby loads or brief telemetry fluctuations. An unavailable state must never be interpreted as `off`.

### 3.2 Energy inputs

At least one energy source is required to calculate session energy:

| Role | Entity | Expected meaning | Accepted units |
|---|---|---|---|
| Preferred | Session energy | Session-scoped delivered energy | Wh, kWh |
| Alternative | Cumulative energy | Meter total; session energy is calculated from start/end deltas | Wh, kWh |

The configuration must explicitly identify the selected energy mode. The implementation must handle counter resets, rollover, unavailable readings, stale readings, and Home Assistant restarts. It must not subtract values from unrelated sessions or silently accept a negative delta.

### 3.3 Vehicle inputs

| Role | Required? | Entity domain | Accepted units / range |
|---|---|---|---|
| Battery SOC | Recommended | `sensor` | %, 0–100 |
| Odometer | Optional | `sensor` | km, mi |
| Battery capacity | Optional | `sensor` or configured value | kWh |
| Remaining range | Optional | `sensor` | km, mi |
| Vehicle availability/connectivity | Optional | `binary_sensor` or `sensor` | Integration-specific; diagnostic only |

SOC is a percentage, not a fraction from 0 to 1. If a source uses a different scale, the user must select an explicit conversion or the integration must reject it with a clear validation message.

Odometer values must be normalized to kilometres internally. Odometer increase may be used as a configurable finalization strategy, but it must not be mandatory for all users.

### 3.4 Optional charger diagnostics

| Role | Entity domain | Accepted units |
|---|---|---|
| Current | `sensor` | A |
| Voltage | `sensor` | V |
| Phase count | `sensor` or configured value | count |
| Charger availability | `binary_sensor` or `sensor` | state |
| Temperature | `sensor` | °C, °F |

These values must not be prerequisites for session tracking.

## 4. Unit normalization

Normalize values internally to:
- Energy: kWh
- Power: kW
- Distance: km
- SOC: %
- Current: A
- Voltage: V
- Temperature: °C

Accept compatible source units and convert them explicitly. Never infer units from entity names or numeric magnitude. If the entity has no unit and no explicit user override is configured, show a configuration/diagnostic warning and do not silently guess.

## 5. Session lifecycle

Proposed lifecycle:

1. **Idle:** no active session.
2. **Starting:** a configured detection signal meets its start criteria.
3. **Charging:** session start time and available baseline readings are stored; energy and SOC maxima are tracked.
4. **Finishing:** configured detection signal meets its stop criteria. Final energy and end time are captured when reliable.
5. **Pending finalization:** optional post-charge data (for example, a fresh SOC reading or odometer increase) is awaited.
6. **Completed:** a single immutable session summary is committed to persistent history.
7. **Needs attention:** required readings are missing or contradictory; retain the session and expose a diagnostic rather than fabricating values.

The finalization strategy must be configurable:
- Immediate when charging ends and required data is valid.
- Wait for a fresh post-charge SOC reading.
- Wait for odometer increase.
- Manual confirmation.

A missing SOC must remain unknown, never be represented as a valid 0%. The maximum valid SOC observed during a session should be retained, including while pending finalization. Stale values must not be treated as fresh readings.

## 6. Persistence and recovery

Session state and history must survive Home Assistant restarts and integration reloads. A restart must not create a duplicate session, lose energy baselines, or finalize a session based solely on an `unknown`/`unavailable` transition.

Persist at least:
- Vehicle and charger identifiers.
- Session ID and lifecycle state.
- Start/end timestamps.
- Start and final SOC, plus maximum SOC observed.
- Energy baseline, last valid reading, and final energy.
- Start/end odometer when available.
- Price snapshot and calculated cost when configured.
- Data quality flags and finalization reason.

Historical sessions should remain available if source entities are later renamed or removed.

## 7. Multiple vehicles and chargers

The integration should support multiple vehicle entries and multiple charger entries. A charging profile explicitly associates a vehicle with a charger and maps the entities used by that combination. A vehicle may be associated with more than one charger. Simultaneous sessions must be supported only when they can be unambiguously assigned to different vehicles.

## 8. Configuration experience

Use Home Assistant config flows:
- Add a vehicle.
- Add a charger.
- Create or edit a charging profile linking them.
- Select entities by semantic role.
- Select detection and energy modes.
- Configure thresholds, debounce times, price source/value, and finalization strategy.
- Validate domains, units, availability and sample states.
- Allow optional fields to remain unset.

Reconfiguration must not delete historical sessions.

## 9. Non-goals for the first milestone

- Direct vehicle cloud/API integrations.
- Direct charger protocol integrations.
- Remote control of charging current or charge limits.
- Energy tariff forecasting.
- Automatic discovery of arbitrary entity semantics.

The integration consumes Home Assistant entities supplied by existing integrations.

## 10. Initial implementation milestones

1. Finalize sensor contract and lifecycle rules.
2. Build integration skeleton and config flow.
3. Implement entity validation and unit conversion.
4. Implement one profile and a persistent session state machine.
5. Add history and recovery tests.
6. Add multiple profiles, vehicles and chargers.
7. Add statistics, diagnostics, translations and HACS metadata.
