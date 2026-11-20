"""Install a personal sound pack into data/sounds (never committed).

The bundled sounds in assets/audio are original/CC0 and ship with the repo.
If you want the official Genshin UI sounds on your own machine, put them in a
folder with these names and run this script:

    chime.wav  levelup.wav  interact.wav  click.wav
    confirm.wav  open.wav  cancel.wav  error.wav

Usage:
    python tools/install_genshin_sfx.py --source build/sfx-candidates --prefix gi_
    python tools/install_genshin_sfx.py --source D:/my-sfx --dry-run

The target is ``data/sounds`` (or ``BLACK_DATA_DIR/sounds`` when that env var
is set), which .gitignore already excludes.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TARGET_NAMES = ("chime", "levelup", "interact", "click", "confirm", "open", "cancel", "error")

# Candidate file name -> event name, for the SamToki-style rip set.
DEFAULT_MAP = {
    "chime": "chime",
    "levelup": "levelup",
    "interact": "interact",
    "click": "ui_click",
    "confirm": "confirm",
    "open": "open",
    "cancel": "cancel",
    "error": "error",
}


def data_sounds_dir() -> Path:
    return Path(os.environ.get("BLACK_DATA_DIR", ROOT / "data")) / "sounds"


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a personal UI sound pack")
    parser.add_argument("--source", required=True, help="folder containing the wav files")
    parser.add_argument("--prefix", default="gi_", help="file name prefix in the source folder (default gi_)")
    parser.add_argument("--dry-run", action="store_true", help="only show what would be copied")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_dir():
        print(f"source folder not found: {source}")
        return 1
    target = data_sounds_dir()
    print(f"target: {target}")

    copied = 0
    for event, stem in DEFAULT_MAP.items():
        candidate = source / f"{args.prefix}{stem}.wav"
        if not candidate.exists():
            print(f"  skip {event}: {candidate.name} not found")
            continue
        destination = target / f"{event}.wav"
        print(f"  {'would copy' if args.dry_run else 'copy'} {candidate.name} -> {destination.name}")
        if not args.dry_run:
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, destination)
        copied += 1

    print(f"\n{copied}/{len(TARGET_NAMES)} sounds {'planned' if args.dry_run else 'installed'}.")
    if not args.dry_run and copied:
        print("Restart Black to hear them; the app prefers data/sounds over assets/audio.")
    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
