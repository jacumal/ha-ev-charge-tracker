# EV Charge Tracker 0.1.0-beta.3

## Highlights

- Add per-vehicle visual identity fields: brand, model, generation, model year, trim, body style and body color. Visual identity is shared by all charger profiles belonging to the same vehicle.
- Add a compact secondary vehicle thumbnail to the Lovelace card, with a transparent built-in silhouette fallback and optional user-supplied transparent PNG/WebP stored locally under `www/ev-charge-tracker/`.
- Add an SVG charging-cable overlay with distinct disconnected, connected-but-idle, charging/energy-flow, completed and attention states. Custom image users can adjust the horizontal and vertical charge-port anchor in the vehicle appearance options. The optional cable-connected binary sensor distinguishes a physically connected vehicle from a disconnected one; without it, the card does not claim to know the plug state.
- Respect reduced-motion preferences and avoid remote image APIs or mandatory paid services.
- Expose live battery SOC and odometer from the profile-selected source entities without creating duplicate tracker sensors.

- Refresh the bundled Lovelace card presentation and editor while preserving profile discovery, explicit profile selection and manual entity mapping.
- Add responsive energy-per-session and cost-per-session charts based on persisted session history. The charts do not require ApexCharts or another external frontend library.
- Keep the energy and cost chart datasets independent, so a known partial cost remains visible even when a session's energy reading is missing.
- Display partial known costs distinctly from complete costs. Missing or invalid values are omitted rather than fabricated as zero.
- Improve tariff configuration: choose a manual price or a Home Assistant price sensor independently for each of up to three periods. The next step shows only the field for the selected source.
- Preserve the inactive source value when switching between manual and sensor pricing. A selected sensor remains the exclusive runtime source; unavailable or invalid sensor data never falls back to the retained manual price.
- Clarify that manually entered prices and price sensors must report the final price actually paid per kWh, including VAT and applicable taxes. The integration does not add taxes.
- Add regression tests for tariff form visibility, retained source selections, sensor exclusivity, and chart empty/partial-data cases.

## Vehicle thumbnail setup

- Open **Settings → Devices & services → EV Charge Tracker → Configure → Vehicle appearance**.
- Enter the vehicle identity and choose its body style and color. These fields are optional and do not alter the vehicle/charger profile IDs or saved sessions.
- For a personal image, copy a transparent PNG or WebP into `/config/www/ev-charge-tracker/` and enter its `/local/ev-charge-tracker/filename.webp` path. The card uses a built-in silhouette when no image is supplied.
- To show connected-but-idle separately from disconnected, select an optional binary sensor that is ON while the cable is physically plugged in. The charging-state sensor remains the authoritative signal for active charging.

## Upgrade notes

- Update the integration in place; do not remove and re-add the config entry.
- Existing vehicle/charger profiles and stored session history are keyed independently of tariff editor state and must be preserved.
- Existing tariff periods with a manual price continue to open with manual pricing selected.
- Existing tariff periods with a price sensor continue to open with sensor pricing selected. If an old period contains both values, the sensor remains authoritative; the manual value is retained only so the user can switch back later.
- After updating, review **Settings → Devices & services → EV Charge Tracker → Configure → Electricity tariffs** to confirm each period's price source and final tax-inclusive price.

## Validation boundary and known limitations

- Repository CI validates Python compilation, translation structure, JavaScript syntax, frontend behavior tests, imports and unit tests.
- Live Home Assistant validation is still required for the config-flow selectors, card rendering, editor persistence, mobile/desktop layout, light/dark themes, and profile/history survival after restart.
- A complete real charging session must still be checked against actual charger energy, SOC, odometer, tariff and electricity-bill values before production reliance.
- Beta.3 does not add daily/weekly/monthly aggregate statistics, battery-care monitoring, vampire-drain monitoring or remote charging control.
