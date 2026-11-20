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

The configuration must explicitly identify the selected energy mode. The current prototype supports session counters and cumulative lifetime counters by storing the reading at session start as the baseline and accumulating only subsequent positive deltas. A decrease during a session establishes a new baseline and is diagnosed; it is never treated as negative energy. Unavailable readings are ignored. Rollover detection, advanced stale-reading validation, and full restart/recovery tests remain open. The integration must not subtract values from unrelated sessions or silently accept a negative delta.

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


## 11. User-facing session summary and history

The primary vehicle/profile view must present the same essential information consistently:

### Latest charge

- Battery SOC at charge start (%).
- Battery SOC at charge end (%).
- Battery increase in percentage points, calculated as final SOC minus start SOC. Do not label this as energy or relative percent growth.
- Charging duration.
- Charge start date and time.
- Charge end date and time.
- Energy delivered (kWh).
- Charge cost (configured currency; EUR in the first example).

If a value is unavailable or cannot be trusted, show an explicit unknown/pending state rather than a fabricated zero. The latest-charge view must distinguish an in-progress session, a session pending finalization, and a completed session.

### Historical charges

Maintain a persistent, chronological history. Each completed history entry must show at least:
- Date of the charge (and optionally start/end times in its detail view).
- SOC start → SOC end (for example, 35.6 → 90.0 %).
- Energy delivered (for example, 50.96 kWh).
- Cost (for example, 10.23 €).

The history must not be derived from current helper values or source entity states. Each completed session is an immutable stored record so later charges cannot overwrite previous entries. Provide a configurable retention policy, with a sensible default and no silent deletion.

## 12. Lovelace dashboard card

The repository must include a ready-to-use Lovelace dashboard example for the integration. The design direction is **Bubble Card with an Apple-inspired visual language**: dark/light theme compatibility, restrained typography, rounded surfaces, generous spacing, clear hierarchy, subtle separators, and compact status indicators.

The reference layout supplied by the project owner contains:

1. Header identifying the vehicle/profile and a latest-charge summary.
2. Two prominent SOC indicators: battery at start and battery at end.
3. Battery increase summary.
4. Charging duration.
5. Start and end date/time.
6. Cost and energy charged.
7. A chronological charge-history section, with each row/card showing SOC start → end, kWh, and cost.

The card should be responsive and work on mobile as well as desktop. Use Bubble Card where it adds value, but avoid making the underlying integration dependent on frontend custom cards. The README must clearly state any Lovelace custom-card dependencies and installation steps. The repository should include:
- A documented example YAML dashboard card.
- A list of entities exposed by the integration and what each one represents.
- Instructions for adapting the example to a configured vehicle/profile.
- A visual example or screenshot once the first functional card exists.

The card must not assume fixed entity IDs across installations. It should document the entity mapping or use a predictable entity naming scheme generated by the integration.

## 13. Config-flow sensor guidance and examples

The graphical setup must explain every sensor field in plain language. For each field, show:
- What physical measurement or state it represents.
- Whether it is required or optional.
- Expected Home Assistant entity domain.
- Accepted unit(s) and expected value/range.
- A valid example entity and sample value.
- A warning/example of an incompatible selection.

Examples should be generic and clearly marked as examples, not entity IDs the integration expects users to have. Include a visual sensor map or illustrated setup guide in the documentation. Explain the difference between session energy (resets for each charge) and a cumulative energy meter (keeps increasing and requires a baseline/delta).

The config flow should validate the selected entity and unit where possible, show a human-readable error, and allow the user to test a sample reading before saving. Optional sensors can be skipped. Users must be able to review and change mappings later without deleting charge history.


## 14. Electricity price source

The electricity price must be configurable per charging profile using either:

1. **Manual fixed value:** user enters a non-negative price in €/kWh.
2. **Home Assistant sensor:** user selects a numeric `sensor` whose state represents €/kWh.

The configuration UI must clearly explain the expected unit and provide examples. The initial implementation accepts explicit €/kWh-style units (for example `€/kWh` or `EUR/kWh`); it must not infer the unit from the sensor name or numeric value.

