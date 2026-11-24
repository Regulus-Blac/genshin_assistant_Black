from __future__ import annotations

import os
import sys
from pathlib import Path

# When packed by PyInstaller, ``__file__`` lives inside the bundle directory
# while user data must stay next to the .exe (writable, survives upgrades).
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parents[1]
    BUNDLE_DIR = APP_DIR

ROOT = APP_DIR
ASSETS = BUNDLE_DIR / "assets"
IMAGES = ASSETS / "images"
AVATARS = ASSETS / "avatars"
FONTS = ASSETS / "fonts"
AUDIO = ASSETS / "audio"
MUSIC = ASSETS / "music"

DATA_DIR = Path(os.environ.get("BLACK_DATA_DIR", APP_DIR / "data"))
JOURNAL_DIR = Path(os.environ.get("BLACK_JOURNAL_DIR", APP_DIR / "journal"))
CACHE_DIR = Path(os.environ.get("BLACK_CACHE_DIR", APP_DIR / "cache"))
# Sound overrides live inside the project tree so collected packs are easy to
# find and share.  ``assets/audio`` keeps the bundled (original/CC0) sounds.
CUSTOM_AUDIO = AUDIO / "custom"
# Bundled character voice lines (see assets/audio/voices/README.md).  Users can
# add their own lines under data/voice, which takes precedence.
BUNDLED_VOICES = AUDIO / "voices"
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
