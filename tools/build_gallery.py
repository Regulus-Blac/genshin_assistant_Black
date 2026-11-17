"""Build the expanded, stage-ready character gallery.

Sources
-------
* Character metadata and Chinese names: Project Amber (gi.yatta.moe) public API.
* Official "wish" and "splash" artwork for 34 characters: ScobbleQ/HoYo-Assets
  on GitHub (official art mirror), fetched through jsDelivr.
* Skirk fallback: Enka Network's public UI asset mirror.
* Vodyanitsa: four illustrations supplied in the local workspace.

All output is composited onto a dark Genshin-style backdrop so the stage can
use fixed, high-resolution JPGs that never need to move or resize the art at
runtime. Sources are credited in assets/gallery.json.
"""
from __future__ import annotations

import io
import json
import math
import random
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black.paths import ASSETS, IMAGES  # noqa: E402

OUT = IMAGES / "gallery"
THUMBS = OUT / "thumbs"
OUT.mkdir(parents=True, exist_ok=True)
THUMBS.mkdir(parents=True, exist_ok=True)
CACHE = ROOT / "build" / "gallery_src"
CACHE.mkdir(parents=True, exist_ok=True)

H = {"User-Agent": "BlackAssistant/1.0 (local personal use)"}
W, H_OUT = 800, 1600
ELEMENT = {
    "Water": ("hydro", "#72cfe4"),
    "Fire": ("pyro", "#ec9b7b"),
    "Ice": ("cryo", "#a9dfe8"),
    "Electric": ("electro", "#bda0e8"),
    "Wind": ("anemo", "#82d6c6"),
    "Rock": ("geo", "#e0bd78"),
    "Grass": ("dendro", "#96cc8e"),
    "None": ("default", "#d9bc7d"),
}
# A curated roster: popular characters across every region, with both the tall
# wish illustration and the wide splash illustration where available.
ROSTER = [
    ("Furina", "furina", "水之国度的大明星"),
    ("Neuvillette", "neuvillette", "谕告的潮音"),
    ("Arlecchino", "arlecchino", "壁炉之家的父亲"),
    ("Navia", "navia", "刺玫会会长"),
    ("Clorinde", "clorinde", "枫丹的决斗代理人"),
    ("Wriothesley", "wriothesley", "梅洛彼得堡公爵"),
    ("Sigewinne", "sigewinne", "梅洛彼得堡护士长"),
    ("Chiori", "chiori", "千织屋店主"),
    ("Xianyun", "xianyun", "尘外身闲"),
    ("Hu Tao", "hutao", "往生堂第七十七代堂主"),
    ("Zhongli", "zhongli", "往生堂客卿"),
    ("Xiao", "xiao", "护法夜叉"),
    ("Ganyu", "ganyu", "月海亭秘书"),
    ("Shenhe", "shenhe", "孤辰茕怀"),
    ("Yelan", "yelan", "兰生幽谷"),
    ("Keqing", "keqing", "玉衡星"),
    ("Nahida", "nahida", "小吉祥草王"),
    ("Nilou", "nilou", "祖拜尔剧场的舞者"),
    ("Wanderer", "wanderer", "久世浮倾"),
    ("Cyno", "cyno", "大风纪官"),
    ("Tighnari", "tighnari", "巡林官"),
    ("Dehya", "dehya", "炽鬃之狮"),
    ("Raiden Shogun", "raiden", "一心净土"),
    ("Yae Miko", "yae", "鸣神大社宫司"),
    ("Kaedehara Kazuha", "kazuha", "红叶逐荒波"),
    ("Kamisato Ayaka", "ayaka", "白鹭霜华"),
    ("Yoimiya", "yoimiya", "夏祭的女王"),
    ("Sangonomiya Kokomi", "kokomi", "现人神巫女"),
    ("Venti", "venti", "风色诗人"),
    ("Klee", "klee", "火花骑士"),
    ("Mona", "mona", "星天水镜"),
    ("Eula", "eula", "浪沫的旋舞"),
    ("Tartaglia", "tartaglia", "愚人众执行官「公子」"),
    ("Albedo", "albedo", "白垩之子"),
]

