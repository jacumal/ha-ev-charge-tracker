"""Render ChargeTrack's approved light/dark brand icon masters to Home Assistant PNG assets.

Requires: CairoSVG and Pillow.
The SVG masters are the source of truth; PNGs are generated at 256px and 512px.
"""
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "ev_charge_tracker" / "brand"

for stem in ("icon", "dark_icon"):
    source = BRAND / f"{stem}.svg"
    svg = source.read_bytes()
    for suffix, size in (("", 256), ("@2x", 512)):
        png_path = BRAND / f"{stem}{suffix}.png"
        rendered = cairosvg.svg2png(bytestring=svg, output_width=size, output_height=size)
        png_path.write_bytes(rendered)
        with Image.open(png_path) as image:
            image.verify()
        print(f"Rendered {png_path.relative_to(ROOT)} ({size}x{size})")
