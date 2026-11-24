# Beta 9 validation checklist — vehicle image catalog

## Repository / automated checks
- [x] Version metadata set to `0.1.0-beta.9`.
- [x] Catalog selector includes Leapmotor C10, B10 and T03.
- [x] Catalog includes the 2025 global BEV leaders and representative European BEVs.
- [x] The last selector option opens the personal image picker.
- [x] Personal image upload uses the authenticated Home Assistant API.
- [x] Uploaded files are stored only in the local Home Assistant `www/ev-charge-tracker/custom/` directory.
- [x] Uploads are limited to 8 MB and normalized to 1200 × 675 PNG with alpha.
- [x] C10 default render is served from the integration's local route.
- [ ] Final GitHub Actions CI is green on the latest PR head.
- [ ] Review generated HACS ZIP and confirm all new Python modules are packaged.

## Required live Home Assistant validation
- [ ] Update beta 8 in place without deleting the integration or config entries.
- [ ] Confirm all existing profiles, entity mappings, tariff settings and charging history remain intact.
- [ ] Open the Lovelace editor and verify the vehicle selector is populated.
- [ ] Confirm the personal image option is the final selector option.
- [ ] Upload a transparent PNG and verify the preview and card update.
- [ ] Repeat with a transparent WebP.
- [ ] Confirm JPEG, non-transparent PNG/WebP, files over 8 MB and invalid image dimensions are rejected.
- [ ] Restart Home Assistant and verify the uploaded image remains available.
- [ ] Confirm uploaded files are served from `/local/ev-charge-tracker/custom/`.
- [ ] Select different models on two vehicle profiles and verify their images do not overwrite each other.
- [ ] Reopen the card editor and verify the selected image persists.
- [ ] Restore the bundled C10 default after selecting a personal image.
- [ ] Verify the restore control clears a personal image for models without a bundled default.
- [ ] Check image composition on mobile/desktop and light/dark themes.

## Visual acceptance standard
- [ ] Front three-quarter view.
- [ ] Nose facing right.
- [ ] Full vehicle visible; no clipping.
- [ ] Transparent background.
- [ ] Same 1200 × 675 canvas and comparable vehicle scale.
- [ ] No mixed camera angles or photographic backgrounds in the built-in catalog.

## Explicit limitations
The editor validates transparency and canvas normalization, but it cannot reliably infer camera angle or vehicle direction. Models without a legally redistributable, visually compliant bundled render remain selectable and require a personal image. Do not mark those models as having a bundled render until the asset is included and license/source evidence is recorded.
