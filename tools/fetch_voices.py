"""Download a small set of Chinese character voice lines into data/voice/.

Source: the public CSUSTers/mys-voice-genshin dataset (scraped from the official
HoYoLAB wiki) which lists each line's text and an official CDN mp3 URL.  Only a
handful of short lines per character are fetched.

The audio belongs to HoYoverse; files are written to ``data/voice/`` which is
git-ignored, so nothing is redistributed with the repository.  Use it for your
own local copy only.

Examples
--------
    python tools/fetch_voices.py --list
    python tools/fetch_voices.py --speaker 琴 --limit 8
    python tools/fetch_voices.py --all --limit 5
"""
from __future__ import annotations

import argparse
import csv
import html
import io
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from black import content  # noqa: E402
from black.paths import BUNDLED_VOICES  # noqa: E402
from black.voices import VoiceBank  # noqa: E402

RAW = "https://raw.githubusercontent.com/CSUSTers/mys-voice-genshin/main/res/csv/"
TREE = "https://github.com/CSUSTers/mys-voice-genshin/tree/main/res/csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
DEST = BUNDLED_VOICES
INDEX = DEST / "index.json"


def clean_text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def available_characters() -> list[str]:
    """Names that have a CSV in the dataset (decoded from the GitHub tree page)."""
    try:
        page = requests.get(TREE, headers=HEADERS, timeout=30).text
    except Exception:
        return []
    names = set()
    for raw in re.findall(r"([^/\"<>]+)\.csv", html.unescape(page)):
        try:
            names.add(requests.utils.unquote(raw).strip())
        except Exception:
            names.add(raw.strip())
    return sorted(n for n in names if n)


def fetch_csv(speaker: str) -> list[dict]:
    url = RAW + requests.utils.quote(speaker) + ".csv"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            return []
        rows = list(csv.DictReader(io.StringIO(r.text)))
    except Exception:
        return []
    out = []
    for row in rows:
        text = clean_text(row.get("text", ""))
        audio = str(row.get("audio", "")).strip()
        topic = clean_text(row.get("topic", ""))
        if not audio.endswith(".mp3"):
            continue
        if not (4 <= len(text) <= 48):
            continue
        out.append({"topic": topic, "text": text, "audio": audio})
    return out


def download(url: str, target: Path) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        if len(r.content) < 2000:
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.content)
        return True
    except Exception as exc:
        print(f"  ! {target.name}: {exc}")
        return False


def fetch_speaker(speaker: str, limit: int, index: dict) -> int:
    rows = fetch_csv(speaker)
    if not rows:
        print(f"[voice] {speaker}: 没有可用台词")
        return 0
    folder = DEST / speaker
    folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    entries = []
    seen = set()
    for row in rows:
        if saved >= limit:
            break
        if row["audio"] in seen:
            continue
        seen.add(row["audio"])
        name = f"line{saved + 1:02d}.mp3"
        target = folder / name
        if target.exists() and target.stat().st_size > 2000:
            saved += 1
            entries.append({"file": name, "topic": row["topic"], "text": row["text"], "source": row["audio"]})
            continue
        if download(row["audio"], target):
            saved += 1
            entries.append({"file": name, "topic": row["topic"], "text": row["text"], "source": row["audio"]})
            print(f"  + {speaker}/{name}: {row['topic']} · {row['text'][:24]}")
            time.sleep(0.25)
    if entries:
        index[speaker] = entries
    return saved


def main() -> int:
    global DEST, INDEX
    parser = argparse.ArgumentParser(description="下载少量中文角色语音到 data/voice/")
    parser.add_argument("--list", action="store_true", help="列出数据集里可用的角色")
    parser.add_argument("--speaker", help="角色名，例如 琴")
    parser.add_argument("--all", action="store_true", help="为所有已有悄悄话的角色下载")
    parser.add_argument("--limit", type=int, default=5, help="每个角色下载几条，默认 5")
    parser.add_argument("--dest", help="输出目录，默认写入 assets/audio/voices")
    args = parser.parse_args()

    if args.list:
        names = available_characters()
        personas = [s for s in content.SPEAKERS if s in names]
        print(f"数据集角色 {len(names)} 个；其中和悄悄话对得上的 {len(personas)} 个：")
        print("、".join(personas))
        return 0

    index: dict = {}
    if INDEX.exists():
        try:
            loaded = json.loads(INDEX.read_text(encoding="utf-8"))
            index = loaded if isinstance(loaded, dict) else {}
        except Exception:
            index = {}

    if args.dest:
        DEST = Path(args.dest).expanduser()
        INDEX = DEST / "index.json"

    if args.all:
        names = set(available_characters())
        targets = [s for s in content.SPEAKERS if s in names]
        if not targets:
            print("[voice] 没有匹配到角色，先跑 --list 看看。")
            return 1
        total = 0
        for speaker in targets:
            count = fetch_speaker(speaker, max(1, args.limit), index)
            total += count
            print(f"[voice] {speaker}: {count} 条")
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[voice] 共 {total} 条，目录 {DEST}")
        print("[voice] 提醒：语音版权归米哈游；这些文件会随仓库分发，仅用于非商业的个人学习项目。")
        return 0

    if not args.speaker:
        parser.print_help()
        return 1
    speaker = args.speaker.strip()
    count = fetch_speaker(speaker, max(1, args.limit), index)
    if count:
        INDEX.parent.mkdir(parents=True, exist_ok=True)
        INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    bank = VoiceBank()
    print(f"[voice] {speaker}: 已下载 {count} 条，当前共 {bank.count()} 条")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
