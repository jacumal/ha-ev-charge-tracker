# Lovelace dashboard design

**Status:** design brief; the final YAML will be implemented after the integration's entity model is stable.

## Visual direction

Use Bubble Card components with an Apple-inspired interface:
- Calm, minimal visual hierarchy.
- Rounded cards and pill-shaped indicators.
- Clear typography and readable numeric values.
- Restrained accent colour for battery/energy status.
- Dark and light theme support.
- Responsive layout, designed mobile-first but useful on desktop.
- Avoid excessive borders, gradients, decorative icons, and dense tables.

Bubble Card is a frontend custom-card dependency for the example dashboard only. The integration itself must work without Bubble Card or any other custom Lovelace card.

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

Use circular progress/ring indicators for start and end SOC where supported by the chosen frontend components. A missing value must display as unavailable/pending, not 0%.

### Charge history
Display newest completed charge first. Every item must show:
- Charge date.
- SOC start → SOC end.
- Energy delivered (kWh).
- Cost.

The history should be backed by persistent session records exposed by the integration, not by a manually maintained Lovelace helper or a list of current sensor states. Provide a detailed view or expandable section for timestamps and duration.

## Example from the project owner

The supplied screenshot is the visual/content reference for the initial card. It shows a dark interface with:
- A “CARGAS / Última carga” heading.
- Start and end battery indicators.
- Battery increase.
- Duration and start/end dates.
- Cost and delivered energy.
- Historical charge rows with SOC range, kWh and cost.

The first implementation should preserve this information hierarchy while improving responsive behavior and ensuring that long dates and values do not get clipped.

## Entity contract for the card

Before producing the final copy/paste YAML, the integration must settle stable entity IDs and attributes. The card should use entities created for a configured vehicle/profile and document how to replace the example IDs. Prefer a compact set of well-defined entities plus a history entity with structured session attributes or a dedicated history view.

Do not publish a Lovelace example that refers to guessed or not-yet-implemented entity IDs. Keep this design brief until the entity model is implemented and tested.
