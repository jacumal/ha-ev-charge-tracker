"""Regression contract checks for beta 9 vehicle catalog and local image upload."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/ev_charge_tracker"
CARD = PACKAGE / "frontend/ev-charge-tracker-card.js"


def test_manifest_is_beta9():
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.1.0-beta.9"


def test_catalog_contains_only_models_with_bundled_vehicle_images():
    catalog = json.loads((PACKAGE / "vehicle_catalog.json").read_text(encoding="utf-8"))
    vehicles = catalog["vehicles"]
    assert catalog["source_row_count"] == 26
    assert len(vehicles) == 26
    assert len({vehicle["id"] for vehicle in vehicles}) == 26
    assert all(vehicle["image"] for vehicle in vehicles)
    assert all(vehicle["image"].startswith("/ev_charge_tracker/vehicle-images/") for vehicle in vehicles)
    assert {vehicle["label"] for vehicle in vehicles} >= {
        "Leapmotor C10", "Tesla Model Y", "Tesla Model 3",
        "BYD Dolphin", "BYD Dolphin Surf", "BYD Seagull", "Leapmotor B10", "Xiaomi SU7", "XPeng Mona M03",
        "Mercedes-Benz EQA", "BMW iX1", "Audi Q4 e-tron", "Skoda Enyaq", "Cupra Born",
        "Volkswagen ID.3", "Renault 4 E-Tech", "Renault 5 E-Tech",
    }
    assets = PACKAGE / "brand" / "vehicle-images"
    from PIL import Image
    for vehicle in vehicles:
        filename = vehicle["image"].rsplit("/", 1)[-1]
        asset = assets / filename
        assert asset.is_file(), f"Missing bundled image: {filename}"
        assert asset.stat().st_size > 0, f"Empty bundled image: {filename}"
        with Image.open(asset) as image:
            assert image.width > 0 and image.height > 0
            assert "A" in image.getbands(), f"Image has no alpha channel: {filename}"
            alpha_min, alpha_max = image.getchannel("A").getextrema()
            assert alpha_min < 255 and alpha_max > 0, f"Image is not transparent: {filename}"
    generic = assets / "vehicle-generic.png"
    assert generic.is_file()
    card = CARD.read_text(encoding="utf-8")
    assert 'id="visual_catalog"' in card
    assert 'option value="__generic__">Vehículo genérico' in card
    assert 'option value="__personal__">➕ Añadir una foto personal' in card
    assert "DEFAULT_VEHICLE_CATALOG" not in card
    assert "full-401" not in card
    assert re.search(r"morro (?:orientado )?hacia la derecha", card)


def test_c10_default_is_served_from_the_integration_not_a_remote_host():
    source = CARD.read_text(encoding="utf-8")
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'DEFAULT_C10_IMAGE_URL = "/ev_charge_tracker/vehicle-images/Leapmotor-C10.png"' in source
    assert 'VEHICLE_IMAGES_URL = "/ev_charge_tracker/vehicle-images"' in init
    asset = PACKAGE / "brand" / "vehicle-images" / "Leapmotor-C10.png"
    assert asset.is_file()
    from PIL import Image
    with Image.open(asset) as image:
        assert image.size[0] > 0 and image.size[1] > 0
        assert "A" in image.getbands()
        assert image.getchannel("A").getextrema()[0] < 255
    assert "www.leapmotor.net/_next/image" not in source


def test_personal_upload_is_authenticated_local_and_normalized():
    source = CARD.read_text(encoding="utf-8")
    endpoint = (PACKAGE / "vehicle_images.py").read_text(encoding="utf-8")
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'Authorization: "Bearer " + token' in source
    assert 'url = "/api/ev_charge_tracker/vehicle-image"' in endpoint
    assert "requires_auth = True" in endpoint
    assert "MAX_IMAGE_BYTES = 8 * 1024 * 1024" in endpoint
    assert "CANVAS_SIZE = (1200, 675)" in endpoint
    assert 'Path("www") / "ev-charge-tracker" / "custom"' in endpoint
    assert "async_register_vehicle_image(hass)" in init
    assert "createImageBitmap(file)" in source
    assert "context.drawImage(source" in source
    assert 'canvas.toBlob(resolve, "image/png")' in source


def test_upload_endpoint_requires_transparency_and_png_canvas():
    endpoint = (PACKAGE / "vehicle_images.py").read_text(encoding="utf-8")
    assert 'request.content_type != "image/png"' in endpoint
    assert 'if "A" not in image.getbands()' in endpoint
    assert "alpha_min == 255" in endpoint
    assert "transparent_pixels < total_pixels * 0.12" in endpoint
    assert "image.size != CANVAS_SIZE" in endpoint


def test_card_resource_uses_stable_url_and_local_asset_route():
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'CARD_URL = "/ev_charge_tracker/ev-charge-tracker-card.js"' in init
    assert "cache_headers=False" in init
    assert "StaticPathConfig(VEHICLE_IMAGES_URL" in init
    assert 'VEHICLE_CATALOG_URL = "/ev_charge_tracker/vehicle-catalog.json"' in init
    assert "StaticPathConfig(VEHICLE_CATALOG_URL" in init
    assert len(json.loads((PACKAGE / "vehicle_catalog.json").read_text(encoding="utf-8"))["vehicles"]) == 26


def test_brand_assets_keep_marketplace_ready_dimensions():
    import struct

    brand = PACKAGE / "brand"
    icon = (brand / "icon.png").read_bytes()
    logo = (brand / "logo.png").read_bytes()
    dark_icon = (brand / "dark_icon.png").read_bytes()
    dark_logo = (brand / "dark_logo.png").read_bytes()
    for image in (icon, logo, dark_icon, dark_logo):
        assert image[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", icon[16:24]) == (256, 256)
    assert struct.unpack(">II", dark_icon[16:24]) == (256, 256)
    logo_width, logo_height = struct.unpack(">II", logo[16:24])
    dark_logo_width, dark_logo_height = struct.unpack(">II", dark_logo[16:24])
    assert (logo_width, logo_height) == (490, 110)
    assert (dark_logo_width, dark_logo_height) == (490, 110)


def test_brand_icon_masters_use_rounded_centered_geometry_and_hidpi_assets():
    brand = PACKAGE / "brand"
    for stem in ("icon", "dark_icon"):
        svg = (brand / f"{stem}.svg").read_text(encoding="utf-8")
        assert 'stroke-linecap="round"' in svg
        assert 'stroke-linejoin="round"' in svg
        assert 'viewBox="0 0 256 256"' in svg
        assert (brand / f"{stem}@2x.png").is_file()
