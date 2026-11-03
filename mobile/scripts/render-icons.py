"""Render assets/brand/*.svg to the PNGs app.json uses (cairosvg; no browser needed).
Run after `npx tsx scripts/make-icons.ts`:  python scripts/render-icons.py
Windows alternative with Edge: node scripts/render-icons.mjs
"""
from pathlib import Path

import io

import cairosvg
from PIL import Image, ImageChops

ASSETS = Path(__file__).resolve().parents[1] / "assets"
JOBS = [
    ("icon.svg", "icon.png", 1024),
    ("android-icon-foreground.svg", "android-icon-foreground.png", 1024),
    ("android-icon-background.svg", "android-icon-background.png", 1024),
    ("splash-icon.svg", "splash-icon.png", 1024),
    ("favicon.svg", "favicon.png", 196),
]
for src, out, size in JOBS:
    cairosvg.svg2png(url=str(ASSETS / "brand" / src), write_to=str(ASSETS / out), output_width=size, output_height=size)
    print("rendered", out, size)

# Monochrome themed icon: alpha only = silhouette minus the cut-out details.
def _alpha(name: str) -> Image.Image:
    png = cairosvg.svg2png(url=str(ASSETS / "brand" / name), output_width=1024, output_height=1024)
    return Image.open(io.BytesIO(png)).convert("RGBA").getchannel("A")


alpha = ImageChops.subtract(_alpha("_mono-keep.svg"), _alpha("_mono-cut.svg"))
mono = Image.new("RGBA", (1024, 1024), (255, 255, 255, 0))
mono.putalpha(alpha)
mono.save(ASSETS / "android-icon-monochrome.png")
print("rendered android-icon-monochrome.png 1024")
