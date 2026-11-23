# EV Charge Tracker 0.1.0-beta.5

## Dashboard redesign

- Reworks the Lovelace card around the active/latest charging session rather than making SOC and odometer the main visual.
- Adds independent information density settings: Compacto, Equilibrado and Completo.
- Adds independent appearance settings: Automática (follows Home Assistant), Clara and Oscura.
- Adds a vehicle illustration with cable states for disconnected, connected, charging, completed and attention/error.
- During charging, the animated energy flow is confined to the cable. The vehicle body remains visually static.
- Respects the operating system/browser reduced-motion preference.
- Retains local transparent PNG/WebP vehicle images, fallback silhouette and configurable charge-port position.
- Retains session energy/cost charts, partial-cost indication and historical session list in the appropriate display modes.

## Upgrade

Update the integration files through HACS or the repository installation method, restart Home Assistant, and refresh the browser frontend (hard refresh if the previous card JavaScript remains cached). Existing config entries, profile mappings, tariff settings and stored session history are intended to remain intact; do not delete the integration or its storage as part of the update.

## Known limitations

- Automated CI verifies source syntax and card behavior, but cannot validate rendering in every Home Assistant theme/browser combination.
- A real Home Assistant installation and a complete physical charging session are still required to validate the live entity mapping, cable sensor semantics, tariff allocation and persisted history end to end.
- Vehicle image assets remain user-provided local PNG/WebP files; no external image service is used.
