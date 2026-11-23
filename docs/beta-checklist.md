# Beta candidate checklist

Target candidate: `0.1.0-beta.3`

This checklist separates repository/CI readiness from behavior that can only be
verified in a real Home Assistant installation.

## Repository and CI
- [x] Version metadata set in the integration manifest.
- [x] HACS metadata present.
- [x] MIT license included.
- [x] Lovelace card source is bundled with the integration.
- [x] Vehicle visual identity is stored per vehicle and shared across its charger profiles.
- [x] Card includes a transparent local thumbnail/fallback silhouette and animated cable/energy states.
- [x] Vehicle image paths are restricted to local PNG/WebP assets; no paid image API or external service is required.
- [x] Previous beta.3 baseline passed CI (run #172, commit `3484dbe`).
- [x] Consolidated beta.3 candidate passes CI (PR #13 run #217, commit `0e65a45`).
- [ ] Post-merge main-branch CI completes successfully.
- [ ] Verify the HACS release/tag installation path and packaged file layout.
- [x] Publish release notes with known limitations and upgrade instructions (`docs/release-notes-beta-3.md`).

## Real Home Assistant validation (required before production use)

The automated candidate checks do not close these live-instance gates. Do not treat beta.3 as production-validated until they are completed.
- [ ] Install/update from the beta candidate without removing the existing config entry.
- [ ] Confirm all configured entity selectors and tariff/unit options are usable.
- [ ] Confirm the Lovelace card JavaScript is served and the visual editor loads.
- [ ] Configure make/model/generation/year/trim/body style/color and verify they survive restart.
- [ ] Add a transparent PNG/WebP under `www/ev-charge-tracker/` and verify it loads through `/local/ev-charge-tracker/` in light and dark themes.
- [ ] Verify fallback silhouette when no custom image is configured.
- [ ] Adjust horizontal/vertical charge-port anchors for a custom image and confirm cable alignment.
- [ ] Verify cable states: disconnected, connected-but-idle (using the optional plugged sensor), charging with animated energy flow, completed and attention/error.
- [ ] Verify reduced-motion preference disables continuous cable animation.
- [ ] Confirm the live battery SOC and odometer values are auto-mapped from the selected profile and displayed correctly.
- [ ] Confirm energy and cost charts match stored sessions, including partial and missing costs.
- [ ] Confirm conditional tariff price fields and source switching preserve existing values.
- [ ] Confirm profile settings and history survive a Home Assistant restart.
- [ ] Confirm sensors report sensible idle/unknown values before a real session.
- [ ] Validate a complete real charge: start, energy deltas, SOC, stop grace period,
      final energy, cost, tariff breakdown and persisted history.
- [ ] Confirm no duplicate session or history record is created after restart/reload.

Do not create simulated sessions or overwrite/delete existing history to satisfy
this checklist. Record actual results and Home Assistant logs for each item.
