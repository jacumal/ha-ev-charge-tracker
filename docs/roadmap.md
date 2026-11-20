# Development roadmap and test-readiness gates

**Current status:** pre-alpha. The integration is not ready for real charging data.

The project owner has set this order. Work must follow it; do not start real-sensor testing until every gate is closed.

| Priority | Block | Current status | Exit criteria |
|---|---|---|---|
| 1 | Lovelace card | In progress | Card resource loads in HA; visual editor is usable; current/latest session and history render correctly; light/dark and mobile layouts verified; cost-quality states match backend. |
| 2 | Lifecycle | In progress | Automated coverage for start/stop, unknown/unavailable, restart recovery, delayed readings, all finalization strategies, unload/reload and persistent history; controlled HA lifecycle validation. |
| 3 | Statistics | Not started | Persistent, timezone-correct day/week/month aggregates; totals and averages; incomplete costs clearly separated; HA statistics metadata and reset behavior validated. |
| 4 | Quality and documentation | In progress | Current CI green on final candidate; Python/JS checks; translations; config/storage migration review; installation, upgrade, backup/recovery and test procedures consistent with implementation. |
| 5 | Profile management | Foundations only | Guided selection/reuse of vehicles and chargers; ownership validation; shared charger arbitration; multi-profile behavior and conflict cases tested. |

## Current evidence

- The branch contains a first custom Lovelace card, static resource serving and a README example. No live Home Assistant browser validation has been recorded.
- The card editor now uses Home Assistant `ha-entity-picker` controls for all eight semantic entity mappings. End-to-end editor validation in a live HA frontend is still needed.
- Coordinator recovery logic has unit tests for freshness, stale odometer observations, counter resets and the recovery decision matrix. Finalization regression tests cover the post-stop grace period, manual strategy, odometer freshness/increase requirements and missing energy. Config-entry lifecycle tests cover cleanup after first-refresh/platform-setup failures, successful setup and idempotent listener shutdown. Recovery-path tests also cover restoration of an active/pending session when the charger is ON, OFF or unavailable, preservation of history across restore, and delayed energy readings arriving after stop. These focused tests are not a substitute for executing the suite, exercising Home Assistant's real Store/restart/unload machinery, or controlled HA frontend validation.
- A read-only profile registry and conflict detection exist. The config flow does not yet provide complete reuse/selection or shared-charger arbitration.
- No daily/weekly/monthly statistics implementation or statistics-specific tests have been found in the current development scope.
- A JavaScript syntax check has been added to CI. The Lovelace editor now exposes native entity selectors; browser compatibility and persistence still need validation. A successful CI run for the final candidate has not yet been confirmed.

## Rules for the first real test

1. Close priorities 1 through 5 in the stated order, with tests and documentation updated at each gate.
2. Confirm CI is green for the exact candidate commit.
3. Review the final Lovelace card in Home Assistant (desktop/mobile and light/dark themes).
4. Only then install the candidate and map the user's real vehicle and charger sensors.
5. Keep PR #5 open; do not merge it without the project owner's explicit approval.

A disposable/synthetic test profile may be used earlier only if explicitly agreed as a separate development test. It does not count as authorization for the real charging test.
