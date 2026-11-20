# Home Assistant EV Charge Tracker

Universal EV charging session tracker for Home Assistant.

Track charging sessions, delivered energy, battery state of charge (SOC), mileage, costs and history across multiple electric vehicles and chargers. The integration is designed to work with existing Home Assistant entities, independently of vehicle and charger brands.

**Project status:** development / pre-alpha (`0.1.0-dev`). The integration includes persistent charging sessions, recovery safeguards, configurable energy counters, fixed and dynamic tariff pricing, tariff-period allocation, unit preferences, and the first vehicle/charger registry. It is not yet validated in a live Home Assistant instance; use only a disposable test profile until the controlled test plan is completed.

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
- [Development roadmap and acceptance gates](docs/roadmap.md)

## Current development scope

- Charging session detection using a selected `binary_sensor`, with explicit handling for `unknown` and `unavailable` states.
- Session energy from either a session-scoped counter or a cumulative lifetime meter in Wh or kWh, using a start-of-session baseline.
- SOC start, maximum and final values.
- Optional odometer-based or manual session finalization; automatic immediate finalization waits 60 seconds after the charging signal turns off to collect delayed final energy/SOC updates.
- Duration, electricity cost, history and diagnostics.
- Multiple vehicles, chargers and charging profiles.
- Guided graphical sensor setup with explanations, unit validation and examples.
- An integrated custom Lovelace card, bundled with the integration. No separate Bubble Card installation is required.

## Development

The first reference setup is a Leapmotor C10 with a V2C charger. It is a test environment only; the core design must remain generic.

The first Lovelace card implementation is included in this repository. It is still undergoing frontend validation; its presence does not mean the dashboard milestone is complete.

Contributions, feature requests and bug reports are welcome. The architecture and sensor contract are still being defined, so interfaces may change before the first release.

## License

MIT (planned; license file to be added before the first public release).


## Current prototype scope

The first development increment is intentionally limited to one charging profile per config entry:
- Required charging-state `binary_sensor` (`on` / `off`).
- Required session-energy `sensor` with an explicit Wh or kWh unit.
- Optional SOC and odometer sensors.
- Initial pricing configuration currently supports a manual fixed price or a price sensor. The session coordinator now contains an initial sampled-energy tariff allocation path and stores a per-period breakdown. A graphical options flow now lets users configure one, two or three custom periods, weekdays, local start/end times and €/kWh prices; schedules are validated for weekly gaps and overlaps.
- Immediate or odometer-increase finalization.
- Persistent session state and up to 500 history records.

Power-assisted tariff allocation, timestamped per-period price-sensor changes, session recovery hardening, and read-only vehicle/charger identity indexing are implemented in the development branch. The Lovelace card is at first implementation stage; lifecycle validation, daily/weekly/monthly statistics, complete documentation/quality validation, and graphical multi-profile management remain outstanding. Manual finalization is available through a dedicated button entity when selected in the profile. Do not install this development version in a production instance or use it to record real charging sessions. A testable alpha will be announced only after syntax checks, Home Assistant validation, and a controlled test plan are complete.


The tariff engine supports one to three periods, weekday selection, overnight boundaries, schedule validation, and estimated allocation of sampled energy deltas. The coordinator now calls this engine when tariff periods are present in the profile configuration and persists the resulting per-period breakdown. The schedule editor is available from the profile options. Its end-to-end behavior still requires controlled Home Assistant testing. See the functional specification for the target behavior.


## Automated validation

A GitHub Actions workflow now installs Home Assistant and pytest, compiles the integration, and runs the unit tests on pushes and pull requests. Earlier workflow runs passed compilation, translation checks, module import smoke tests and unit tests. The current integration branch has additional commits that still require a fresh CI run. This does not replace an end-to-end test in a real Home Assistant instance.

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
with zero. Tariff periods currently use the profile's selected currency and
manually entered per-kWh prices. Dynamic per-period price sensors remain planned.


## Controlled pre-alpha test

Do not use the first test to record a real charging session. Install the integration only in a test Home Assistant instance or with a disposable profile and synthetic/test entities. Before testing, create:
- a binary sensor that can be switched ON/OFF manually;
- an energy sensor with a known Wh or kWh value and the correct unit;
- optional SOC and odometer test sensors;
- a fixed test price or a dedicated price sensor.

Verify, in order: setup; start on ON; energy accumulation; no finalization on unknown/unavailable; stop on OFF; configured finalization behavior; restart recovery; and persisted history after restart. Compare calculated energy and cost with the known test values. Do not connect the test profile to the production charger until these checks pass.

A live test on the user's Home Assistant installation still requires installing the branch and confirming its actual entity IDs and sensor units. CI success alone is not sufficient evidence of operational correctness.


## Bundled Lovelace card

The repository now includes the first functional version of the `EV Charge Tracker`
custom card at `custom_components/ev_charge_tracker/frontend/ev-charge-tracker-card.js`.
It is served by the integration at:

```text
/ev_charge_tracker/ev-charge-tracker-card.js
```

After installing/updating the integration and restarting Home Assistant:

1. Open **Settings → Dashboards → Resources**.
2. Add a JavaScript module resource with URL
   `/ev_charge_tracker/ev-charge-tracker-card.js`.
3. Add a **Manual** card to a dashboard and use the example below.
4. Replace each entity ID with the matching entity created by your EV Charge Tracker profile.

The card does not depend on Bubble Card or any other frontend custom card. It displays
the current/latest session, SOC start/end and increase, duration, energy, cost,
cost quality, tariff allocation quality, diagnostic text and persistent session history.
Missing values remain shown as unavailable rather than being displayed as zero.
The current visual editor accepts entity IDs as text for each semantic role; entity-picker controls and full editor usability checks remain outstanding.

### Lovelace YAML example

```yaml
type: custom:ev-charge-tracker-card
name: Mi vehículo
max_history: 8
entities:
  status: sensor.mi_vehiculo_estado_de_carga
  energy: sensor.mi_vehiculo_energia_de_la_carga
  cost: sensor.mi_vehiculo_coste_de_la_carga
  soc_start: sensor.mi_vehiculo_bateria_al_inicio
  soc_end: sensor.mi_vehiculo_bateria_al_final
  soc_increase: sensor.mi_vehiculo_aumento_de_bateria
  duration: sensor.mi_vehiculo_duracion_de_la_carga
  history: sensor.mi_vehiculo_historico_de_cargas
```

Entity IDs above are examples only. Use the IDs shown in **Settings → Devices & services
→ EV Charge Tracker → your vehicle device**. The history sensor exposes the persistent
`sessions` array plus `current_session`, `latest_session` and `diagnostic` attributes.

The card is a first implementation and still requires browser rendering checks across
Home Assistant themes and screen sizes before it can be considered validated for the
real charging test.
