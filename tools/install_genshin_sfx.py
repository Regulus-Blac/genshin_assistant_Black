"""Install a collected sound pack into assets/audio/custom.

The bundled sounds in assets/audio are original/CC0 and ship with the repo.
A pack in assets/audio/custom overrides them by file name.  Names:

    chime.wav  levelup.wav  interact.wav  click.wav
    confirm.wav  open.wav  cancel.wav  error.wav

Usage:
    python tools/install_genshin_sfx.py --source build/sfx-candidates --prefix gi_
    python tools/install_genshin_sfx.py --source D:/my-sfx --dry-run

Use --to data/sounds if you would rather keep a pack out of the repository.
"""
from __future__ import annotations

import argparse
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Install a collected UI sound pack")
    parser.add_argument("--source", required=True, help="folder containing the wav files")
    parser.add_argument("--prefix", default="gi_", help="file name prefix in the source folder (default gi_)")
    parser.add_argument(
        "--to",
        default="assets/audio/custom",
        help="target folder relative to the project (default assets/audio/custom)",
    )
    parser.add_argument("--dry-run", action="store_true", help="only show what would be copied")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_dir():
        print(f"source folder not found: {source}")
        return 1
    target = Path(args.to)
    if not target.is_absolute():
        target = ROOT / target
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
        print("Restart Black to hear them; assets/audio/custom wins over assets/audio.")
    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
