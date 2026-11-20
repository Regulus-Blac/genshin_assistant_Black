from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ASSETS / "images"
AVATARS = ASSETS / "avatars"
FONTS = ASSETS / "fonts"
AUDIO = ASSETS / "audio"
MUSIC = ASSETS / "music"

DATA_DIR = Path(os.environ.get("BLACK_DATA_DIR", ROOT / "data"))
JOURNAL_DIR = Path(os.environ.get("BLACK_JOURNAL_DIR", ROOT / "journal"))
CACHE_DIR = Path(os.environ.get("BLACK_CACHE_DIR", ROOT / "cache"))
# Sound overrides live inside the project tree so collected packs are easy to
# find and share.  ``assets/audio`` keeps the bundled (original/CC0) sounds.
CUSTOM_AUDIO = AUDIO / "custom"
# Older builds kept a personal pack under data/; still honoured as a fallback.
LEGACY_CUSTOM_AUDIO = DATA_DIR / "sounds"

CONFIG_PATH = DATA_DIR / "black.json"
CHAT_PATH = DATA_DIR / "chat.json"


def ensure_dirs() -> None:
    for d in (DATA_DIR, JOURNAL_DIR, CACHE_DIR, CACHE_DIR / "music"):
        d.mkdir(parents=True, exist_ok=True)


def avatar_path(name: str) -> Path:
    p = AVATARS / name
    if p.exists():
        return p
    return AVATARS / "black.png"
