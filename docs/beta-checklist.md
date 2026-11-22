# Beta candidate checklist

Target candidate: `0.1.0-beta.3`

This checklist separates repository/CI readiness from behavior that can only be
verified in a real Home Assistant installation.

## Repository and CI
- [x] Version metadata set in the integration manifest.
- [x] HACS metadata present.
- [x] MIT license included.
- [x] Lovelace card source is bundled with the integration.
- [ ] CI is green on the final beta candidate commit.
- [ ] Verify the HACS release/tag installation path and packaged file layout.
- [ ] Publish release notes with known limitations and upgrade instructions.

## Real Home Assistant validation (required before production use)
- [ ] Install/update from the beta candidate without removing the existing config entry.
- [ ] Confirm all configured entity selectors and tariff/unit options are usable.
- [ ] Confirm the Lovelace card JavaScript is served and the visual editor loads.
- [ ] Confirm energy and cost charts match stored sessions, including partial and missing costs.
- [ ] Confirm conditional tariff price fields and source switching preserve existing values.
- [ ] Confirm profile settings and history survive a Home Assistant restart.
- [ ] Confirm sensors report sensible idle/unknown values before a real session.
- [ ] Validate a complete real charge: start, energy deltas, SOC, stop grace period,
      final energy, cost, tariff breakdown and persisted history.
- [ ] Confirm no duplicate session or history record is created after restart/reload.

Do not create simulated sessions or overwrite/delete existing history to satisfy
this checklist. Record actual results and Home Assistant logs for each item.
