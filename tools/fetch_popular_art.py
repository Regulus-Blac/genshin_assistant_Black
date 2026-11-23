"""Collect popular fan art (pixiv) as optional extra 立绘.

The repository only ships the hand-picked official-art gallery.  This tool lets
you pull the most-liked pixiv illustrations for a character into
``data/art_extra/<character id>/`` (git-ignored) and registers them in
``data/art_extra/manifest.json`` so the character picker shows them as extra
looks.

Notes
-----
* Only public pixiv search results are used (no login required).
* Every entry keeps its title, author and pixiv link in the manifest, please
  respect the artists: personal use only, no redistribution.
* 米游社 (miHoYo's community) needs a signed, logged-in API; this tool does not
  support it, use ``--source local`` style copying by hand if you saved images.

Examples
--------
    python tools/fetch_popular_art.py --list
    python tools/fetch_popular_art.py --character jean --limit 6
    python tools/fetch_popular_art.py --character 琴 --query "琴 原神" --limit 6
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402
from PIL import Image  # noqa: E402

from black.characters import all_characters, art_path, get_character  # noqa: E402
from black.paths import DATA_DIR  # noqa: E402

EXTRA_DIR = DATA_DIR / "art_extra"
MANIFEST = EXTRA_DIR / "manifest.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36",
    "Referer": "https://www.pixiv.net/",
}
API = "https://www.pixiv.net/ajax"


def read_manifest() -> dict:
    if not MANIFEST.exists():
        return {}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_manifest(data: dict) -> None:
    EXTRA_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_character(value: str) -> dict:
    value = str(value or "").strip()
    chars = all_characters()
    for meta in chars:
        if meta["id"] == value:
            return meta
    for meta in chars:
        if str(meta.get("name")) == value:
            return meta
    for meta in chars:
        if value and value in str(meta.get("name")) or value and value in str(meta.get("title", "")):
            return meta
    raise SystemExit(f"找不到角色：{value}（用 --list 查看可用的 id）")


def pixiv_search(word: str, pages: int = 3) -> list[dict]:
    out: list[dict] = []
    for page in range(1, pages + 1):
        url = f"{API}/search/artworks/{requests.utils.quote(word)}"
        params = {
            "word": word,
            "order": "popular_d",
            "mode": "all",
            "p": page,
            "s_mode": "s_tag",
            "type": "all",
            "lang": "zh",
        }
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        body = r.json().get("body", {})
        data = (body.get("illustManga") or {}).get("data") or []
        out.extend(item for item in data if isinstance(item, dict))
        if not data:
            break
        time.sleep(0.4)
    return out


def pick_candidates(items: list[dict], name: str, tag_hint: str, limit: int, name_tag: str = "") -> list[dict]:
    name_tags = {name, f"{name}(原神)", f"{name}（原神）"}
    if name_tag:
        name_tags = {name_tag}
    picked = []
    seen = set()
    for item in items:
        iid = str(item.get("id") or "")
        if not iid or iid in seen:
            continue
        if int(item.get("illustType", 0) or 0) != 0:
            continue
        tags = [str(t) for t in (item.get("tags") or [])]
        joined = " ".join(tags)
        if tag_hint and tag_hint not in joined:
            continue
        # Requiring the *exact* character tag keeps "琴" (Jean) from matching
        # 鋼琴/小提琴 illustrations that merely mention a piano.
        tag_match = any(t.strip() in name_tags for t in tags)
        title_match = bool(name) and name in str(item.get("title", ""))
        if not tag_match and not title_match:
            continue
        seen.add(iid)
        picked.append(item)
        if len(picked) >= limit:
            break
    return picked


def fetch_detail(illust_id: str) -> dict | None:
    try:
        r = requests.get(f"{API}/illust/{illust_id}", headers=HEADERS, timeout=30)
        r.raise_for_status()
        body = r.json().get("body") or {}
        return body if isinstance(body, dict) else None
    except Exception as exc:
        print(f"  ! 详情失败 {illust_id}: {exc}")
        return None


def save_image(url: str, target: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=90)
        r.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.content)
        return True
    except Exception as exc:
        print(f"  ! 下载失败 {url}: {exc}")
        return False


def make_thumb(source: Path, target: Path, width: int = 300, height: int = 400) -> None:
    try:
        im = Image.open(source).convert("RGB")
        scale = max(width / im.width, height / im.height)
        resized = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.LANCZOS)
        x = max(0, (resized.width - width) // 2)
        y = max(0, (resized.height - height) // 2)
        resized.crop((x, y, x + width, y + height)).save(target, quality=88, optimize=True)
    except Exception as exc:
        print(f"  ! 缩略图失败 {source.name}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description="从 pixiv 收集人气同人图作为补充立绘（仅本地）")
    parser.add_argument("--list", action="store_true", help="列出可用的角色 id")
    parser.add_argument("--character", help="角色 id 或名字，例如 jean / 琴")
    parser.add_argument("--query", help="搜索词，默认「<名字> 原神」")
    parser.add_argument("--tag", default="原神", help="结果必须包含的标签，默认 原神")
    parser.add_argument("--name-tag", default="", help="精确角色标签，例如 ジン(原神)；默认用中文名")
    parser.add_argument("--limit", type=int, default=6, help="最多保存几张，默认 6")
    parser.add_argument("--min-bookmarks", type=int, default=0, help="最低收藏数（0 表示不过滤）")
    parser.add_argument("--replace", action="store_true", help="替换这个角色之前收集的 pixiv 图")
    args = parser.parse_args()

    if args.list:
        for meta in all_characters():
            print(f"{meta['id']:14s} {meta.get('name')}")
        return 0

    if not args.character:
        parser.print_help()
        return 1

    meta = resolve_character(args.character)
    cid = meta["id"]
    name = str(meta.get("name") or "")
    query = args.query or f"{name} 原神"
    print(f"[art] {name}（{cid}）· 搜索「{query}」")

    items = pixiv_search(query, pages=5)
    candidates = pick_candidates(items, name, args.tag, max(24, args.limit * 6), args.name_tag)
    print(f"[art] 候选 {len(candidates)} 张（共 {len(items)} 条结果）")
    if not candidates:
        print("[art] 没有合适的图，可以换一个 --query 或 --tag。")
        return 1

    manifest = read_manifest()
    if args.replace:
        manifest[cid] = [look for look in manifest.get(cid, []) if look.get("source") != "pixiv"]
    entries = list(manifest.get(cid, []))
    existing = {str(look.get("id")) for look in entries}
    folder = EXTRA_DIR / cid

    # Rank by real bookmark count: pixiv's "popular_d" order still mixes in
    # recent works, so fetch details for a wider pool and sort ourselves.
    ranked = []
    for item in candidates[:24]:
        detail = fetch_detail(str(item.get("id")))
        if not detail:
            continue
        bookmarks = int(detail.get("bookmarkCount") or 0)
        likes = int(detail.get("likeCount") or 0)
        if args.min_bookmarks and bookmarks < args.min_bookmarks:
            continue
        ranked.append((bookmarks, likes, item, detail))
        time.sleep(0.25)
    ranked.sort(key=lambda row: row[0], reverse=True)
    print("[art] 收藏数前几名：" + "、".join(f"{row[0]}" for row in ranked[:6]))
    saved = 0
    rank = 0
    for bookmarks, likes, item, detail in ranked:
        if saved >= args.limit:
            break
        iid = str(item.get("id"))
        urls = detail.get("urls") or {}
        url = str(urls.get("regular") or urls.get("original") or "")
        if not url:
            continue
        rank += 1
        stem = f"px{iid}"
        target = folder / f"{stem}.jpg"
        if not save_image(url, target):
            continue
        thumb = folder / f"{stem}_thumb.jpg"
        make_thumb(target, thumb)
        look_id = f"pixiv-{iid}"
        if look_id in existing:
            saved += 1
            continue
        entries.append(
            {
                "id": look_id,
                "label": f"人气 {rank}",
                "orientation": "portrait" if target.stat().st_size else "portrait",
                "art": str(target.resolve()),
                "thumb": str(thumb.resolve()),
                "source": "pixiv",
                "credit": f"{detail.get('title') or item.get('title')} / {detail.get('userName') or item.get('userName')} / "
                f"https://www.pixiv.net/artworks/{iid} · 收藏 {bookmarks} · 赞 {likes}",
            }
        )
        existing.add(look_id)
        saved += 1
        print(f"  + {stem}: {detail.get('title')}（收藏 {bookmarks}）")
        time.sleep(0.7)
    if not saved:
        print("[art] 没有保存任何图片。")
        return 1
    if entries:
        manifest[cid] = entries
    write_manifest(manifest)
    print(f"[art] 已保存 {saved} 张到 {folder}")
    print("[art] 提醒：同人图版权归原作者，仅供个人本地使用；清单里已记录作者与链接。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
