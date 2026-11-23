# Home Assistant EV Charge Tracker

Universal EV charging session tracker for Home Assistant.

Track charging sessions, delivered energy, battery state of charge (SOC), mileage, costs and history across multiple electric vehicles and chargers. The integration is designed to work with existing Home Assistant entities, independently of vehicle and charger brands.

**Project status:** beta `0.1.0-beta.5` candidate on `feature/beta-5-apple-dashboard`, based on beta.4 merged to `main`. Beta 5 refreshes the Lovelace dashboard with a charging-first visual hierarchy, configurable Compact/Equilibrado/Completo information density, automatic/light/dark appearance, a vehicle illustration with cable-only charging animation, and retained session energy/cost charts and history. It also includes vehicle profile discovery, manual entity mapping and configurable vehicle visuals. This remains a beta, not a production-validated release: live Home Assistant frontend/config-flow validation and real charging-session checks remain important limitations. See the [implementation roadmap](docs/roadmap.md), [beta checklist](docs/beta-checklist.md), [beta.4 release notes](docs/release-notes-beta-4.md) and [beta.5 release notes](docs/release-notes-beta-5.md).

## Design principles

- Brand-agnostic: no hard-coded vehicle, charger, integration or entity IDs.
- User-mapped sensors: select Home Assistant entities by semantic role.
- Explicit units: validate and normalize compatible units; never guess silently.
- Reliable sessions: handle unavailable entities, stale readings, counter resets and Home Assistant restarts.
- Persistent history: completed sessions remain available if source entities are renamed or removed.
- Multi-vehicle and multi-charger support.

## Documentation

- [Functional specification and sensor contract](docs/functional-specification.md)
- [Lovelace dashboard design](docs/dashboard-design.md)
- [Implementation roadmap and status](docs/roadmap.md)
- [Beta validation checklist](docs/beta-checklist.md)
- [Beta.4 candidate release notes](docs/release-notes-beta-4.md)
- [Previous beta.3 release notes](docs/release-notes-beta-3.md)

## Planned capabilities

- Initial prototype: charging session detection using a selected `binary_sensor`.
- Initial prototype: session energy from either a session-scoped counter or a cumulative lifetime meter in Wh or kWh, using a start-of-session baseline.
- SOC start, maximum and final values.
- Battery-care roadmap: parked SOC history, vampire-drain monitoring, optional 12 V monitoring and advisory notifications (specified; implementation pending).
- Optional odometer-based or manual session finalization; automatic immediate finalization waits 60 seconds after the charging signal turns off to collect delayed final energy/SOC updates.
- Duration, electricity cost, history and diagnostics.
- Multiple vehicles, chargers and charging profiles.
- Guided graphical sensor setup with explanations, unit validation and examples.
- A bundled custom Lovelace card with a live SOC/odometer hero, optional explicitly mapped range, per-session charts, configurable vehicle identity and charge-port preview, local PNG/WebP support, and cable-only charging animation. No separate Bubble Card installation is required; frontend behavior still needs real-HA validation.

## Development

The first reference setup is a Leapmotor C10 with a V2C charger. It is a test environment only; the core design must remain generic.

The Lovelace card is included in this integration repository and served by the integration. Its editor discovers configured profiles through an authenticated Home Assistant WebSocket command, automatically selects a sole profile, and offers a selector when multiple profiles exist. The profile-linked card entities (status, energy, cost, SOC start/end/increase, live SOC, odometer, optional range and plugged state, duration and history) are resolved from the integration entity registry; manual mapping remains available.

Contributions, feature requests and bug reports are welcome. The architecture and sensor contract are still being defined, so interfaces may change before the first release.

## License

MIT (planned; license file to be added before the first public release).


## Current prototype scope

The first development increment is intentionally limited to one charging profile per config entry:
- Required charging-state `binary_sensor` (`on` / `off`).
- Required session-energy `sensor` with an explicit Wh or kWh unit.
- Optional SOC, odometer and range sensors. Range is display-only and is never inferred.
- Pricing supports a manual fixed price or a price sensor, plus one-, two- or three-period schedules. Each tariff period can use a manual €/kWh value or its own Home Assistant price sensor. Dynamic price changes are timestamped during a session and retained as historical price segments; energy without a valid price remains explicitly unpriced.
- Immediate or odometer-increase finalization.
- Persistent session state and up to 500 history records.

Power-based session detection, country-specific tariff presets, aggregate day/week/month statistics and complete release packaging remain outside the current beta.4 scope. The bundled card supports profile-aware setup and stable editor controls; responsive energy/cost charts were introduced in beta.3 and are retained in beta.4. Per-period dynamic price sensors and the conditional manual/sensor tariff editor are implemented and covered by automated tests, but still require controlled end-to-end validation in a real Home Assistant instance. Manual finalization is available through a dedicated button entity when selected in the profile. Do not treat this beta as production-validated or rely on it as the sole record of real charging sessions until the real-HA checklist has been completed.


The tariff engine supports one to three periods, weekday selection, overnight boundaries, schedule validation, and estimated allocation of sampled energy deltas. The coordinator now calls this engine when tariff periods are present in the profile configuration and persists the resulting per-period breakdown. The schedule editor is available from the profile options. Its end-to-end behavior still requires controlled Home Assistant testing. See the functional specification for the target behavior.


## Automated validation

A GitHub Actions workflow now installs Home Assistant and pytest, compiles the integration, and runs the unit tests on pushes and pull requests. Recent workflow runs have passed compilation, translation checks, module import smoke tests and tariff unit tests. This does not replace an end-to-end test in a real Home Assistant instance.

## International units and currency

Unit preferences are configured from the profile options under **Units and currency**.
The conversion registry supports energy (Wh, kWh, MWh and joules), power (W, kW,
MW), distance (m, km, mi, ft, yd), voltage (mV, V, kV), current (mA, A, kA),
temperature (°C, °F, K), and vehicle consumption (kWh/100 km, Wh/km, km/kWh,
mi/kWh and kWh/100 mi). Unsupported or ambiguous source units are rejected rather
than inferred from a sensor name or value.

Calculations use canonical units internally (kWh, kW, km, V, A, °C and
kWh/100 km). Energy and cost entities currently honor the selected display energy
unit and currency. Other display preferences are available for the next sensor
roles as those measurements are added.

Currency is selected as a three-letter ISO 4217-style code (for example EUR, USD,
GBP, JPY or CAD). Prices and costs are stored in that selected currency; no
foreign-exchange conversion is performed. A price sensor must declare a matching
currency-per-kWh unit (for example USD/kWh when USD is selected). Existing
historical records retain the currency saved with their session.

### Charging cost quality

Each session stores its currency, tariff breakdown, energy with a known price,
and energy that could not be priced. The cost sensor exposes:

- `cost`: the complete session cost only when all delivered energy is priced.
- `known_cost`: the sum of cost segments that could be calculated, even if the
  session is incomplete.
- `cost_status`: `complete`, `partial`, or `unknown`.
- `priced_energy_kwh` and `unpriced_energy_kwh`: energy coverage of the cost.
- `tariff_breakdown` and `tariff_estimated`: period-level amounts and whether
  allocation is estimated.
- `tariff_allocation_method`: `power` when a usable power profile was integrated,
  or `time_fallback` when elapsed time was used instead.

A partial amount is never presented as the complete session cost. Missing or
invalid price data does not erase known priced segments and is never replaced
with zero. Tariff periods support either manually entered per-kWh prices or selected Home Assistant price sensors. Dynamic price changes are timestamped and retained as historical price segments; this behavior is implemented but still requires end-to-end validation in a real Home Assistant instance.