VODY = {
    "id": "vodyanitsa",
    "name": "沃雅妮莎",
    "title": "潮声中的歌者",
    "element": "hydro",
    "color": "#7fd3d1",
    "looks": [
        {"id": "snow", "label": "雪窗", "art": "art_snow.jpg", "thumb": "gallery/thumbs/vody_snow.jpg"},
        {"id": "wisteria", "label": "紫藤", "art": "art_wisteria.jpg", "thumb": "gallery/thumbs/vody_wisteria.jpg"},
        {"id": "picnic", "label": "野餐", "art": "art_picnic.jpg", "thumb": "gallery/thumbs/vody_picnic.jpg"},
        {"id": "tea", "label": "茶会", "art": "art_tea.jpg", "thumb": "gallery/thumbs/vody_tea.jpg"},
    ],
    "default_look": "snow",
    "source": "workspace / user-supplied illustrations",
}


def fetch_yatta() -> dict[str, dict]:
    r = requests.get(
        "https://gi.yatta.moe/api/v2/chs/avatar",
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gi.yatta.moe/"},
        timeout=45,
    )
    r.raise_for_status()
    items = r.json()["data"]["items"]
    by_route = {}
    for cid, item in items.items():
        if item.get("route"):
            by_route[item["route"]] = {**item, "_cid": str(cid)}
    return by_route


def download(url: str, cache_name: str) -> bytes:
    path = CACHE / cache_name
    if path.exists() and path.stat().st_size > 5000:
        return path.read_bytes()
    last = None
    for attempt in range(3):
        try:
            r = requests.get(url, headers=H, timeout=60)
            r.raise_for_status()
            if len(r.content) < 5000:
                raise RuntimeError("too small")
            path.write_bytes(r.content)
            return r.content
        except Exception as e:
            last = e
            time.sleep(1.2 + attempt)
    raise RuntimeError(f"download failed {url}: {last}")


def gradient_canvas(accent: str, seed: int) -> Image.Image:
    top = np.array([6, 12, 20], dtype=np.float32)
    accent_rgb = np.array([int(accent[1:3], 16), int(accent[3:5], 16), int(accent[5:7], 16)], dtype=np.float32)
    bottom = top * 0.35 + accent_rgb * 0.20
    y = np.linspace(0, 1, H_OUT, dtype=np.float32)[:, None]
    rows = top[None, :] * (1 - y) + bottom[None, :] * y
    arr = np.repeat(rows[:, None, :], W, axis=1)
    # soft central bloom
    yy, xx = np.mgrid[0:H_OUT, 0:W].astype(np.float32)
    dist = np.sqrt(((xx - W * 0.5) / (W * 0.75)) ** 2 + ((yy - H_OUT * 0.33) / (H_OUT * 0.5)) ** 2)
    glow = np.clip(1 - dist, 0, 1) ** 2
    arr = arr + glow[..., None] * accent_rgb * 0.30
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGB").convert("RGBA")
    d = ImageDraw.Draw(im, "RGBA")
    # large moon and simple astrolabe rings
    d.ellipse((W * 0.70, 110, W * 0.70 + 150, 260), fill=(245, 231, 198, 20), outline=(245, 231, 198, 55), width=2)
    d.ellipse((W * 0.70 + 60, 170, W * 0.70 + 90, 200), fill=(246, 235, 211, 20))
    for radius, alpha in ((330, 35), (390, 18)):
        d.ellipse(
            (W / 2 - radius, H_OUT * 0.42 - radius, W / 2 + radius, H_OUT * 0.42 + radius),
            outline=(217, 188, 125, alpha),
            width=1,
        )
    # spray of stars
    rng = random.Random(seed)
    for _ in range(65):
        x = rng.uniform(20, W - 20)
        y = rng.uniform(40, H_OUT - 260)
        r = rng.uniform(1.0, 3.2)
        alpha = rng.randint(30, 160)
        color = (240, 220, 170, alpha) if rng.random() < 0.65 else (140, 225, 220, alpha)
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)
    # low mist
    for y0, alpha, h in ((1080, 18, 44), (1200, 13, 58), (1320, 10, 74)):
        d.ellipse((-100, y0, W + 100, y0 + h), fill=(200, 220, 220, alpha))
    return im


def edge_fade(im: Image.Image, left: int = 24, right: int = 24) -> Image.Image:
    if im.mode != "RGBA":
        return im
    alpha = np.array(im.getchannel("A"), dtype=np.float32) / 255.0
    h, w = alpha.shape
    x = np.arange(w, dtype=np.float32)
    y = np.arange(h, dtype=np.float32)
    fx = np.clip(np.minimum(x, w - 1 - x) / max(1, left), 0, 1) ** 0.8
    fy = np.clip(np.minimum(y, h - 1 - y) / max(1, right), 0, 1) ** 0.8
    alpha *= np.minimum(fx[None, :], fy[:, None])
    im = im.copy()
    im.putalpha(Image.fromarray((alpha * 255).astype(np.uint8), "L"))
    return im


