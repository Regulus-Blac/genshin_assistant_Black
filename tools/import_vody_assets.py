"""Import every supplied Vodyanitsa illustration into the stage gallery.

The source folder contains both portrait and landscape paintings.  Portrait
files become 800x1600 stage cards; landscape files become 1600x900 banner
art.  The generated assets are committed so the app works without the raw
workspace folder.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.build_gallery import IMAGES, compose, compose_wide, make_thumb  # noqa: E402

SRC = ROOT / "Vodyanitsa_image"
GALLERY = IMAGES / "gallery"
THUMBS = GALLERY / "thumbs"

# id, source filename, label
LOOKS = [
    ("window", "窗边练歌全身.jpg", "窗边"),
    ("qipao_full", "旗袍全身.jpg", "旗袍·全身"),
    ("qipao_half", "旗袍半身.jpg", "旗袍·半身"),
    ("qipao_fan", "旗袍团扇.jpg", "旗袍·团扇"),
    ("swim1", "泳装沙滩全身.jpg", "泳装·沙滩"),
    ("swim2", "泳装沙滩全身2.jpg", "泳装·沙滩 2"),
    ("swim_comic", "泳装漫画画风.jpg", "泳装·漫画"),
    ("snowpool", "雪糕水池全身.jpg", "雪糕水池"),
    ("mermaid_down", "水中人鱼倒立.jpg", "人鱼·倒影"),
    ("mermaid_sing", "水中人鱼歌唱.jpg", "人鱼·歌唱"),
    ("drink_half", "饮料半身.jpg", "饮料·半身"),
    ("drink_store", "饮料杂货店半身.jpg", "饮料·杂货店"),
    ("drink_beach", "饮料海滩半身.jpg", "饮料·海滩"),
    ("drink_grass", "饮料草地全身.jpg", "饮料·草地"),
    ("drink_bench", "饮料长椅半身.jpg", "饮料·长椅"),
]


def main() -> None:
    exists = [p for p in SRC.glob("*.jpg") if p.name in {x[1] for x in LOOKS}]
    if not exists:
        raise SystemExit(f"no Vodyanitsa files in {SRC}")
    looks = []
    for idx, (look_id, filename, label) in enumerate(LOOKS):
        source = SRC / filename
        if not source.exists():
            print("skip", filename)
            continue
        data = source.read_bytes()
        src = Image.open(io.BytesIO(data))
        is_wide = src.width / max(1, src.height) > 1.05
        if is_wide:
            im = compose_wide(data, "#7fd3d1", seed=100 + idx, focus_y=0.24)
            art_name = f"gallery/vody_{look_id}_wide.jpg"
        else:
            im = compose(data, "cover", "#7fd3d1", seed=100 + idx)
            art_name = f"gallery/vody_{look_id}_portrait.jpg"
        thumb_name = f"gallery/thumbs/vody_{look_id}.jpg"
        (IMAGES / art_name).parent.mkdir(parents=True, exist_ok=True)
        im.save(IMAGES / art_name, quality=92, optimize=True)
        make_thumb(im, 0.08).save(IMAGES / thumb_name, quality=88, optimize=True)
        looks.append({
            "id": look_id,
            "label": label,
            "orientation": "landscape" if is_wide else "portrait",
            "art": art_name,
            "thumb": thumb_name,
        })
        print("wrote", look_id, "landscape" if is_wide else "portrait", im.size)

    manifest_path = ROOT / "assets" / "gallery.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for char in manifest["characters"]:
        if char.get("id") == "vodyanitsa":
            char["looks"] = looks
            char["default_look"] = "window"
            char["source"] = "workspace / user-supplied illustrations"
            break
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("vody looks", len(looks))
    for look in looks:
        print(" ", look["id"], look["label"], look["orientation"])


if __name__ == "__main__":
    main()
