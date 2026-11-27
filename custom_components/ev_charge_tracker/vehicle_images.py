"""Secure local upload endpoint for per-installation vehicle artwork."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

MAX_IMAGE_BYTES = 8 * 1024 * 1024
CANVAS_SIZE = (1200, 675)


class VehicleImageUploadView(HomeAssistantView):
    """Accept only normalized transparent PNG artwork and store it locally."""

    url = "/api/ev_charge_tracker/vehicle-image"
    name = "api:ev_charge_tracker:vehicle-image"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def async_post(self, request: web.Request) -> web.Response:
        """Validate and persist a normalized transparent PNG."""
        if request.content_type != "image/png":
            raise web.HTTPUnsupportedMediaType(
                text="Solo se admiten imágenes PNG normalizadas."
            )
        if request.content_length is not None and request.content_length > MAX_IMAGE_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_IMAGE_BYTES, actual_size=request.content_length
            )

        body = await request.content.read(MAX_IMAGE_BYTES + 1)
        if not body or len(body) > MAX_IMAGE_BYTES:
            raise web.HTTPRequestEntityTooLarge(
                max_size=MAX_IMAGE_BYTES, actual_size=len(body)
            )

        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError as err:
            raise web.HTTPInternalServerError(
                text="Falta Pillow. Reinicia Home Assistant para instalar las dependencias de ChargeTrack."
            ) from err

        try:
            image = Image.open(io.BytesIO(body))
            if image.format != "PNG":
                raise ValueError("Formato no permitido")
            if image.size != CANVAS_SIZE:
                raise ValueError("La imagen debe estar normalizada a 1200 × 675 px")
            image.load()
            if "A" not in image.getbands():
                raise ValueError("La imagen debe incluir transparencia")
            alpha = image.getchannel("A")
            alpha_min, alpha_max = alpha.getextrema()
            histogram = alpha.histogram()
            total_pixels = image.width * image.height
            transparent_pixels = sum(histogram[:24])
            visible_pixels = sum(histogram[24:])
            if (
                alpha_min == 255
                or alpha_max == 0
                or transparent_pixels < total_pixels * 0.12
                or visible_pixels < total_pixels * 0.08
            ):
                raise ValueError(
                    "La imagen debe incluir un vehículo visible y al menos un 12 % de fondo transparente"
                )
        except (ValueError, OSError, UnidentifiedImageError) as err:
            raise web.HTTPBadRequest(
                text=f"Imagen no válida: {err}"
            ) from err
        except Exception as err:  # Pillow may raise decoder-specific errors.
            raise web.HTTPBadRequest(
                text="La imagen PNG no se puede decodificar."
            ) from err
        digest = hashlib.sha256(body).hexdigest()
        relative = Path("www") / "ev-charge-tracker" / "custom" / f"{digest}.png"
        destination = Path(self.hass.config.path(str(relative)))
        await self.hass.async_add_executor_job(destination.parent.mkdir, 0o755, True, True)
        await self.hass.async_add_executor_job(destination.write_bytes, body)

        return web.json_response(
            {"path": f"/local/ev-charge-tracker/custom/{digest}.png"},
            status=201,
        )


def async_register(hass: HomeAssistant) -> None:
    """Register the authenticated image upload endpoint."""
    hass.http.register_view(VehicleImageUploadView(hass))
