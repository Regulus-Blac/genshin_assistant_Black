"""User-imported character voice lines.

The project never ships Genshin audio (see ``docs/voice-research.md``).  If the
user drops recorded lines into ``data/voice/<角色>/`` themselves, the whisper
popup will play one before falling back to TTS.  An optional
``data/voice/manifest.json`` maps an exact quote to a file so the audio and the
text always match:

    {
      "琴": {
        "休息也是骑士团的规定。站起来活动一下，我替你看着时间。": "rest.mp3"
      }
    }
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PyQt5.QtCore import QObject, QUrl
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

from .paths import DATA_DIR

VOICE_DIR = DATA_DIR / "voice"
AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"}


class VoiceBank:
    """Looks up an imported recording for a speaker / quote."""

    def __init__(self, folder: str | Path | None = None) -> None:
        self.folder = Path(folder) if folder else VOICE_DIR

    def _manifest(self) -> dict:
        path = self.folder / "manifest.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def speakers(self) -> list[str]:
        if not self.folder.exists():
            return []
        return sorted(
            item.name
            for item in self.folder.iterdir()
            if item.is_dir() and any(p.suffix.lower() in AUDIO_SUFFIXES for p in item.iterdir())
        )

    def files_for(self, speaker: str) -> list[Path]:
        folder = self.folder / speaker
        if not folder.exists():
            return []
        return sorted(
            p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
        )

    def count(self) -> int:
        return sum(len(self.files_for(speaker)) for speaker in self.speakers())

    def line_for(self, speaker: str, text: str = "", *, loose: bool = True) -> Path | None:
        """Exact manifest match first, then (optionally) any line of that speaker."""
        speaker = str(speaker or "")
        if not speaker:
            return None
        mapping = self._manifest().get(speaker)
        if isinstance(mapping, dict):
            name = mapping.get(str(text or ""))
            if name:
                candidate = self.folder / speaker / str(name)
                if candidate.exists():
                    return candidate
        files = self.files_for(speaker)
        if files and loose:
            return random.choice(files)
        return None


class VoicePlayer(QObject):
    """A small player kept separate from the music engine."""

    def __init__(self, parent: QObject | None = None, volume: int = 85) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._volume = max(0, min(100, int(volume)))
        self._player.setVolume(self._volume)

    @property
    def volume(self) -> int:
        return self._volume

    @volume.setter
    def volume(self, value: int) -> None:
        self._volume = max(0, min(100, int(value)))
        self._player.setVolume(self._volume)

    def play(self, path: str | Path) -> bool:
        file = Path(path)
        if not file.exists():
            return False
        self._player.stop()
        self._player.setMedia(QMediaContent(QUrl.fromLocalFile(str(file))))
        self._player.play()
        return True

    def stop(self) -> None:
        self._player.stop()

    def shutdown(self) -> None:
        """Release the audio session so the process can exit promptly."""
        try:
            self._player.stop()
            self._player.setMedia(QMediaContent())
        except Exception:
            pass

    def current_file(self) -> str:
        media = self._player.media()
        return media.canonicalUrl().toLocalFile() if not media.isNull() else ""
