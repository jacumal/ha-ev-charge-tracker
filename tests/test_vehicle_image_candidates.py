"""Tests for the Wikimedia Commons image candidate discovery helper."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "find_vehicle_image_candidates.py"
SPEC = importlib.util.spec_from_file_location("vehicle_image_candidates", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_license_normalization_and_allowed_filter():
    assert MODULE._license_key("<span>CC BY-SA 4.0</span>") == "cc by-sa 4.0"
    assert "cc by-sa 4.0" in MODULE.ALLOWED_LICENSES
    assert "all rights reserved" not in MODULE.ALLOWED_LICENSES


def test_candidate_scoring_prefers_front_quarter_and_penalizes_interior():
    preferred = MODULE._score("Tesla Model Y front three-quarter view.jpg", "Tesla Model Y")
    interior = MODULE._score("Tesla Model Y interior dashboard.jpg", "Tesla Model Y")
    assert preferred > interior


def test_commons_candidate_search_records_full_provenance():
    import inspect

    source = inspect.getsource(MODULE.search_model)
    for field in (
        "descriptionurl", "LicenseShortName", "LicenseUrl", "Artist",
        "AttributionRequired", "thumburl", "review_status",
    ):
        assert field in source
