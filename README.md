# ChargeTrack

**EV Management Platform for Home Assistant.**

ChargeTrack brings your electric vehicle's charging sessions, energy, battery state of charge (SOC), mileage, costs, tariffs and history together in one platform. It is designed to work with existing Home Assistant entities, independently of vehicle and charger brands.

**Project status:** beta `0.1.0-beta.8` in development. This corrective beta focuses on the approved vehicle-first Lovelace design, reliable C10 image loading in both the card and editor, and complete light/dark branding. It is not considered release-ready until CI passes and the installed Home Assistant frontend is verified.

## ChargeTrack identity

- Product name: **ChargeTrack**.
- Tagline: **EV Management Platform**.
- Visual identity: minimalist open circular arc and lightning bolt.
- Brand colors: Apple-inspired blue, green, white and neutral grays.
- Dark and light icon variants are included in `custom_components/ev_charge_tracker/brand/`.
- The internal Home Assistant domain remains `ev_charge_tracker` to preserve existing installations, config entries, entity IDs and stored history.

## Design principles

- Brand-agnostic: no hard-coded vehicle, charger, integration or entity IDs.
- User-mapped sensors: select Home Assistant entities by semantic role.
- Explicit units: validate and normalize compatible units; never guess silently.
- Reliable sessions: handle unavailable entities, stale readings, counter resets and Home Assistant restarts.
- Persistent history: completed sessions remain available if source entities are renamed or removed.
- Multi-vehicle and multi-charger support.

## Documentation

- [Brand identity and assets](docs/branding.md)
- [Functional specification and sensor contract](docs/functional-specification.md)
- [Lovelace dashboard design](docs/dashboard-design.md)
- [Implementation roadmap and status](docs/roadmap.md)
- [Beta validation checklist](docs/beta-checklist.md)
- [Beta 6 plan](docs/beta-6-plan.md)

## Vehicle gallery and dashboard

Add the Lovelace resource as a **JavaScript Module**:

```text
/ev_charge_tracker/ev-charge-tracker-card.js?v=0.1.0-beta.8
```

The version query is a cache-busting value; update it when installing a newer beta so the browser requests the new card file.

- Search Wikimedia Commons from the card editor.
- Allowlist recognized CC0, Public Domain, CC BY and CC BY-SA licenses.
- Preserve creator, license, license URL and Commons source-page attribution.
- Store image selection independently per vehicle, shared across that vehicle's charger profiles.
- Keep manual local PNG/WebP image paths available.
- Responsive vehicle-first dashboard with battery, range, odometer, charging state, latest session, cost and history.

## Development

The first reference setup is a Leapmotor C10 with a V2C charger. It is a test environment only; the core design remains generic. The internal integration domain and Lovelace element type intentionally remain stable across the rebrand.

## License

MIT.
