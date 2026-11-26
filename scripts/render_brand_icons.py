"""Render or verify ChargeTrack's light/dark Home Assistant brand icons.

The SVG masters are the source of truth. PNGs are committed to the repository;
CI uses --check to ensure they are reproducible without writing to the PR branch.
"""
import argparse
from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "ev_charge_tracker" / "brand"
SIZES = (("", 256), ("@2x", 512))


def render_icons(check: bool = False) -> None:
    failed = []
    for stem in ("icon", "dark_icon"):
        source = BRAND / f"{stem}.svg"
        svg = source.read_bytes()
        for suffix, size in SIZES:
            png_path = BRAND / f"{stem}{suffix}.png"
            rendered = cairosvg.svg2png(
                bytestring=svg, output_width=size, output_height=size
            )
            with Image.open(BytesIO(rendered)) as image:
                if image.size != (size, size):
                    raise ValueError(
                        f"{png_path.name}: rendered size {image.size}, expected {(size, size)}"
                    )
                image.verify()

            if check:
                if not png_path.is_file() or png_path.read_bytes() != rendered:
                    failed.append(png_path.relative_to(ROOT).as_posix())
                else:
                    print(f"Verified {png_path.relative_to(ROOT)} ({size}x{size})")
            else:
                png_path.write_bytes(rendered)
                print(f"Rendered {png_path.relative_to(ROOT)} ({size}x{size})")

    if failed:
        paths = "\n".join(f"- {path}" for path in failed)
        raise SystemExit(
            "Generated icon PNGs are missing or out of date. "
            "Run python scripts/render_brand_icons.py and commit the results:\n"
            + paths
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed PNGs match the SVG masters without modifying files",
    )
    args = parser.parse_args()
    render_icons(check=args.check)
