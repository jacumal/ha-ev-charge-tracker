"""Regression contract checks for the beta.6 Commons vehicle gallery.

These static checks complement browser tests: Home Assistant's custom card must
still be exercised in a real frontend before beta.6 is considered release-ready.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/ev_charge_tracker/frontend/ev-charge-tracker-card.js"


def test_gallery_uses_commons_public_api_and_https_upload_host_only():
    source = CARD.read_text(encoding="utf-8")
    assert "https://commons.wikimedia.org/w/api.php?" in source
    assert 'url.hostname === "upload.wikimedia.org"' in source
    assert 'url.protocol === "https:"' in source
    assert "upload\\.wikimedia\\.org" in source


def test_gallery_filters_to_recognized_free_licenses():
    source = CARD.read_text(encoding="utf-8")
    assert "CC0" in source
    assert "Public domain" in source
    assert "CC BY 4" in source
    assert "CC BY-SA 4" in source
    assert "!allowed.test(license)" in source


def test_gallery_selection_is_stored_per_vehicle_not_globally():
    source = CARD.read_text(encoding="utf-8")
    assert "vehicle_visuals" in source
    assert "_profileVisualKey(profile)" in source
    assert "next.vehicle_visuals = {" in source
    assert "const suggestedQuery =" in source


def test_selected_image_keeps_attribution_metadata():
    source = CARD.read_text(encoding="utf-8")
    for field in (
        "visual_image_credit",
        "visual_image_license",
        "visual_image_license_url",
        "visual_image_page",
        "visual_image_source",
    ):
        assert field in source
    assert "vehicle-image-credit" in source
    assert "rel=\"noopener noreferrer\"" in source


def test_local_images_remain_supported_and_remote_hosts_are_validated():
    source = CARD.read_text(encoding="utf-8")
    assert "/local/ev-charge-tracker/" in source
    assert "this._validVehicleImage(value)" in source
    assert "url.hostname === \"upload.wikimedia.org\"" in source


def test_current_manifest_version_is_beta8():
    import json

    manifest = json.loads(
        (ROOT / "custom_components/ev_charge_tracker/manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["version"] == "0.1.0-beta.8"


def test_lovelace_resource_uses_stable_url_without_long_lived_cache_headers():
    init = (ROOT / "custom_components/ev_charge_tracker/__init__.py").read_text(
        encoding="utf-8"
    )
    assert 'CARD_URL = "/ev_charge_tracker/ev-charge-tracker-card.js"' in init
    assert "cache_headers=False" in init
