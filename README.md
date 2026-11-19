# Home Assistant EV Charge Tracker

Universal EV charging session tracker for Home Assistant.

Track charging sessions, delivered energy, battery state of charge (SOC), mileage, costs and history across multiple electric vehicles and chargers. The integration is designed to work with existing Home Assistant entities, independently of vehicle and charger brands.

**Project status:** early development (`0.1.0-dev`). The first integration skeleton is being implemented; it is not ready for installation or real charging tests yet.

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

## Planned capabilities

- Initial prototype: charging session detection using a selected `binary_sensor`.
- Initial prototype: session energy from a session-scoped sensor in Wh or kWh.
- SOC start, maximum and final values.
- Optional odometer-based or manual session finalization.
- Duration, electricity cost, history and diagnostics.
- Multiple vehicles, chargers and charging profiles.
- Guided graphical sensor setup with explanations, unit validation and examples.
- An integrated custom Lovelace card, bundled with the integration and styled with Bubble Card / Apple-inspired design principles. No separate Bubble Card installation is required.

## Development

The first reference setup is a Leapmotor C10 with a V2C charger. It is a test environment only; the core design must remain generic.

The Lovelace card will be included in this same integration repository and distributed with it. The integration backend will also work without the card.

Contributions, feature requests and bug reports are welcome. The architecture and sensor contract are still being defined, so interfaces may change before the first release.

## License

MIT (planned; license file to be added before the first public release).


## Current prototype scope

The first development increment is intentionally limited to one charging profile per config entry:
- Required charging-state `binary_sensor` (`on` / `off`).
- Required session-energy `sensor` with an explicit Wh or kWh unit.
- Optional SOC and odometer sensors.
- Electricity pricing with one, two or three configurable time-of-use periods, manual prices or Home Assistant price sensors, and per-session cost breakdown.
- Immediate or odometer-increase finalization.
- Persistent session state and up to 500 history records.

Power-based detection, cumulative meter deltas, manual finalization, editable options, advanced freshness validation, and the bundled Lovelace card are not implemented yet. Do not install this development version in a production instance or use it to record real charging sessions. A testable alpha will be announced only after syntax checks, Home Assistant validation, and a controlled test plan are complete.


Time-of-use tariffs are part of the planned design. The initial alpha is expected to start with a fixed single-period price; configurable two/three-period schedules will be added after the core session tracker is validated. See the functional specification for the target behavior.
