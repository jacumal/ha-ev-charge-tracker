# Beta 5 implementation checklist

Target: `0.1.0-beta.5`  
Branch: `feature/beta-5-apple-dashboard`

This checklist tracks the work defined in [beta-5-plan.md](beta-5-plan.md). It is intentionally separate from the published beta.4 checklist.

## Live telemetry
- [ ] Current precise SOC mapping verified end-to-end.
- [ ] Odometer mapping verified end-to-end.
- [x] Prominent live SOC and odometer presentation.
- [x] Freshness/availability states; stale primary telemetry is hidden rather than presented as current, and invalid values are not replaced with zero.
- [x] Optional range entity only; no guessed range calculations (configurable from profile options and surfaced to Lovelace).
- [ ] Automated tests for missing, unavailable and changing telemetry.

## Lovelace redesign
- [x] Apple-inspired vehicle hero and clear information hierarchy.
- [ ] Latest charge summary redesigned.
- [ ] History and charts redesigned.
- [x] Charging state transitions and purposeful motion.
- [x] Reduced-motion support.
- [ ] Mobile, desktop, light and dark layouts checked.
- [ ] Accessibility: contrast, focus, labels and touch targets.

## Vehicle identity
- [x] Live preview while editing identity fields.
- [x] Local image path guidance and preview (manual copy to /config/www; no upload control).
- [x] Local PNG/WebP path validation and fallback silhouette; transparency is recommended in the editor guidance but the alpha channel is not inspected.
- [x] Visual port-anchor adjustment controls.
- [x] Correct vehicle/profile context shown.
- [x] Shared identity remains consistent across charger profiles (registry regression test).

## Configuration feedback and refresh
- [ ] Save confirmation and summary.
- [x] Profile refresh errors are shown with a retry path; save confirmation remains pending.
- [x] Existing cards refresh selected profile identity without reconstruction.
- [x] Manual Lovelace entity overrides and card-specific vehicle identity overrides are preserved.
- [ ] No config-entry recreation required.

## Compatibility and release
- [ ] Existing config entries and profile IDs preserved.
- [ ] Existing tariffs preserved.
- [ ] Existing session history preserved.
- [x] EVSE source diagnostics added (entity, state, unit, timestamp, age and validity reason); confirm against the user's live EVSE entity still pending.
- [ ] Full CI green on PR.
- [ ] Post-merge CI green.
- [ ] Live Home Assistant update-in-place validation.
- [ ] Real charging session validated.
- [ ] HACS package/tag verified.
