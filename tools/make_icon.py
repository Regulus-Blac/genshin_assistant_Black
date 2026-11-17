"""Create the '小王子' black-cat icon for Black.

The icon is intentionally drawn rather than cut from an official asset: 小王子
is the black cat of Cat's Tail in Genshin, and a custom at-a-glance icon scales
better than a crop from a screenshot.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ASSETS / "images"

S = 1024
GOLD = (219, 188, 125, 255)
GOLD_LIGHT = (246, 226, 180, 255)
GOLD_DARK = (137, 111, 63, 255)
TEAL = (105, 210, 203, 255)
CREAM = (246, 236, 215, 255)
INK = (6, 9, 13, 255)
CAT = (9, 14, 20, 255)
CAT_LIGHT = (25, 39, 49, 255)
ROSE = (181, 112, 113, 255)


def radial_background() -> Image.Image:
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx, cy = S * 0.50, S * 0.48
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (S * 0.5)
    arr = np.zeros((S, S, 4), dtype=np.float32)
    # midnight indigo, a cool teal lower glow and warm top edge
    arr[..., 0] = 10 + 14 * np.clip(1 - d, 0, 1) ** 1.4
    arr[..., 1] = 18 + 38 * np.clip(1 - d, 0, 1) ** 1.4
    arr[..., 2] = 30 + 44 * np.clip(1 - d, 0, 1) ** 1.2
    teal_glow = np.clip(1 - np.sqrt((xx - S * 0.30) ** 2 + (yy - S * 0.78) ** 2) / (S * 0.45), 0, 1) ** 2
    arr[..., 1] += teal_glow * 22
    arr[..., 2] += teal_glow * 28
    warm = np.clip(1 - np.sqrt((xx - S * 0.78) ** 2 + (yy - S * 0.18) ** 2) / (S * 0.45), 0, 1) ** 2
    arr[..., 0] += warm * 26
    arr[..., 1] += warm * 14
    arr[..., 3] = 255
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((34, 34, S - 34, S - 34), fill=255)
    im.putalpha(mask)
    return im


def main() -> None:
    icon = radial_background()
    d = ImageDraw.Draw(icon, "RGBA")
    cx = cy = S // 2

    # night sky: moon and constellations, kept away from the face
    d.ellipse((700, 105, 885, 290), fill=(245, 231, 201, 25), outline=(245, 231, 201, 70), width=3)
    d.ellipse((748, 140, 850, 242), fill=(245, 231, 201, 18))
    for x, y, r, a in (
        (168, 198, 3, 180), (240, 142, 2, 120), (300, 248, 2, 110),
        (820, 420, 2, 140), (160, 560, 2, 80), (870, 610, 3, 110),
    ):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(242, 226, 185, a))

    # outer ornament rings
    d.ellipse((34, 34, S - 34, S - 34), outline=(217, 188, 125, 210), width=7)
    d.ellipse((55, 55, S - 55, S - 55), outline=(240, 219, 170, 90), width=2)
    for ang in range(0, 360, 90):
        a = math.radians(ang - 90)
        x = cx + math.cos(a) * 479
        y = cy + math.sin(a) * 479
        d.polygon([(x, y - 22), (x + 14, y), (x, y + 22), (x - 14, y)], fill=GOLD_LIGHT)
        d.ellipse((x - 4, y - 4, x + 4, y + 4), fill=TEAL)

    # soft cat shadow
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.ellipse((250, 268, 774, 862), fill=(0, 0, 0, 165))
    icon.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(34)))

    # ears
    left_ear = [(268, 430), (238, 190), (455, 330)]
    right_ear = [(756, 430), (786, 190), (569, 330)]
    d.polygon(left_ear, fill=CAT)
    d.polygon(right_ear, fill=CAT)
    d.polygon([(286, 400), (270, 255), (410, 340)], fill=(43, 30, 35, 255))
    d.polygon([(738, 400), (754, 255), (614, 340)], fill=(43, 30, 35, 255))
    d.line([(281, 409), (258, 228), (430, 334)], fill=(81, 105, 109, 140), width=3)
    d.line([(743, 409), (766, 228), (594, 334)], fill=(81, 105, 109, 140), width=3)

    # head
    d.ellipse((244, 300, 780, 790), fill=CAT)
    d.arc((250, 306, 774, 784), 196, 344, fill=(55, 83, 86, 150), width=4)

    # hair tufts / forehead fur
    d.polygon([(500, 350), (512, 300), (530, 352)], fill=CAT_LIGHT)
    d.polygon([(466, 360), (478, 320), (493, 364)], fill=CAT_LIGHT)
    d.polygon([(554, 360), (542, 320), (527, 364)], fill=CAT_LIGHT)

    # crown, slightly tilted to the left
    crown = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(crown, "RGBA")
    band_y = 372
    points = [(366, band_y), (400, 230), (488, 314), (574, 214), (654, 330), (700, 380), (660, 420), (380, 420)]
    cd.polygon(points, fill=(193, 153, 82, 255), outline=GOLD_LIGHT)
    cd.rectangle((372, 388, 674, 432), fill=(188, 148, 78, 255), outline=GOLD_LIGHT, width=4)
    cd.line((388, 404, 660, 414), fill=(248, 228, 182, 180), width=3)
    for x, y, r, color in (
        (400, 258, 18, TEAL), (574, 238, 22, TEAL), (662, 366, 16, (195, 92, 90, 255)),
        (512, 401, 31, TEAL),
    ):
        cd.ellipse((x - r, y - r, x + r, y + r), fill=(40, 60, 62, 255), outline=GOLD_LIGHT, width=4)
        cd.ellipse((x - r * 0.55, y - r * 0.55, x + r * 0.55, y + r * 0.55), fill=color)
        cd.ellipse((x - r * 0.22, y - r * 0.28, x + r * 0.08, y + r * 0.02), fill=(255, 250, 230, 210))
    # tiny crown cross/star
    cd.polygon([(512, 342), (524, 360), (512, 378), (500, 360)], fill=(80, 190, 190, 255))
    crown = crown.rotate(-7, resample=Image.BICUBIC, center=(512, 350))
    icon.alpha_composite(crown)

    # forehead star
    def star(center, r, color):
        x, y = center
        d.polygon(
            [(x, y - r), (x + r * 0.28, y - r * 0.28), (x + r, y),
             (x + r * 0.28, y + r * 0.28), (x, y + r), (x - r * 0.28, y + r * 0.28),
             (x - r, y), (x - r * 0.28, y - r * 0.28)],
            fill=color,
        )

    star((512, 490), 31, (234, 210, 150, 255))

    # eyes
    for ex in (414, 610):
        d.polygon([(ex - 83, 548), (ex, 508), (ex + 83, 548), (ex, 590)], fill=(231, 193, 107, 255))
        d.polygon([(ex - 55, 548), (ex, 526), (ex + 55, 548), (ex, 577)], fill=(40, 29, 13, 255))
        d.ellipse((ex - 24, 533, ex + 24, 561), fill=(252, 239, 199, 220))
        d.ellipse((ex - 14, 528, ex + 5, 550), fill=(255, 253, 235, 230))
        d.line([(ex - 93, 542), (ex - 57, 528)], fill=(245, 218, 158, 120), width=3)

    # nose and smile
    d.polygon([(498, 620), (526, 620), (512, 642)], fill=(205, 161, 101, 255))
    d.arc((461, 630, 563, 696), 18, 162, fill=(168, 126, 86, 210), width=5)
    # whiskers
    for y0, y1, xoff in ((602, 586, -1), (618, 611, -1), (602, 586, 1), (618, 611, 1)):
        start = (335 if xoff < 0 else 689, y0)
        end = (222 if xoff < 0 else 802, y1)
        d.line((start[0], start[1], end[0], end[1]), fill=(241, 232, 214, 115), width=3)

    # collar with a Vision-like gem
    d.arc((328, 720, 696, 900), 200, 340, fill=(217, 188, 125, 240), width=13)
    d.arc((335, 726, 689, 890), 205, 335, fill=(123, 100, 61, 210), width=4)
    gem = [(512, 765), (556, 808), (512, 858), (468, 808)]
    d.polygon(gem, fill=(187, 153, 94, 255), outline=GOLD_LIGHT)
    d.polygon([(512, 785), (540, 809), (512, 836), (484, 809)], fill=(74, 190, 186, 255), outline=(225, 247, 238, 220))

    # small paw-print constellation at lower right
    for x, y, r in ((780, 780, 6), (804, 752, 4), (820, 782, 4), (786, 812, 4)):
        d.ellipse((x - r, y - r, x + r, y + r), fill=(230, 206, 152, 120))

    # final subtle sparkle
    rng = np.random.default_rng(31)
    for _ in range(44):
        x = rng.uniform(120, 904)
        y = rng.uniform(110, 900)
        if (x - 512) ** 2 + (y - 520) ** 2 < 310 ** 2:
            continue
        r = rng.uniform(1.0, 2.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(240, 220, 170, int(rng.uniform(35, 120))))

    icon = icon.filter(ImageFilter.GaussianBlur(0.25))
    out = icon.resize((256, 256), Image.LANCZOS)
    out.save(IMAGES / "app_icon.png", optimize=True)
    out.save(ASSETS / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    # larger preview for docs
    icon.resize((512, 512), Image.LANCZOS).save(ROOT / "docs" / "icon_512.png", optimize=True)
    print("wrote", IMAGES / "app_icon.png", (IMAGES / "app_icon.png").stat().st_size)


if __name__ == "__main__":
    main()
