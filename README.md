# ChargeTrack

**EV Management Platform for Home Assistant.**

ChargeTrack brings your electric vehicle's charging sessions, energy, battery state of charge (SOC), mileage, costs, tariffs and history together in one platform. It is designed to work with existing Home Assistant entities, independently of vehicle and charger brands.

**Project status:** beta `0.1.0-beta.9` in development. This beta adds a model catalog, a private local personal-image upload flow, and a consistent transparent-image canvas. Automated and live Home Assistant validation are still required. It is not considered release-ready until CI passes and the installed Home Assistant frontend is verified.

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
/ev_charge_tracker/ev-charge-tracker-card.js?v=0.1.0-beta.9
```

The version query is a cache-busting value; update it when installing a newer beta so the browser requests the new card file.

- Select from the built-in catalog: Leapmotor C10/B10/T03, the leading global BEV models, and representative European models.
- The final selector option is **Añadir una foto personal**.
- Personal images are uploaded directly to the authenticated Home Assistant instance and stored under `/config/www/ev-charge-tracker/custom/`; they are never sent to a third-party image service.
- Personal images must be transparent PNG/WebP and are normalized to a 1200 × 675 transparent canvas.
- The visual standard is front three-quarter view, nose facing right, complete vehicle, consistent scale and transparent background.
- Vehicle image selection remains per vehicle and shared across that vehicle's charger profiles.
- Models without a verified, redistributable bundled render remain selectable but ask the user for a personal image; no unlicensed image is silently packaged.
- Responsive vehicle-first dashboard with battery, range, odometer, charging state, latest session, cost and history.

## Development

The first reference setup is a Leapmotor C10 with a V2C charger. It is a test environment only; the core design remains generic. The internal integration domain and Lovelace element type intentionally remain stable across the rebrand.

## License

MIT.
