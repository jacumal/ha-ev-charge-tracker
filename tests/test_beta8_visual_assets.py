"""Beta 8 regression checks for visual assets and static serving."""
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components/ev_charge_tracker"
BRAND = INTEGRATION / "brand"
CARD = INTEGRATION / "frontend/ev-charge-tracker-card.js"
INIT = INTEGRATION / "__init__.py"


def test_marketplace_icon_meets_home_assistant_brand_dimensions():
    with Image.open(BRAND / "icon.png") as icon:
        assert icon.format == "PNG"
        assert icon.size == (256, 256)


def test_marketplace_logo_is_horizontal_and_large_enough():
    with Image.open(BRAND / "logo.png") as logo:
        assert logo.format == "PNG"
        assert logo.width > logo.height
        assert min(logo.size) >= 128


def test_bundled_c10_image_is_decodable_webp_with_transparency():
    image_path = BRAND / "leapmotor-c10-white.webp"
    with Image.open(image_path) as image:
        assert image.format == "WEBP"
        assert image.mode in ("RGBA", "LA")
        assert image.width >= 400
        assert image.height >= 180
        image.verify()


def test_card_and_editor_share_the_registered_c10_image_url():
    init = INIT.read_text(encoding="utf-8")
    card = CARD.read_text(encoding="utf-8")
    image_url = "/ev_charge_tracker/vehicle-images/leapmotor-c10-white.webp"
    assert f'C10_IMAGE_URL = "{image_url}"' in init
    assert f'const defaultC10Image = "{image_url}"' in card
    assert image_url in card


def test_static_assets_are_registered_idempotently_for_setup_and_entry_reload():
    init = INIT.read_text(encoding="utf-8")
    assert "async def _async_register_static_paths" in init
    assert "STATIC_PATHS_REGISTERED_KEY" in init
    assert 'StaticPathConfig(C10_IMAGE_URL, str(c10_image_path), cache_headers=False)' in init
    assert "await _async_register_static_paths(hass)" in init
    assert init.count("await _async_register_static_paths(hass)") == 2


def test_broken_profile_image_retries_the_bundled_c10_image_before_fallback():
    card = CARD.read_text(encoding="utf-8")
    assert "customVehicleImage.dataset.c10FallbackAttempted" in card
    assert "imageNode.dataset.c10FallbackAttempted" in card
    assert "Imagen del vehículo no disponible" in card
    assert "Imagen no disponible" in card
