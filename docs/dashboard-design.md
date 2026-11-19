# Integrated Lovelace card design

**Status:** design brief; implementation follows the integration's entity model.

## Packaging decision

The Lovelace card is part of this integration's repository and distribution. It is not a separate project and must not require users to install Bubble Card.

The frontend card will be a custom JavaScript module bundled with the integration (for example, under `custom_components/ev_charge_tracker/frontend/`). The integration will expose the module as a static frontend resource. The setup/documentation should explain any Home Assistant resource registration step that cannot safely be automated for the user's Lovelace storage mode.

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

Before producing the final card implementation, settle stable entity IDs and attributes. The card must bind to entities created for a configured vehicle/profile. Avoid guessed or hard-coded entity IDs across installations.

Prefer a compact set of well-defined integration entities plus a structured history source. The card should support selecting the vehicle/profile it displays and explain configuration errors clearly.

## Installation and updates

- The card JavaScript is distributed with the integration.
- Document how the integration registers/exposes the card as a Lovelace resource.
- If manual resource registration is required for a particular Lovelace mode, provide the exact URL and steps.
- The card should update alongside the integration through HACS/manual integration updates; users should not need a second repository or separate Bubble Card installation.
- Keep the backend independent of the frontend card.
