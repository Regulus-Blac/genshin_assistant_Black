"""Import your own voice lines into ``data/voice/<角色>/``.

Black never ships Genshin audio (see docs/voice-research.md).  This helper only
moves files you already have into the local, git-ignored voice folder, and can
optionally map one exact quote to one file so the audio matches the text.

Examples
--------
    python tools/import_voices.py --list
    python tools/import_voices.py --speaker 琴 --source D:\\my_voices
    python tools/import_voices.py --speaker 琴 --text "休息也是骑士团的规定。" --file rest.mp3
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black.voices import AUDIO_SUFFIXES, VOICE_DIR, VoiceBank  # noqa: E402


def _manifest_path() -> Path:
    return VOICE_DIR / "manifest.json"


def _read_manifest() -> dict:
    path = _manifest_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_manifest(data: dict) -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    _manifest_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _unique(target: Path) -> Path:
    if not target.exists():
        return target
    index = 2
    while True:
        candidate = target.with_name(f"{target.stem}-{index}{target.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def import_folder(speaker: str, source: Path) -> list[Path]:
    target_dir = VOICE_DIR / speaker
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    if source.is_file():
        files = [source]
    else:
        files = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES)
    for item in files:
        if item.suffix.lower() not in AUDIO_SUFFIXES:
            continue
        target = _unique(target_dir / item.name)
        shutil.copyfile(item, target)
        copied.append(target)
    return copied


def map_line(speaker: str, text: str, filename: str) -> bool:
    target = VOICE_DIR / speaker / filename
    if not target.exists():
        print(f"[voices] 找不到 {target}")
        return False
    data = _read_manifest()
    data.setdefault(speaker, {})[text] = filename
    _write_manifest(data)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="把本地语音文件导入 data/voice/")
    parser.add_argument("--speaker", help="角色名，例如 琴 / 钟离")
    parser.add_argument("--source", help="语音文件或文件夹")
    parser.add_argument("--text", help="要精确匹配的台词（可选）")
    parser.add_argument("--file", help="配合 --text 使用：该台词对应的文件名")
    parser.add_argument("--list", action="store_true", help="列出当前已导入的语音")
    args = parser.parse_args()

    if args.list:
        bank = VoiceBank()
        speakers = bank.speakers()
        if not speakers:
            print(f"[voices] {VOICE_DIR} 里还没有语音。")
        for speaker in speakers:
            print(f"{speaker}: {len(bank.files_for(speaker))} 条")
        print(f"合计 {bank.count()} 条 · {VOICE_DIR}")
        return 0

    if not args.speaker:
        parser.print_help()
        return 1

    if args.text and args.file:
        ok = map_line(args.speaker.strip(), args.text, args.file)
        print("[voices] 已写入台词映射。" if ok else "[voices] 映射失败。")
        return 0 if ok else 1

    if not args.source:
        parser.print_help()
        return 1
    source = Path(args.source).expanduser()
    if not source.exists():
        print(f"[voices] 找不到来源：{source}")
        return 1
    copied = import_folder(args.speaker.strip(), source)
    print(f"[voices] 已导入 {len(copied)} 条到 {VOICE_DIR / args.speaker.strip()}")
    print("[voices] 提醒：这些录音只供本机使用，不要提交到仓库或再分发。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
