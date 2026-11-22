# EV Charge Tracker 0.1.0-beta.3

## Highlights

- Refresh the bundled Lovelace card presentation and editor while preserving profile discovery, explicit profile selection and manual entity mapping.
- Add responsive energy-per-session and cost-per-session charts based on persisted session history. The charts do not require ApexCharts or another external frontend library.
- Keep the energy and cost chart datasets independent, so a known partial cost remains visible even when a session's energy reading is missing.
- Display partial known costs distinctly from complete costs. Missing or invalid values are omitted rather than fabricated as zero.
- Improve tariff configuration: choose a manual price or a Home Assistant price sensor independently for each of up to three periods. The next step shows only the field for the selected source.
- Preserve the inactive source value when switching between manual and sensor pricing. A selected sensor remains the exclusive runtime source; unavailable or invalid sensor data never falls back to the retained manual price.
- Clarify that manually entered prices and price sensors must report the final price actually paid per kWh, including VAT and applicable taxes. The integration does not add taxes.
- Add regression tests for tariff form visibility, retained source selections, sensor exclusivity, and chart empty/partial-data cases.

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