At the beginning of each charging session, snapshot the current valid price and store it in that session record. Later changes to the manual setting or source sensor must not alter the cost of an already-started or completed session. If the sensor is unavailable, non-numeric, or has an unsupported unit at session start, preserve the energy data but leave the session cost unknown and expose a diagnostic; do not substitute zero.


## 15. Time-of-use electricity tariffs (one, two or three periods)

The pricing engine must support time-of-use schedules rather than assuming one country's tariff structure.

### User configuration

For each charging profile, the user can select one of these pricing models:

- **Single period:** one price applies all day, every day.
- **Two periods:** two configurable time bands, each with its own price and applicable days.
- **Three periods:** three configurable time bands, each with its own price and applicable days.

The user must also be able to choose:
- A built-in tariff preset when one is available (identified by country/market and tariff name).
- A fully custom schedule, independent of country.
- The Home Assistant local time zone as the default schedule time zone, with the schedule evaluated using that zone (including daylight-saving transitions).

A preset is only a starting configuration. The user must be able to inspect and edit its periods, prices, weekdays, weekends, and any special-day rules supported by the selected preset. Do not assume that all countries use the same number of periods or the same clock boundaries.

### Period definition

Each period contains:
- Display name (for example, Peak / Shoulder / Off-peak).
- Start and end local time.
- Applicable weekdays (Monday–Sunday).
- A manual price per kWh, or an optional selected Home Assistant price sensor for that period.
- Optional effective date range / special-day calendar in a later extension.

Schedules must support periods that cross midnight and schedules whose boundaries differ by weekday or weekend. Validation must detect gaps, overlaps, invalid times, and missing prices. A single-period tariff is the default fallback when the user does not need time bands.

### Cost accounting

The integration must store timestamped energy increments during an active session and apply the price period that was active when each increment was measured. The cost is the sum of the energy attributed to each period multiplied by that period's price. Each session record must retain a breakdown by period as well as the total cost.

If an energy reading interval crosses a tariff boundary, the implementation must:
1. Prefer a power sensor and integrate measured power over time when a suitable power input is configured.
2. Otherwise split the energy delta across the boundary using a documented time-proportional estimate and mark the cost breakdown as estimated.
3. Never silently attribute the entire delta to the period at the end of the interval.

If readings are missing, stale, reset, or unavailable, retain the known energy and cost segments, mark the affected portion as incomplete, and do not fabricate a price or cost.

### Configuration and presentation

The graphical setup must explain the selected tariff preset, period count, each time band, applicable days, price source, and time zone. Users must be able to edit the schedule later without deleting session history.

The latest-charge summary and historical entries must show total cost. A session detail view should additionally show the energy and cost attributed to each tariff period, and whether any amount is estimated.

### Initial implementation boundary

The first testable alpha implements:
- Single-period manual price and single-period price sensor.
- Custom two- or three-period schedules with an independent manual price or optional Home Assistant price sensor for each period.
- Timestamped price history during a session. When a dynamic sensor changes, the new value applies from its observed timestamp onward.
- If a dynamic price sensor is unavailable, invalid, or has an unsupported unit, the affected energy remains unpriced and is explicitly reported; a stale previous value is not silently reused.
- Historical session breakdowns retain the energy and cost attributed to each price segment.

Country-specific preset libraries and special public-holiday calendars remain later extensions. The data model must preserve historical prices so future schedule changes do not rewrite completed sessions.


## 16. Tariff schedule configuration defaults

The setup flow should ask for the number of periods (1, 2 or 3) and generate an editable starter schedule. Starter boundaries are examples only and must never be presented as a country's official tariff unless the user explicitly selects a verified country/tariff preset. The user must be able to change each period's name, start/end times, applicable weekdays and price.

A one-period schedule covers the full day. Two- and three-period starter schedules are convenience templates, not assumptions about Spanish or any other market. The active schedule is interpreted in Home Assistant's configured timezone.
