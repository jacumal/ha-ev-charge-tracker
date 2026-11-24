#!/usr/bin/env python3
"""Find openly licensed vehicle-photo candidates on Wikimedia Commons.

This script only builds a review manifest. It never downloads or bundles an image
automatically: vehicle identity, camera angle, orientation, background removal
and license details must be checked by a maintainer before packaging.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "custom_components" / "ev_charge_tracker" / "vehicle_catalog.json"
OUTPUT = ROOT / "docs" / "data" / "vehicle_image_candidates.json"
API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "ChargeTrackVehicleCatalog/0.1 (https://github.com/jacumal/ha-ev-charge-tracker)"
ALLOWED_LICENSES = {
    "cc0", "public domain", "cc by 4.0", "cc by-sa 4.0",
    "cc by 3.0", "cc by-sa 3.0", "cc by 2.5", "cc by-sa 2.5",
    "cc by 2.0", "cc by-sa 2.0",
}
BAD_TERMS = ("interior", "dashboard", "wheel", "engine", "logo", "toy", "model kit", "rear view")


def _text(metadata: dict, key: str) -> str:
    value = metadata.get(key, {})
    raw = str(value.get("value", "")) if isinstance(value, dict) else str(value)
    return html.unescape(re.sub(r"<[^>]+>", " ", raw)).strip()


def _license_key(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value).lower()
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _score(title: str, model: str) -> int:
    title_lower = title.lower()
    model_tokens = [token for token in re.findall(r"[a-z0-9]+", model.lower()) if len(token) > 1]
    score = sum(5 for token in model_tokens if token in title_lower)
    if "front" in title_lower:
        score += 4
    if any(token in title_lower for token in ("quarter", "three-quarter", "3/4")):
        score += 4
    if any(token in title_lower for token in BAD_TERMS):
        score -= 20
    return score


def search_model(vehicle: dict, limit: int = 8) -> list[dict]:
    names = [vehicle["label"], *(vehicle.get("aliases") or [])[:2]]
    query = " OR ".join(f'"{name}"' for name in names) + " car"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": 6,
        "gsrlimit": limit,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1800,
        "format": "json",
        "formatversion": 2,
    }
    request = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    candidates = []
    for page in payload.get("query", {}).get("pages", []):
        info = (page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        license_name = _text(metadata, "LicenseShortName")
        if _license_key(license_name) not in ALLOWED_LICENSES:
            continue
        title = page.get("title", "")
        image_url = info.get("thumburl") or info.get("url")
        if not image_url:
            continue
        candidates.append({
            "title": title,
            "image_url": image_url,
            "source_page": info.get("descriptionurl", ""),
            "author": _text(metadata, "Artist"),
            "credit": _text(metadata, "Credit"),
            "license": license_name,
            "license_url": _text(metadata, "LicenseUrl"),
            "attribution_required": _text(metadata, "AttributionRequired"),
            "width": info.get("width"),
            "height": info.get("height"),
            "score": _score(title, vehicle["label"]),
            "review_status": "needs_visual_and_license_review",
        })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Only process the first N models (0 = all)")
    parser.add_argument("--delay", type=float, default=0.35, help="Seconds between Commons API requests")
    args = parser.parse_args()

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    vehicles = catalog["vehicles"][: args.limit or None]
    results = []
    for index, vehicle in enumerate(vehicles, start=1):
        try:
            candidates = search_model(vehicle)
            results.append({
                "vehicle_id": vehicle["id"],
                "vehicle": vehicle["label"],
                "technology": vehicle["technology"],
                "candidates": candidates[:5],
                "status": "candidates_found" if candidates else "no_licensed_candidate_found",
            })
        except Exception as error:  # Keep the batch moving; report per-model failures.
            results.append({
                "vehicle_id": vehicle["id"],
                "vehicle": vehicle["label"],
                "technology": vehicle["technology"],
                "candidates": [],
                "status": "search_error",
                "error": str(error),
            })
        print(f"[{index}/{len(vehicles)}] {vehicle['label']}: {len(results[-1]['candidates'])} candidates")
        time.sleep(max(0.0, args.delay))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps({
            "source": "Wikimedia Commons API",
            "license_filter": sorted(ALLOWED_LICENSES),
            "results": results,
            "notice": "Candidates are not approved assets. Review exact model, derivative rights, author, license, angle and image quality before bundling.",
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    found = sum(bool(item["candidates"]) for item in results)
    print(f"Saved {OUTPUT}; {found}/{len(results)} models have at least one candidate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
