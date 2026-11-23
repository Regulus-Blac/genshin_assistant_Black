"""Fetch 20 more characters (official art + avatar icons) into the gallery.

Reuses the compositing helpers from ``tools/build_gallery.py`` so the new
entries look identical to the existing roster, but only touches the new
characters: existing artwork and manifest entries are left alone.

Sources
-------
* Metadata (Chinese names, element, avatar icon): Project Amber / gi.yatta.moe
* Stage art (wish + splash renders): ScobbleQ/HoYo-Assets via jsDelivr
* Square avatars: Enka Network UI asset mirror
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

import requests  # noqa: E402
from PIL import Image  # noqa: E402

import build_gallery as bg  # noqa: E402
from black.paths import ASSETS, AVATARS, IMAGES  # noqa: E402

MANIFEST = ASSETS / "gallery.json"

# (yatta route, gallery id, 中文称号)
NEW_ROSTER = [
    ("Jean", "jean", "蒲公英骑士"),
    ("Diluc", "diluc", "晨曦的暗面"),
    ("Amber", "amber", "飞行冠军"),
    ("Lisa", "lisa", "蔷薇魔女"),
    ("Kaeya", "kaeya", "寒风剑士"),
    ("Barbara", "barbara", "闪耀偶像"),
    ("Xiangling", "xiangling", "万民百味"),
    ("Beidou", "beidou", "无冕的龙王"),
    ("Ningguang", "ningguang", "掩月天权"),
    ("Noelle", "noelle", "未授勋之花"),
    ("Fischl", "fischl", "断罪皇女"),
    ("Bennett", "bennett", "命运试金石"),
    ("Chongyun", "chongyun", "雪融有踪"),
    ("Xingqiu", "xingqiu", "少年春衫薄"),
    ("Razor", "razor", "狼少年"),
    ("Diona", "diona", "猫尾特调"),
    ("Sucrose", "sucrose", "无害甜度"),
    ("Qiqi", "qiqi", "冻冻回魂夜"),
    ("Kamisato Ayato", "ayato", "磐祭叶守"),
    ("Yun Jin", "yunjin", "红毹婵娟"),
]


def fetch_avatar(icon: str, target: Path) -> bool:
    if target.exists() and target.stat().st_size > 2000:
        return True
    for base in ("https://enka.network/ui/", "https://gi.yatta.moe/assets/UI/"):
        try:
            r = requests.get(base + icon + ".png", headers={**bg.H, "Referer": "https://gi.yatta.moe/"}, timeout=45)
            r.raise_for_status()
            if len(r.content) < 2000:
                continue
            import io

            im = Image.open(io.BytesIO(r.content)).convert("RGBA")
            side = max(im.size)
            canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
            canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
            canvas = canvas.resize((256, 256), Image.LANCZOS)
            target.parent.mkdir(parents=True, exist_ok=True)
            canvas.save(target, optimize=True)
            return True
        except Exception as exc:  # pragma: no cover - network dependent
            print("avatar miss", icon, base, exc)
    return False


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    existing = {c["id"]: c for c in manifest["characters"]}
    by_route = bg.fetch_yatta()

    jobs = []
    for route, cid, title in NEW_ROSTER:
        if cid in existing:
            print("already present", cid)
            continue
        meta = by_route.get(route)
        if not meta:
            print("missing metadata", route)
            continue
        element, color = bg.ELEMENT.get(meta.get("element", "None"), bg.ELEMENT["None"])
        jobs.append((route, cid, title, meta, element, color))

    downloads = {}

    def fetch(job):
        route, cid, title, meta, element, color = job
        got = {}
        for kind in ("wish", "splash"):
            url = f"https://cdn.jsdelivr.net/gh/ScobbleQ/HoYo-Assets@main/genshin/{kind}/{meta['_cid']}.png"
            try:
                got[kind] = bg.download(url, f"{cid}_{kind}.png")
                print("ok", cid, kind, len(got[kind]) // 1024, "KB")
            except Exception as exc:
                print("miss", cid, kind, exc)
        return cid, got

    with ThreadPoolExecutor(max_workers=4) as pool:
        for cid, got in pool.map(fetch, jobs):
            downloads[cid] = got

    added = []
    for route, cid, title, meta, element, color in jobs:
        data = downloads.get(cid, {})
        if not data.get("wish") and not data.get("splash"):
            print("no art, skipped", cid)
            continue
        looks = []
        try:
            if data.get("splash"):
                im = bg.compose(data["splash"], "splash", color, seed=sum(ord(c) for c in cid))
                im.save(IMAGES / f"gallery/{cid}_splash.jpg", quality=90, optimize=True)
                bg.make_thumb(im, 0.12).save(IMAGES / f"gallery/thumbs/{cid}_splash.jpg", quality=86, optimize=True)
                looks.append({
                    "id": "splash",
                    "label": "全景",
                    "orientation": "portrait",
                    "art": f"gallery/{cid}_splash.jpg",
                    "thumb": f"gallery/thumbs/{cid}_splash.jpg",
                })
            if data.get("wish"):
                im = bg.compose(data["wish"], "wish", color, seed=sum(ord(c) for c in cid) + 7)
                im.save(IMAGES / f"gallery/{cid}_wish.jpg", quality=90, optimize=True)
                bg.make_thumb(im, 0.12).save(IMAGES / f"gallery/thumbs/{cid}_wish.jpg", quality=86, optimize=True)
                looks.append({
                    "id": "wish",
                    "label": "全身",
                    "orientation": "portrait",
                    "art": f"gallery/{cid}_wish.jpg",
                    "thumb": f"gallery/thumbs/{cid}_wish.jpg",
                })
            wide_source = data.get("splash") or data.get("wish")
            if wide_source:
                im = bg.compose_wide(wide_source, color, seed=sum(ord(c) for c in cid) + 19)
                im.save(IMAGES / f"gallery/{cid}_wide.jpg", quality=90, optimize=True)
                bg.make_thumb(im, 0.12).save(IMAGES / f"gallery/thumbs/{cid}_wide.jpg", quality=86, optimize=True)
                looks.append({
                    "id": "wide",
                    "label": "横屏",
                    "orientation": "landscape",
                    "art": f"gallery/{cid}_wide.jpg",
                    "thumb": f"gallery/thumbs/{cid}_wide.jpg",
                })
        except Exception as exc:
            print("compose failed", cid, exc)
        if not looks:
            continue
        icon = str(meta.get("icon") or "")
        avatar_ok = fetch_avatar(icon, AVATARS / f"{cid}.png") if icon else False
        print("avatar", cid, avatar_ok)
        entry = {
            "id": cid,
            "name": meta.get("name") or route,
            "title": title,
            "element": element,
            "color": color,
            "looks": looks,
            "default_look": looks[0]["id"],
            "source": "HoYo-Assets / Enka Network",
        }
        added.append(entry)

    if not added:
        print("nothing added")
        return 0
    manifest["characters"].extend(added)
    manifest["generated_at"] = datetime.now().isoformat(timespec="seconds")
    sources = manifest.setdefault("sources", {})
    sources.setdefault("official_art", "https://github.com/ScobbleQ/HoYo-Assets")
    sources.setdefault("avatars", "https://enka.network/")
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("added", len(added), "characters; now", len(manifest["characters"]),
          "looks", sum(len(c["looks"]) for c in manifest["characters"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
