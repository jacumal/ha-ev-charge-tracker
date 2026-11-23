# EV Charge Tracker 0.1.0-beta.5

## Dashboard redesign

- Promotes live SOC and odometer into the primary vehicle hero, with per-source freshness and unavailable states; stale or implausible readings are not displayed as current.
- Adds independent information density settings: Compacto, Equilibrado and Completo.
- Adds independent appearance settings: Automática (follows Home Assistant), Clara and Oscura.
- Supports an optional explicitly mapped vehicle range sensor; range is never inferred or calculated.
- Adds a vehicle illustration with cable states for disconnected, connected, charging, completed and attention/error.
- During charging, the animated energy flow is confined to the cable. The vehicle body remains visually static.
- Respects the operating system/browser reduced-motion preference.
- Adds editor controls and live preview for vehicle identity, local PNG/WebP paths, fallback silhouette and charge-port position. Transparency is recommended but the alpha channel is not inspected.
- Redesigns the latest-session summary around delivered energy and SOC progression, with clearer duration, cost, tariff allocation and an explicit explanation when cost is partial.
- Refreshes the energy/cost charts and historical session rows with responsive layouts, session-level energy indicators and distinct partial/unknown values.
- Refreshes the selected profile in existing cards while preserving manual entity and card-specific visual overrides.
- The editor emits Lovelace’s standard bubbling/composed `config-changed` event, clearly marks changes as pending, and instructs the user to use the native Save action. Home Assistant does not expose a reliable save-completion callback to the custom editor, so it never reports persistence success prematurely. The final save/reopen check must be performed in a live Home Assistant dashboard.
- CI validates the HACS integration directory, metadata, frontend asset and generated ZIP archive structure, and now runs the official HACS Action plus Home Assistant hassfest. A real HACS install/update in Home Assistant remains a release gate.
- Exposes diagnostic metadata for the configured EVSE energy source to help distinguish missing, unavailable, stale and invalid readings.

## Upgrade

Update the integration files through HACS or the repository installation method, restart Home Assistant, and refresh the browser frontend (hard refresh if the previous card JavaScript remains cached). Existing config entries, profile mappings, tariff settings and stored session history are intended to remain intact; do not delete the integration or its storage as part of the update. Regression coverage and real-instance confirmation are still release gates.

## Known limitations

- Automated CI verifies source syntax, card behavior and HACS package structure, but cannot validate rendering in every Home Assistant theme/browser combination or perform an actual HACS installation.
- A real Home Assistant installation and a complete physical charging session are still required to validate the live entity mapping, cable sensor semantics, tariff allocation and persisted history end to end.
- Vehicle image assets remain user-provided local PNG/WebP files; no external image service is used.
