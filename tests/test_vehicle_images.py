"""Tests for the authenticated local vehicle image upload endpoint."""

import json
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from aiohttp import web

from custom_components.ev_charge_tracker.vehicle_images import (
    MAX_IMAGE_BYTES,
    VehicleImageUploadView,
)


class FakeAlpha:
    def __init__(self, valid=True):
        self.valid = valid

    def getextrema(self):
        return (0, 255) if self.valid else (255, 255)

    def histogram(self):
        values = [0] * 256
        values[0] = 1200 * 675 // 2
        values[255] = 1200 * 675 // 2
        return values


class FakeImage:
    format = "PNG"
    size = (1200, 675)
    width = 1200
    height = 675

    def __init__(self, valid_alpha=True):
        self.valid_alpha = valid_alpha

    def load(self):
        return None

    def getbands(self):
        return ("R", "G", "B", "A")

    def getchannel(self, channel):
        assert channel == "A"
        return FakeAlpha(self.valid_alpha)


class VehicleImageUploadTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.body = b"normalized-png-content"
        self.image = FakeImage()

        image_module = types.SimpleNamespace(open=lambda stream: self.image)
        pil_module = types.ModuleType("PIL")
        pil_module.Image = image_module
        pil_module.UnidentifiedImageError = type("UnidentifiedImageError", (OSError,), {})
        self.pil_patch = patch.dict("sys.modules", {"PIL": pil_module})
        self.pil_patch.start()
        self.addCleanup(self.pil_patch.stop)

        async def run_in_executor(function, *args):
            return function(*args)

        hass = types.SimpleNamespace(
            config=types.SimpleNamespace(path=lambda path: str(self.root / path)),
            async_add_executor_job=run_in_executor,
        )
        self.view = VehicleImageUploadView(hass)

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, body=None, content_type="image/png", content_length=None):
        payload = self.body if body is None else body
        return types.SimpleNamespace(
            content_type=content_type,
            content_length=len(payload) if content_length is None else content_length,
            content=types.SimpleNamespace(read=AsyncMock(return_value=payload)),
        )

    async def test_valid_normalized_transparent_png_is_saved_locally(self):
        request = self.request()

        response = await self.view.async_post(request)

        self.assertEqual(response.status, 201)
        result = json.loads(response.text)
        self.assertRegex(
            result["path"],
            r"^/local/ev-charge-tracker/custom/[a-f0-9]{64}\.png$",
        )
        stored = self.root / "www" / "ev-charge-tracker" / "custom" / (
            result["path"].rsplit("/", 1)[-1]
        )
        self.assertTrue(stored.is_file())
        self.assertEqual(stored.read_bytes(), self.body)

    async def test_rejects_non_png_content_type(self):
        with self.assertRaises(web.HTTPUnsupportedMediaType):
            await self.view.async_post(self.request(content_type="image/webp"))

    async def test_rejects_payload_larger_than_eight_megabytes(self):
        with self.assertRaises(web.HTTPRequestEntityTooLarge):
            await self.view.async_post(
                self.request(body=b"x", content_length=MAX_IMAGE_BYTES + 1)
            )

    async def test_rejects_png_without_transparency(self):
        self.image = FakeImage(valid_alpha=False)
        with self.assertRaises(web.HTTPBadRequest):
            await self.view.async_post(self.request())

    async def test_rejects_oversized_stream_even_without_content_length(self):
        with self.assertRaises(web.HTTPRequestEntityTooLarge):
            await self.view.async_post(
                self.request(body=b"x" * (MAX_IMAGE_BYTES + 1), content_length=0)
            )


if __name__ == "__main__":
    unittest.main()
