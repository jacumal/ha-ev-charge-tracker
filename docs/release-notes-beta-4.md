# EV Charge Tracker 0.1.0-beta.4

Beta.4 packages the complete beta.3 implementation now merged to `main), including the consolidated vehicle visualization and telemetry work, as a new versioned candidate. Beta.3 remains available as a historical release.

## Highlights

- Responsive Lovelace card with per-session energy and cost charts based on persisted session history.
- Configurable vehicle identity: make, model, generation/year, trim, color and body style.
- Secondary vehicle thumbnail with transparent local PNG/WebP support and a local SVG silhouette fallback.
- Configurable charging-port anchor coordinates for aligning the cable with custom vehicle images.
- Cable and charging-port states for disconnected, connected, charging, completed, unknown and inconsistent conditions.
- Animated energy flow while charging, respecting the operating system's reduced-motion preference.
- Live battery SOC and odometer display, mapped from the selected profile without creating duplicate telemetry sensors.
- Profile discovery, multi-profile selection and manual entity mapping in the Lovelace card editor.
- One-to-three-period electricity tariffs, with manual final prices or authoritative Home Assistant price sensors per period.
- Preservation of existing profile settings and charging history during in-place upgrades.

## Reliability and data handling

- Unknown or unavailable cable state is not interpreted as physically disconnected.
- A charging state combined with an explicitly disconnected cable is surfaced as an inconsistency.
- Missing or invalid price data is not replaced by a manual fallback or fabricated zero.
- Partial known costs remain distinguishable from complete session costs.
- Vehicle images are served locally; no paid image API or remote image service is required.

## Validation and release gates

- The beta.3 consolidated candidate passed CI (run #217); post-merge main CI passed (run #220).
- Beta.4 PR CI must pass before merging and publishing this tag.
- Live Home Assistant validation remains required for config-flow selectors, card rendering, editor persistence, mobile/desktop and light/dark layouts, profile/history persistence after restart, and a complete real charging session.
- Verify HACS installation from the versioned beta.4 tag after publication.

## Upgrade notes

- Update the integration in place; do not remove and re-add the config entry.
- Do not delete profile data or reset stored session history.
- Back up Home Assistant before installing a beta release.

This is a beta release and is not yet production-validated.
