# Beta 6 — Free vehicle gallery and visual dashboard

**Branch:** `feature/beta-6-free-vehicle-gallery`  
**Base:** beta.5 candidate (`b6aaf06948272ade93364088cc07e6e7feb896b6`)  
**Scope boundary:** vehicle image gallery and Lovelace card presentation only. No tariff engine, sensor model, charging-session logic or new statistics.

## Approved visual references

The two owner-supplied screenshots define the acceptance target:
- Idle / no valid latest session: large vehicle image, status pill, current battery, explicitly mapped range, odometer, freshness indicator and an empty latest-charge summary.
- Connected / charging or completed: same vehicle hero, clear cable state, live telemetry, latest-session summary, SOC progression, energy, duration, cost, tariff label and history overview.

The vehicle is the visual hero, not a small thumbnail. The card must remain readable on mobile and desktop, and in light/dark themes. Existing display-density options remain supported.

## Free vehicle image gallery

- Search Wikimedia Commons using its public MediaWiki Action API.
- Restrict image URLs to HTTPS assets hosted on `upload.wikimedia.org`.
- Only offer files whose machine-readable `LicenseShortName` is recognized as CC0, Public Domain, CC BY or CC BY-SA (supported versions explicitly allowlisted in code).
- Never silently accept NC/ND, unknown, missing or unrecognized license metadata.
- Preserve creator/credit, license name, license URL and Commons file-description page with the selected image.
- Show attribution in the editor preview and on the card.
- Store the selected image and its attribution in a per-vehicle map inside the Lovelace card configuration, not as one global integration image.
- Use a stable vehicle identity (brand/model when available, otherwise vehicle name) so charger profiles belonging to the same vehicle reuse the same selection.
- Keep each vehicle's image independent when a user configures multiple EVs, and allow changing the selection at any time.
- Prefill the gallery search from the selected vehicle identity; preserve a user's manually edited search query.
- Keep local PNG/WebP image paths supported as a manual fallback.
- Do not bundle third-party image binaries into the integration repository or imply that all Commons images are transparent.
- Commons API failure, no results, missing metadata and image load failure must leave the existing local/fallback vehicle visual usable.

## Card presentation

- Large model-specific vehicle image centered beneath the card header.
- Vehicle name and model details aligned with the hero.
- For Leapmotor C10, default the cable anchor to the rear-left quarter-panel charge port; keep the anchor user-adjustable.
- Distinct idle/connected/charging/completed/attention pill and cable animation retained.
- Current battery percentage and progress bar, optional explicitly mapped autonomy, and odometer.
- Telemetry freshness remains visible and stale values are not presented as current.
- Latest-charge summary retains truthful empty/missing/partial states.
- Five session metrics remain legible, with responsive stacking on narrow screens.
- Charts and history remain available under the existing display-density settings.

## Acceptance gates

- [ ] Commons search returns only recognized free-license results.
- [ ] Search results display thumbnail, title, creator and license.
- [ ] Selecting an image stores the image URL and all attribution fields in the selected vehicle's Lovelace configuration.
- [ ] Two different vehicles can retain different images in the same user's dashboard.
- [ ] Multiple charger profiles for the same vehicle reuse that vehicle's image selection.
- [ ] Switching profiles restores the correct image and gallery search identity.
- [ ] Selected images survive editor close/reopen and Home Assistant restart.
- [ ] Attribution links point to the Commons file page.
- [ ] Unlicensed/unknown-license images are excluded.
- [ ] Malformed URLs and non-Wikimedia hosts are rejected.
- [ ] Local PNG/WebP images continue to work.
- [ ] Broken remote image falls back safely without breaking the card.
- [ ] Approved idle and charging layouts are reproduced responsively.
- [ ] Existing charge states, history, cost quality and tariff labels remain unchanged.
- [ ] JavaScript syntax/behavior tests and repository CI pass.
- [ ] Real Home Assistant mobile/desktop, light/dark and save/reopen checks pass.

## Known limitations

Wikimedia Commons contains photographs and renders with varied framing/backgrounds; a free license does not guarantee a transparent cut-out or an exact studio angle. The gallery must label licensing accurately and let the user choose. The first version uses remote Commons thumbnails; therefore the selected image requires an internet connection unless the user supplies a local copy. A later offline-cache/download feature is outside beta.6 scope.