def compose(source_bytes: bytes, kind: str, accent: str, seed: int) -> Image.Image:
    src = Image.open(io.BytesIO(source_bytes)).convert("RGBA")
    canvas = gradient_canvas(accent, seed)

    # A blurred echo of the source gives the backdrop some of its own colour.
    cover_scale = max(W / src.width, H_OUT / src.height)
    echo = src.resize((max(1, round(src.width * cover_scale)), max(1, round(src.height * cover_scale))), Image.LANCZOS)
    ex = max(0, (echo.width - W) // 2)
    ey = max(0, (echo.height - H_OUT) // 2)
    echo = echo.crop((ex, ey, ex + W, ey + H_OUT))
    echo = echo.filter(ImageFilter.GaussianBlur(22))
    dark = Image.new("RGBA", (W, H_OUT), (4, 9, 14, 145))
    echo.alpha_composite(dark)
    canvas.alpha_composite(echo)

    # Character artwork: tall wish art is shown full-body; wide splash art is
    # cover-cropped around the centre.
    if kind == "wish" or (src.width / src.height) < 0.70:
        art_h = 1500
        art_w = round(src.width * art_h / src.height)
        if art_w > 760:
            art_w = 760
            art_h = round(src.height * art_w / src.width)
        art = src.resize((art_w, art_h), Image.LANCZOS)
        art = edge_fade(art, 20, 20)
        x = (W - art_w) // 2
        y = max(30, H_OUT - art_h - 38)
        canvas.alpha_composite(art, (x, y))
    else:
        scale = max(W / src.width, H_OUT / src.height)
        sw, sh = max(1, round(src.width * scale)), max(1, round(src.height * scale))
        art = src.resize((sw, sh), Image.LANCZOS)
        x = max(0, (sw - W) // 2)
        y = max(0, (sh - H_OUT) // 2)
        art = art.crop((x, y, x + W, y + H_OUT))
        art = edge_fade(art, 8, 8)
        canvas.alpha_composite(art)

    # vignette and cinematic edges
    vignette = Image.new("RGBA", (W, H_OUT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette, "RGBA")
    for i in range(8):
        a = 8 + i * 7
        vd.rectangle((i * 5, i * 8, W - i * 5, H_OUT - i * 8), outline=(3, 7, 11, a), width=5)
    canvas.alpha_composite(vignette.filter(ImageFilter.GaussianBlur(18)))
    top = Image.new("RGBA", (W, 260), (4, 8, 13, 0))
    td = ImageDraw.Draw(top, "RGBA")
    for y in range(260):
        td.line((0, y, W, y), fill=(4, 8, 13, int(190 * (1 - y / 260) ** 1.4)))
    canvas.alpha_composite(top, (0, 0))
    bottom = Image.new("RGBA", (W, 340), (4, 8, 13, 0))
    bd = ImageDraw.Draw(bottom, "RGBA")
    for y in range(340):
        bd.line((0, y, W, y), fill=(4, 8, 13, int(235 * (y / 340) ** 1.2)))
    canvas.alpha_composite(bottom, (0, H_OUT - 340))
    return canvas.convert("RGB")


def make_thumb(im: Image.Image, focus_y: float = 0.12) -> Image.Image:
    target_w, target_h = 600, 800
    scale = max(target_w / im.width, target_h / im.height)
    t = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    x = max(0, (t.width - target_w) // 2)
    y = max(0, int((t.height - target_h) * focus_y))
    t = t.crop((x, y, x + target_w, y + target_h))
    return t.resize((300, 400), Image.LANCZOS)


def build() -> int:
    print("fetch yatta")
    by_route = fetch_yatta()
    characters = [VODY]
    # Vodyanitsa thumbs from the local paintings
    for look in VODY["looks"]:
        im = Image.open(IMAGES / look["art"]).convert("RGB")
        make_thumb(im, 0.03).save(IMAGES / look["thumb"], quality=88, optimize=True)

    jobs = []
    for route, cid, title in ROSTER:
        y = by_route.get(route)
        if not y:
            print("skip missing metadata", route)
            continue
        for kind in ("wish", "splash"):
            url = f"https://cdn.jsdelivr.net/gh/ScobbleQ/HoYo-Assets@main/genshin/{kind}/{y['_cid']}.png"
            jobs.append((route, cid, title, y, kind, url))
    # ensure Skirk gets Enka fallback
    downloaded: dict[tuple[str, str], bytes] = {}

    def dl(job):
        route, cid, title, y, kind, url = job
        name = f"{cid}_{kind}.png"
        try:
            return (cid, kind, download(url, name), None)
        except Exception as e:
            return (cid, kind, None, str(e))

    with ThreadPoolExecutor(max_workers=6) as ex:
        futs = [ex.submit(dl, j) for j in jobs]
        for f in as_completed(futs):
            cid, kind, data, err = f.result()
            if data:
                downloaded[(cid, kind)] = data
                print("ok", cid, kind, len(data) // 1024, "KB")
            else:
                print("miss", cid, kind, err)

    # Enka fallback for Skirk
    skirk = next((j for j in jobs if j[1] == "skirk"), None)
    if skirk and not downloaded.get(("skirk", "wish")):
        try:
            y = by_route["Skirk"]
            icon = y["icon"].replace("UI_AvatarIcon_", "")
            data = download(f"https://enka.network/ui/UI_Gacha_AvatarImg_{icon}.png", f"skirk_enka.png")
            downloaded[("skirk", "wish")] = data
            print("ok skirk enka", len(data) // 1024, "KB")
        except Exception as e:
            print("skirk fallback failed", e)

    for route, cid, title in ROSTER:
        y = by_route.get(route)
        if not y:
            continue
        element_en = y.get("element", "None")
        element, color = ELEMENT.get(element_en, ELEMENT["None"])
        looks = []
        # Splash art is high-resolution and fills the stage beautifully, so it
        # is the default look.  The tall wish render is the alternate full-body
        # studio look.
        for kind, label in (("splash", "全景"), ("wish", "全身")):
            data = downloaded.get((cid, kind))
            if not data:
                continue
            try:
                im = compose(data, kind, color, seed=sum(ord(c) for c in cid) + (0 if kind == "wish" else 7))
                art_name = f"gallery/{cid}_{kind}.jpg"
                thumb_name = f"gallery/thumbs/{cid}_{kind}.jpg"
                im.save(IMAGES / art_name, quality=92, optimize=True)
                make_thumb(im, 0.12).save(IMAGES / thumb_name, quality=88, optimize=True)
                if cid == "skirk" and not looks:
                    label = "官方"
                looks.append({"id": kind, "label": label, "art": art_name, "thumb": thumb_name})
                print("page", cid, kind, (IMAGES / art_name).stat().st_size // 1024, "KB")
            except Exception as e:
                print("compose failed", cid, kind, e)
        if not looks:
            print("NO LOOKS", route)
            continue
        characters.append(
            {
                "id": cid,
                "name": y.get("name") or route,
                "title": title,
                "element": element,
                "color": color,
                "looks": looks,
                "default_look": looks[0]["id"],
                "source": "HoYo-Assets / Enka Network",
            }
        )

    manifest = {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sources": {
            "metadata": "https://gi.yatta.moe/api/v2/chs/avatar",
            "official_art": "https://github.com/ScobbleQ/HoYo-Assets",
            "fallback_art": "https://enka.network/",
            "local_art": "Vodyanitsa_image/",
        },
        "characters": characters,
    }
    (ASSETS / "gallery.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("characters", len(characters), "looks", sum(len(c["looks"]) for c in characters))
    # contact sheet
    sheet_cols = 6
    tw, th = 180, 240
    rows = (len(characters) + sheet_cols - 1) // sheet_cols
    sheet = Image.new("RGB", (sheet_cols * tw, rows * (th + 24)), (8, 12, 18))
    sd = ImageDraw.Draw(sheet)
    for i, c in enumerate(characters):
        look = c["looks"][0]
        im = Image.open(IMAGES / look["thumb"]).convert("RGB").resize((tw, th), Image.LANCZOS)
        x = (i % sheet_cols) * tw
        y = (i // sheet_cols) * (th + 24)
        sheet.paste(im, (x, y + 24))
        sd.text((x + 4, y + 6), f"{i+1}. {c['name']}", fill=(235, 226, 205))
    sheet.save(ROOT / "build" / "gallery_contact.jpg", quality=88)
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
