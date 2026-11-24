# EV Charge Tracker 0.1.0-beta.9 — Vehicle image catalog

## Included in this candidate

- Replaces the manual image-path field in the card editor with a vehicle selector.
- Includes Leapmotor C10, B10 and T03, the leading BEV models from the 2025 global sales ranking, and additional European-market models.
- Adds **Añadir una foto personal** as the final selector option.
- Uploads personal artwork directly to the authenticated Home Assistant instance.
- Stores uploaded files under `www/ev-charge-tracker/custom/`, addressed by SHA-256 content hash. No cloud image service is involved.
- Requires a transparent PNG/WebP source, limits uploads to 8 MB and normalizes accepted images to a 1200 × 675 transparent PNG canvas.
- Serves the bundled C10 render from the integration's local static route rather than the Leapmotor website.
- Adds a control to restore the model's bundled default image or clear a personal image when no bundled render exists.
- Keeps image selection in the Lovelace configuration per vehicle; it does not change charger profiles, session history, tariffs or sensor mappings.

## Visual asset policy

Every bundled render and user image must follow the same visual specification:

- front three-quarter view;
- vehicle nose facing right;
- entire vehicle visible, without cropping;
- transparent background;
- consistent 1200 × 675 canvas and visual scale.

The editor can check file type, dimensions, transparency and basic content presence, but it cannot reliably determine whether a source image has the correct vehicle orientation or camera angle. The user must choose an image that follows the visual guide.

## Catalog image availability

The catalog includes model identities even when a redistributable image is not yet available. Only the C10 has a bundled default render in this candidate. Other models remain selectable, but show the neutral no-image state until the user adds a personal image. This is intentional: images are not copied from manufacturer websites or other sources unless redistribution rights and visual consistency have been verified.

## Validation and known gates

- Automated JavaScript and Python tests must pass on the final PR head.
- Verify upload authentication, rejection of non-PNG requests, oversize payloads, non-transparent images and invalid canvas dimensions.
- In a real Home Assistant instance, verify the upload survives restart and is served from `/local/ev-charge-tracker/custom/`.
- Verify selection persists after closing/reopening the Lovelace editor and is isolated per vehicle.
- Compare all selected images in the card on mobile/desktop and light/dark themes.
- Confirm update-in-place preserves all existing profiles, sensors, tariffs and charge history.

This is a beta candidate, not a claim of completed live Home Assistant validation.
