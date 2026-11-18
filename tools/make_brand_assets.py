"""Crop the two supplied illustrations into square brand avatars.

Source files live in the user's local reference folder (not committed):
  除了沃雅妮莎之外/小王子.png          (night, black cat at the bar)
  除了沃雅妮莎之外/彩特琳德-卡牌.png    (day, Zeitlind card)

The outputs are small square crops used by the titlebar medallion and the
custom whisper avatar picker.  The raw source folder remains ignored by Git.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "除了沃雅妮莎之外"
OUT = ROOT / "assets" / "images"
AVATARS = ROOT / "assets" / "avatars"
OUT.mkdir(parents=True, exist_ok=True)
AVATARS.mkdir(parents=True, exist_ok=True)


def save_crop(source: Path, box: tuple[int, int, int, int], name: str, *, lift: float = 1.0) -> None:
    im = Image.open(source).convert("RGB")
    crop = im.crop(box)
    if lift != 1.0:
        crop = ImageEnhance.Brightness(crop).enhance(lift)
        crop = ImageEnhance.Contrast(crop).enhance(1.06)
        crop = ImageEnhance.Color(crop).enhance(1.08)
    # A square crop; the titlebar/Avatar adds the gold ring at runtime.
    square = ImageOps.fit(crop, (512, 512), method=Image.LANCZOS, centering=(0.5, 0.42))
    square.save(OUT / name, quality=94, optimize=True)
    square.save(AVATARS / name, quality=94, optimize=True)
    print("wrote", OUT / name, square.size)


if __name__ == "__main__":
    # Night: cat and the warm tavern backdrop.  The original is very dark, so
    # lift the shadows and crop closer to the cat for a legible 42px medallion.
    save_crop(SRC / "小王子.png", (278, 74, 434, 286), "brand_night.png", lift=1.42)
    # Day: Zeitlind's face and upper body from the supplied card.
    save_crop(SRC / "彩特琳德-卡牌.png", (0, 25, 225, 250), "brand_day.png")
