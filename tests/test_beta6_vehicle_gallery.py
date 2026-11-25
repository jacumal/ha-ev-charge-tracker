"""Regression contract checks for beta 9 vehicle catalog and local image upload."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/ev_charge_tracker"
CARD = PACKAGE / "frontend/ev-charge-tracker-card.js"


def test_manifest_is_beta9():
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.1.0-beta.9"


def test_catalog_contains_all_400_source_models_plus_leapmotor_b10():
    catalog = json.loads((PACKAGE / "vehicle_catalog.json").read_text(encoding="utf-8"))
    vehicles = catalog["vehicles"]
    assert catalog["source_row_count"] == 400
    assert len(vehicles) == 401
    assert len({vehicle["id"] for vehicle in vehicles}) == 401
    assert sum(vehicle["technology"] == "BEV" for vehicle in vehicles) == 201
    assert sum(vehicle["technology"] == "PHEV" for vehicle in vehicles) == 200
    labels = {vehicle["label"] for vehicle in vehicles}
    for model in (
        "Leapmotor B10", "Leapmotor C10", "Leapmotor T03",
        "Tesla Model Y", "Tesla Model 3", "Geely Galaxy Xingyuan",
        "Wuling Hongguang Mini EV", "BYD Seagull", "Xiaomi SU7",
        "BYD Yuan Up", "BYD Dolphin", "BYD Yuan Plus", "XPeng Mona M03",
        "Volkswagen ID.3", "Volkswagen ID.4", "Renault 5 E-Tech",
    ):
        assert model in labels
    assert all(vehicle["image"] for vehicle in vehicles if vehicle["id"] == "leapmotor-c10")
    tesla = next(vehicle for vehicle in vehicles if vehicle["id"] == "tesla-model-y")
    assert tesla["image_status"] == "candidate_needs_background_removal_and_review"
    assert tesla["image_author"] == "Daniel.Cardenas"
    assert tesla["image_license"] == "CC BY-SA 4.0"
    assert tesla["image_source_page"].startswith("https://commons.wikimedia.org/wiki/File:")
    card = CARD.read_text(encoding="utf-8")
    assert 'id="visual_catalog"' in card
    assert "Híbridos enchufables (PHEV · " not in card
    assert "100 % eléctricos (BEV · " not in card
    assert 'option value="__generic__">Vehículo genérico' in card
    assert 'option value="__personal__">Subir imagen propia…' in card
    assert '.filter(item => Boolean(item.image))' in card


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
    assert 'image.size != CANVAS_SIZE' in endpoint


def test_card_resource_uses_stable_url_and_local_asset_route():
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'CARD_URL = "/ev_charge_tracker/ev-charge-tracker-card.js"' in init
    assert "cache_headers=False" in init
    assert 'StaticPathConfig(VEHICLE_IMAGES_URL' in init
    assert 'VEHICLE_CATALOG_URL = "/ev_charge_tracker/vehicle-catalog.json"' in init
    assert 'StaticPathConfig(VEHICLE_CATALOG_URL' in init
    assert (PACKAGE / "vehicle_catalog.json").is_file()


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
    for image in (logo, dark_logo):
        width, height = struct.unpack(">II", image[16:24])
        assert height == 128
        assert width >= height
