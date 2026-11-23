# Beta 5 implementation plan — Apple-inspired vehicle dashboard

**Target:** `0.1.0-beta.5`  
**Development branch:** `feature/beta-5-apple-dashboard`  
**Baseline:** published `v0.1.0-beta.4`  
**Rule:** beta.4 remains immutable. All beta.5 work is developed and tested on this branch; no changes are made directly to `main`.

## Product objective

Turn the Lovelace card into a polished, mobile-first EV dashboard with an Apple-inspired visual language: calm hierarchy, excellent typography, restrained materials, purposeful motion, clear live telemetry and a coherent vehicle identity. The integration remains useful without the card, and no feature may require deleting/recreating a config entry.

## Workstreams and acceptance criteria

### 1. Live vehicle telemetry
- [ ] Verify profile registry → WebSocket → Lovelace editor → card mapping for precise current SOC and odometer.
- [ ] Make current SOC and odometer prominent in the primary vehicle header/hero, not hidden as secondary metrics.
- [ ] Show source availability and freshness; unknown/unavailable/stale values render as unavailable, never zero or fabricated.
- [ ] Add estimated range only when an explicit valid range entity is configured; do not derive a misleading range from a nominal battery size.
- [ ] Add tests for selected, missing, unavailable and changing live telemetry.

### 2. Apple-inspired card redesign
- [ ] Define a new visual system: typography scale, spacing, surfaces, subtle depth, restrained gradients and status colors.
- [ ] Design a vehicle hero with model identity, live SOC, odometer, optional range and charging state.
- [ ] Redesign latest-session summary with clear SOC progression, energy, duration, cost and tariff breakdown.
- [ ] Redesign history and energy/cost charts with clear empty, partial and unavailable states.
- [ ] Add purposeful micro-interactions and charging animation; honor `prefers-reduced-motion`.
- [ ] Verify responsive layouts, touch targets, contrast, keyboard accessibility, and HA light/dark themes.
- [ ] Keep rendering self-contained; no remote assets, paid APIs or new frontend dependencies.

### 3. Vehicle identity editor and live preview
- [ ] Add an in-editor live preview that reacts to brand, model, generation, year, trim, color, body style and port-anchor changes.
- [ ] Add image selection/upload guidance with a clear preview, file validation and transparent-image guidance; keep local-only PNG/WebP support.
- [ ] Show a visible fallback silhouette when no image is selected or the image fails to load.
- [ ] Make port-anchor adjustment understandable, ideally with a visual draggable marker/controls and immediate cable alignment preview.
- [ ] Show the selected vehicle and charger profile being edited.
- [ ] Preserve existing identity values when editing a sibling charger profile for the same vehicle.

### 4. Save feedback and live Lovelace refresh
- [ ] Provide explicit success/error feedback and a concise summary after saving options.
- [ ] Ensure profile registry reflects updated options after save/reload.
- [ ] Ensure an already-configured card can refresh its selected profile identity without users deleting/re-adding or manually rebuilding the card.
- [ ] Avoid stale cached profile data; define a safe refresh/subscription strategy and test it.
- [ ] Preserve Lovelace manual overrides and existing card configuration.

### 5. Reliability, compatibility and migration
- [ ] Preserve config-entry IDs, profile mappings, tariff definitions, coordinator storage and charge history.
- [ ] Add regression tests for in-place upgrade and option changes across multiple charger profiles.
- [ ] Validate custom image paths and handle missing/invalid assets gracefully.
- [ ] Validate the actual EVSE energy sensor mapping shown as unavailable in the beta.4 test installation; diagnose the source mapping separately from the visual redesign.
- [ ] Update translations, documentation, screenshots and release notes.

## Suggested implementation order

1. Reproduce and fix the live telemetry/profile propagation path.
2. Define the new card layout and implement the vehicle hero.
3. Implement the visual editor preview and image/port controls.
4. Implement save feedback and live profile refresh.
5. Finish session/history redesign, responsive/accessibility checks and regression tests.
6. Run the full CI suite, review the diff, and prepare the beta.5 release candidate.

## Release gates

- [ ] Automated Python and frontend tests pass.
- [ ] JavaScript syntax and translation validation pass.
- [ ] Profile and session-history preservation tests pass.
- [ ] Card behavior tests cover live SOC, odometer, image fallback, identity updates and reduced motion.
- [ ] Beta.5 PR CI passes and post-merge CI passes.
- [ ] Real Home Assistant validation: update in place, edit vehicle identity, verify preview/save/refresh, verify precise SOC and odometer, test mobile/light/dark layouts, and complete a real charge.
- [ ] HACS/tag packaging verified.

**Do not call beta.5 production-validated until the real Home Assistant gates are completed.**
