# EV Charge Tracker 0.1.0-beta.4

## Highlights

- Extend the Lovelace card with a configurable vehicle identity, including make, model, generation/year, trim, color and body style.
- Support a local transparent PNG/WebP vehicle image, with a bundled SVG silhouette fallback.
- Add configurable X/Y positioning for the charging-port anchor so user-provided vehicle images can be aligned.
- Visualize cable and charging-port states: disconnected, connected, charging, completed, unknown and inconsistent.
- Animate energy flow while charging and respect the user's reduced-motion preference.
- Display current battery SOC and odometer using the mapped Home Assistant entities without creating duplicate telemetry sensors.
- Retain the responsive per-session energy and cost charts and the visual editor with profile discovery and manual entity mapping.
- Support up to three configurable tariff periods, with a manual final price or an authoritative Home Assistant price sensor per period.
- Preserve inactive tariff source values and existing profile visual settings when other profiles are configured.

## Reliability and data handling

- Unknown or unavailable cable state is not interpreted as physically disconnected.
- A charging state combined with an explicitly disconnected cable is shown as an inconsistency rather than silently normalized.
- Missing or invalid price data is not replaced with a manual fallback or fabricated zero.
- Partial costs remain distinguishable from complete session costs.
- Vehicle images are restricted to the integration's local image directory; no remote image service is required.
- Existing profiles and stored charging history must be preserved during in-place upgrades.

## Validation and release gates

- Automated repository CI must pass on the final beta.4 commit before publication.
- Live Home Assistant validation remains required for the config flow, Lovelace rendering, editor persistence, mobile/desktop layouts, profile/history persistence after restart and a complete real charging session.
- HACS installation from the versioned tag must be checked after the release is created.

## Upgrade notes

- Update the integration in place; do not remove and re-add the config entry.
- Do not delete profile data or reset stored session history.
- Back up Home Assistant before installing a beta release.

This is a beta release. It is not yet production-validated.
