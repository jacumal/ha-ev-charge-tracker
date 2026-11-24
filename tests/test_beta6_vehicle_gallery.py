"""Regression contract checks for beta 9 vehicle catalog and local image upload."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components/ev_charge_tracker"
CARD = PACKAGE / "frontend/ev-charge-tracker-card.js"


def test_manifest_is_beta9():
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.1.0-beta.9"


def test_catalog_contains_leapmotor_and_global_bev_models():
    source = CARD.read_text(encoding="utf-8")
    for model in (
        "Leapmotor C10", "Leapmotor B10", "Leapmotor T03",
        "Tesla Model Y", "Tesla Model 3", "Geely Galaxy Xingyuan",
        "Wuling Hongguang Mini EV", "BYD Seagull", "Xiaomi SU7",
        "BYD Yuan UP", "BYD Dolphin", "BYD Yuan Plus", "XPeng Mona M03",
        "Volkswagen ID.3", "Volkswagen ID.4", "Kia EV3", "Renault 5 E-Tech",
    ):
        assert model in source
    assert 'id="visual_catalog"' in source
    assert 'id="personalVehicleImage"' in source


def test_c10_default_is_served_from_the_integration_not_a_remote_host():
    source = CARD.read_text(encoding="utf-8")
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'DEFAULT_C10_IMAGE_URL = "/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp"' in source
    assert 'C10_IMAGE_URL = "/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp"' in init
    asset = PACKAGE / "brand" / "leapmotor-c10-white.webp"
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
    assert 'alpha_min == 255 or alpha_max == 0' in endpoint
    assert 'image.size != CANVAS_SIZE' in endpoint


def test_card_resource_uses_stable_url_and_local_asset_route():
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    assert 'CARD_URL = "/ev_charge_tracker/ev-charge-tracker-card.js"' in init
    assert "cache_headers=False" in init
    assert 'StaticPathConfig(C10_IMAGE_URL' in init


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
