# ChargeTrack 0.1.0-beta.6 — candidate

## Scope

Beta 6 is limited to:
- A free vehicle-image gallery using Wikimedia Commons.
- A redesigned, responsive vehicle-first Lovelace card based on the approved idle and charging references.

No new charging, tariff, sensor, cost or statistics functionality is introduced.

## Vehicle gallery

- Search Commons for vehicle images directly from the card editor.
- Filter results by machine-readable license metadata; accept only allowlisted CC0, Public Domain, CC BY and CC BY-SA licenses.
- Store and display creator, license and source-page attribution with the selected image.
- Keep manual local PNG/WebP image paths available.
- Reject non-HTTPS and non-Wikimedia image hosts.

## Card presentation

- Promotes the vehicle image into a large hero area.
- Uses the approved light, premium, rounded visual direction.
- Keeps the existing charging cable states and animation.
- Retains battery, odometer, latest-session metrics, charts and history.
- Responsive layout adjustments for narrow screens.

## Upgrade and validation

Update the integration in place; do not delete the config entry or stored history. Restart Home Assistant and refresh the browser resource. The Lovelace card editor must be saved using the native Save action.

This is a candidate, not a production-validated release. Real Home Assistant checks for image selection/persistence, mobile and desktop layouts, themes, and regression of existing session data remain required.


## ChargeTrack rebrand

- User-facing integration and card name changed to ChargeTrack.
- Added minimalist arc-and-lightning logo in dark and light SVG variants, plus a horizontal wordmark.
- Documented the blue, green, white and neutral-gray identity system.
- Preserved the internal `ev_charge_tracker` domain, Lovelace element type, resource URL and existing configuration/history for safe in-place upgrades.
