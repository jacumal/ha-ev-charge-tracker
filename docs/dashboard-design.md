# Integrated Lovelace card design

**Status:** first functional implementation added at `custom_components/ev_charge_tracker/frontend/ev-charge-tracker-card.js`; browser and live Home Assistant validation still required.

## Packaging decision

The Lovelace card is part of this integration's repository and distribution. It is not a separate project and must not require users to install Bubble Card.

The frontend card is a custom JavaScript module bundled with the integration under `custom_components/ev_charge_tracker/frontend/`. The integration exposes it at `/ev_charge_tracker/ev-charge-tracker-card.js`. The resource must currently be added in Settings → Dashboards → Resources.

The card's visual language should take inspiration from Bubble Card and Apple design, but its implementation and assets are owned by this project. The integration's backend must remain fully functional if the user chooses not to use the card.

## Visual direction

- Calm, minimal visual hierarchy.
- Rounded surfaces and pill-shaped indicators.
- Clear typography and readable numeric values.
- Restrained accent colour for battery/energy status.
- Dark and light theme support, following Home Assistant theme variables where possible.
- Responsive layout, mobile-first but useful on desktop.
- Avoid excessive borders, gradients, decorative icons, and dense tables.
- Accessible contrast, labels and keyboard/focus behavior.

## Main view: vehicle / charging profile

### Header
- Vehicle/profile name.
- Current status: idle, charging, pending finalization, completed, or needs attention.
- Latest charge summary.

### Latest charge
Show these values prominently:
1. Battery at start (%).
2. Battery at end (%).
3. Battery increase in percentage points (end SOC minus start SOC).
4. Charging duration.
5. Start date/time.
6. End date/time.
7. Energy delivered (kWh).
8. Cost.

Use circular progress/ring indicators for start and end SOC. A missing value must display as unavailable/pending, not 0%.

### Charge history
Display newest completed charge first. Every item must show:
- Charge date.
- SOC start → SOC end.
- Energy delivered (kWh).
- Cost.

The history must be backed by persistent session records, not by manually maintained Lovelace helpers or a list of current sensor states. Provide a detailed/expandable view for timestamps and duration. Handle an empty history gracefully.

## Reference supplied by the project owner

The supplied screenshot is the visual/content reference for the initial card. It shows a dark interface with:
- A “CARGAS / Última carga” heading.
- Start and end battery indicators.
- Battery increase.
- Duration and start/end dates.
- Cost and delivered energy.
- Historical charge rows with SOC range, kWh, and cost.

Preserve this information hierarchy while improving responsive behavior and ensuring long dates and values are not clipped.

## Entity contract for the card

The card receives entity IDs through its Lovelace configuration; it does not hard-code installation-specific IDs. Its visual editor accepts semantic entity mappings for status, energy, cost, SOC start/end/increase, live SOC, odometer, optional plugged state, duration and history. The history entity supplies persistent `sessions`, `current_session`, `latest_session` and `diagnostic` attributes.

Prefer a compact set of well-defined integration entities plus a structured history source. The card should support selecting the vehicle/profile it displays and explain configuration errors clearly.

## Installation and updates

- The card JavaScript is distributed with the integration.
- Document how the integration registers/exposes the card as a Lovelace resource.
- If manual resource registration is required for a particular Lovelace mode, provide the exact URL and steps.
- The card should update alongside the integration through HACS/manual integration updates; users should not need a second repository or separate Bubble Card installation.
- Keep the backend independent of the frontend card.


## Implemented card contract

The first card implementation reads these entities:
- `status`: current lifecycle state.
- `energy`: current or latest session energy.
- `cost`: current or latest session cost and cost-quality attributes.
- `soc_start`, `soc_end`, `soc_increase`: battery summary.
- `duration`: elapsed/current session duration.
- `history`: persistent history sensor with session records in attributes.

The card shows the current/latest charge, SOC rings, energy, cost, duration,
timestamps, cost completeness, tariff-estimation state, diagnostics and recent
history. Missing numeric values are not rendered as zero. A missing or
unavailable status entity is explicitly labelled as unconfigured/unavailable;
it must never be presented as an actual idle state. A non-estimated tariff is
labelled "Precio aplicado", not "Medido", because the integration calculates
cost from configured prices and energy rather than measuring a monetary value.
The initial implementation is responsive and uses Home Assistant theme variables.

Remaining acceptance checks before real charging:
- Verify card registration and rendering in a real Home Assistant frontend.
- Check dark/light themes, narrow mobile widths, long profile names and empty history.
- Verify the visual editor's entity pickers populate and persist all configured mappings, including the optional plugged-state entity, in the Lovelace editor.
- Confirm current and completed session presentation against the coordinator's actual lifecycle states, including missing, unknown and unavailable status entities.
- Confirm the history list and cost-quality labels with complete, partial and unknown cost records.
- Verify resource loading after an integration update and restart.


## Beta.3 chart and presentation layer

The beta.3 card adds two compact, responsive charts directly from persisted session
records:

- Energy delivered per completed session (kWh).
- Applied/known cost per session in the profile currency.

The charts use the most recent eight stored sessions and require no external chart
library or ApexCharts dependency. They must remain empty-state friendly and never
invent values. Partial known costs are shown with reduced visual emphasis and are
not represented as complete costs. Chart values are derived from the same stored
session records as the history list; no additional recorder statistics or helpers
are required.

The card editor receives a visual refresh while preserving the profile discovery,
profile selection and all supported semantic entity mappings. Live Home Assistant testing
is still required for frontend rendering, editor persistence and responsive themes.



## Vehicle identity thumbnail and charge activity

The card includes a compact, secondary vehicle visual below the header; battery, energy, cost and history remain the primary information. Vehicle appearance is configured in **Settings → Devices & services → EV Charge Tracker → Configure → Vehicle appearance** and shared across charger profiles for the same vehicle.

The profile stores brand, model, generation, model year, trim, body style and HEX body color. A small local SVG silhouette gallery provides generic SUV/crossover, sedan, hatchback, van and pickup shapes. For a model-accurate image, users may place their own transparent PNG or WebP in /config/www/ev-charge-tracker/ and set its /local/ev-charge-tracker/... path. If the file is absent or fails to load, the card falls back to the colored SVG silhouette. Custom images expose horizontal and vertical port-anchor percentages so the cable can be aligned with different vehicle images. No remote image API or paid image service is required.

An SVG cable/port overlay reflects the actual lifecycle state:
- Charging: cable plugged in and animated energy flow.
- Connected but idle: connector visibly seated at the vehicle port, using the optional cable-connected binary sensor.
- Disconnected: connector shown detached/faded only when the plugged sensor reports OFF.
- Completed: the latest persisted completed session is indicated after the live status returns to idle.
- Error/unknown: attention and unavailable cable telemetry are kept distinct; unknown/unavailable is never interpreted as physically disconnected.

The animation respects the reduced-motion accessibility preference. Without a plugged-state sensor, the card explicitly says that cable connection is not monitored.
