"""Build the round application icon from the supplied 小王子 illustration.

The titlebar switches between 彩特琳德 (day) and 小王子 (night), while the
OS/app icon stays as the night cat so the taskbar remains recognizable.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "assets" / "images"
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"


def main() -> None:
    src = Image.open(IMAGES / "brand_night.png").convert("RGB")
    src = src.resize((512, 512), Image.LANCZOS)
    canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    # Deep warm rim behind the circular crop.
    d = ImageDraw.Draw(canvas, "RGBA")
    d.ellipse((8, 8, 504, 504), fill=(10, 17, 26, 255))
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).ellipse((18, 18, 494, 494), fill=255)
    canvas.paste(src, (0, 0), mask)
    d = ImageDraw.Draw(canvas, "RGBA")
    # gold double ring
    d.ellipse((14, 14, 498, 498), outline=(217, 188, 125, 235), width=7)
    d.ellipse((30, 30, 482, 482), outline=(247, 231, 196, 105), width=2)
    for x, y, r in ((256, 14, 5), (256, 498, 5), (14, 256, 5), (498, 256, 5)):
        d.polygon([(x, y - r), (x + r * 0.55, y - r * 0.25), (x + r, y),
                   (x + r * 0.55, y + r * 0.25), (x, y + r),
                   (x - r * 0.55, y + r * 0.25), (x - r, y),
                   (x - r * 0.55, y - r * 0.25)], fill=(243, 221, 170, 255))
    icon = canvas

    icon.save(IMAGES / "app_icon.png", optimize=True)
    icon.save(ASSETS / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    DOCS.mkdir(exist_ok=True)
    icon.resize((512, 512), Image.LANCZOS).save(DOCS / "icon_512.png", optimize=True)
    print("wrote", IMAGES / "app_icon.png", ASSETS / "app.ico", DOCS / "icon_512.png")


if __name__ == "__main__":
    main()
