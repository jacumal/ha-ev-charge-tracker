# Project roadmap and implementation status

**Repository:** jacumal/ha-ev-charge-tracker  
**Baseline reviewed:** 2026-11-20  
**Baseline commit:** bb44cd1bea7ba38122d125b37568af59e6cea2a8  
**Rule:** A planned or specified capability is not implemented until code and automated tests exist. Real Home Assistant behavior remains pending until controlled testing.

Status: **Implemented** · **Partial** · **Specified / pending** · **Not started / validation pending**

## 1. Architecture and session engine
- [x] Integration skeleton, config flow, coordinator and platform setup.
- [x] Persistent coordinator storage and session/history data model.
- [x] Charging-state transitions; unknown/unavailable are not treated as OFF.
- [x] Initial session recovery/reconciliation after HA restart.
- [ ] Complete recovery matrix for restart during every lifecycle state, duplicate prevention and stale readings.
- [ ] Full lifecycle validation in a real HA instance.
- [ ] Multi-profile architecture and unambiguous simultaneous-session assignment.

**Status: Partial.** Core exists; recovery edge cases and multi-profile behavior remain open.

## 2. Vehicles and chargers
- [x] User-selected charging-state, energy, optional SOC, odometer, power and price entities.
- [x] Vehicle and charger names captured in a profile.
- [x] Optional sensor mapping and profile options flow.
- [ ] First-class independent vehicle and charger registries with reusable mappings.
- [ ] Multiple profiles per installation and explicit vehicle-to-charger assignment.
- [ ] Conflict handling for chargers that could serve more than one vehicle.
- [ ] Validate representative non-Leapmotor vehicles and non-V2C chargers.

**Status: Partial.** Brand-agnostic profile exists; full multi-vehicle/multi-charger model remains open.

## 3. Energy, tariffs and costs
- [x] Session and cumulative energy counter modes; canonical kWh normalization.
- [x] Fixed manual price and selected HA price sensor.
- [x] Price snapshot at session start.
- [x] One-, two- and three-period custom tariff editor.
- [x] Weekly schedule validation, overnight periods and local-time handling.
- [x] Allocation across tariff boundaries, preferring power samples and falling back to time-proportional estimation.
- [x] Tests for tariff boundaries, daylight-saving behavior and stale/future power samples.
- [x] Per-period Home Assistant price sensors with timestamped price changes and historical price-segment breakdown (implementation and automated CI passed on PR #2).
- [ ] More complete counter reset/rollover and stale-energy validation.
- [ ] Controlled end-to-end tests against known meter readings and bills.

**Status: Implementation and automated CI complete (PR #2, run 124 passed).** Controlled validation in a real Home Assistant instance, plus end-to-end comparison against known meter readings and electricity bills, remain open; therefore the full category is not yet closed.

## 4. Sensors, statistics and history
- [x] Current status, session energy, cost, SOC start/end/increase, duration and history sensors.
- [x] Persistent session history and tariff breakdown attributes.
- [x] Display-unit and currency preferences.
- [ ] Daily/weekly/monthly totals, average cost and consumption trends.
- [ ] Explicit data-quality/freshness indicators across source entities.
- [ ] Retention policy and long-history performance validation.
- [ ] Parked SOC history and vampire-drain calculation (new scope).
- [ ] Optional 12 V battery monitoring when a compatible sensor is supplied.

**Status: Partial.** Core session sensors and stored history exist; aggregate statistics and battery-care monitoring remain open.

## 5. Lovelace card
- [x] Design direction documented: responsive, Bubble Card-compatible and Apple-inspired.
- [ ] Functional card bundled in this repository.
- [ ] Latest charge summary, SOC start/end/increase, duration, timestamps, energy and cost.
- [ ] Chronological history and tariff breakdown.
- [ ] Mobile/desktop, light/dark and missing-data behavior.
- [ ] Installation, entity mapping and screenshots.

**Status: Specified / pending.** No integrated card implementation is complete yet.

## 6. Quality, documentation and release
- [x] GitHub Actions: Python compilation, translation structure checks, module import and pytest.
- [x] Unit tests for tariff and power allocation.
- [ ] Expand coverage for coordinator lifecycle, persistence, config flow and sensors.
- [ ] Home Assistant integration validation and controlled real-instance test plan.
- [x] Refresh README project status and link the implementation roadmap; broader README cleanup remains.
- [ ] Complete HACS metadata, release packaging, license and versioning.
- [ ] Alpha installation guide and known limitations.

**Status: Partial.** CI baseline exists and recent run passed; real HA validation and release readiness remain open.

## 7. Battery care, parked monitoring and safety advice (new scope)
Source: user-provided transcript screenshots, approximately 09:36–15:06. These are video-derived recommendations, not verified manufacturer instructions.

### 7.1 Battery-care advice
- [x] Record the video's advice: routine use around 20–80%; prolonged parking around 50–60%; after charging to 100%, use the vehicle soon.
- [ ] Verify chemistry-specific guidance against manufacturer documentation.
- [ ] Make advice configurable by battery chemistry and vehicle guidance; never infer LFP/NMC from vehicle name.
- [ ] Keep advice informational; no automatic charge-control commands.

### 7.2 Vampire-drain monitor
- [ ] Collect timestamped SOC samples while not charging, if a valid SOC entity is configured.
- [ ] Calculate parked SOC change over 24 h and 7 d windows.
- [ ] Report percentage-point change per elapsed day; do not infer kWh without valid usable-capacity data.
- [ ] Reject or flag stale, unavailable, implausible and out-of-order samples; tolerate BMS recalibration and SOC rounding.
- [ ] Expose last sample time, sample count, observation window and data-quality state.
- [ ] Alert only after a configurable observation window and threshold, with cooldown.

### 7.3 12 V battery monitor
- [ ] Optional user-selected 12 V voltage/SOC sensor.
- [ ] Validate units and freshness; configurable advisory thresholds only.
- [ ] State clearly that HA monitoring does not replace vehicle battery management or electrical protection.

### 7.4 Notifications and safety boundaries
- [ ] Optional notifications for prolonged 100% parking, low SOC, unusual parked SOC loss, low 12 V reading and unexpected charge interruption.
- [ ] Separate information, warning and critical alert levels.
- [ ] No remote charging control and no electrical safety certification claims.
- [ ] Verify electrical safety guidance against official vehicle/charger documentation and applicable standards before implementation.

**Status: Specified / pending implementation.** First implementation candidate: vampire-drain monitor, because it is brand-agnostic and can use an optional SOC sensor.

## Working rule
Changes are developed on a feature branch and reviewed before merging to main. A checkbox closes only when implementation and tests exist; real-instance validation is tracked separately.
