# Beta 5 implementation checklist

Target: `0.1.0-beta.5`  
Branch: `feature/beta-5-apple-dashboard`

This checklist tracks the work defined in [beta-5-plan.md](beta-5-plan.md). It is intentionally separate from the published beta.4 checklist.

## Live telemetry
- [ ] Current precise SOC mapping verified end-to-end.
- [ ] Odometer mapping verified end-to-end.
- [ ] Prominent live SOC and odometer presentation.
- [ ] Freshness/availability states; no fabricated zero values.
- [ ] Optional range entity only; no guessed range calculations.
- [ ] Automated tests for missing, unavailable and changing telemetry.

## Lovelace redesign
- [ ] Apple-inspired vehicle hero and clear information hierarchy.
- [ ] Latest charge summary redesigned.
- [ ] History and charts redesigned.
- [ ] Charging state transitions and purposeful motion.
- [ ] Reduced-motion support.
- [ ] Mobile, desktop, light and dark layouts checked.
- [ ] Accessibility: contrast, focus, labels and touch targets.

## Vehicle identity
- [ ] Live preview while editing identity fields.
- [ ] Image selection guidance and preview.
- [ ] Transparent PNG/WebP validation and fallback.
- [ ] Visual port-anchor adjustment.
- [ ] Correct vehicle/profile context shown.
- [ ] Shared identity remains consistent across charger profiles.

## Configuration feedback and refresh
- [ ] Save confirmation and summary.
- [ ] Errors shown clearly and recoverably.
- [ ] Existing card refreshes updated profile identity.
- [ ] Manual Lovelace overrides are preserved.
- [ ] No config-entry recreation required.

## Compatibility and release
- [ ] Existing config entries and profile IDs preserved.
- [ ] Existing tariffs preserved.
- [ ] Existing session history preserved.
- [ ] EVSE energy entity diagnostic investigated.
- [ ] Full CI green on PR.
- [ ] Post-merge CI green.
- [ ] Live Home Assistant update-in-place validation.
- [ ] Real charging session validated.
- [ ] HACS package/tag verified.
