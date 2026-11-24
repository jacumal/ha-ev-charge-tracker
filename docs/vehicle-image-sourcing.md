# Vehicle image sourcing and licensing

## Catalog

The catalog is based on `docs/data/ChargeTrack_catalogo_global_400.csv` and packaged as `custom_components/ev_charge_tracker/vehicle_catalog.json`. It contains 200 BEV and 200 PHEV models. Leapmotor B10 is an additional 401st entry because it was requested separately and is not present in the supplied 400-row file.

## Candidate source

The first candidate source is Wikimedia Commons. Each file has its own author and license; Commons asks reusers to verify the file's license and comply with attribution and share-alike conditions where applicable. The repository must retain the file description page, author, license name and license URL for every bundled asset.

Run:

```bash
python scripts/find_vehicle_image_candidates.py
```

For a small test batch:

```bash
python scripts/find_vehicle_image_candidates.py --limit 10
```

The script writes `docs/data/vehicle_image_candidates.json`. It does not download or bundle images automatically. A result is only a candidate, not an approved image.

## Acceptance before bundling

Every image must pass all of these checks:

- It depicts the exact model/generation or a clearly equivalent regional badge/alias.
- The file's actual license permits redistribution in this repository and the attribution record is complete.
- It shows the whole vehicle in a consistent front three-quarter view, nose facing right.
- Background is removed cleanly; glass, mirrors, wheels, lights and body edges remain intact.
- It is normalized to a transparent 1200 × 675 canvas with a consistent vehicle scale.
- The final asset is visually reviewed in the card on mobile and desktop.

The initial beta 9 implementation only bundles the C10 image. The remaining catalog entries intentionally have no default image until a candidate has passed review. Do not use an unverified thumbnail or hotlink as a bundled asset.

## Sources not suitable for bulk mirroring

Car Image API terms explicitly prohibit bulk downloading, scraping, mirroring or archiving its images and catalog data, and prohibit offering renders as a standalone image library/dataset. A bulk export or self-hosted catalog requires a separate written agreement. It is therefore not used as a source for a 400-image repository bundle.

## Attribution

Keep attribution beside each asset in a machine-readable manifest, including:
- vehicle ID and display name;
- local asset path;
- original file title and source page;
- author/creator;
- exact license name and license URL;
- any required credit line;
- date retrieved and reviewer approval.

For CC BY-SA or other share-alike material, check that the derivative created by background removal and resizing is distributed under compatible terms.
