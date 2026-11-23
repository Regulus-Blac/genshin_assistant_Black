"""Character voice lines: bundled in ``assets/audio/voices`` + user files.

The project ships a small, non-commercial set of Chinese voice lines under
``assets/audio/voices/<角色>/`` (see the README there for attribution and the
takedown note).  Users may drop their own recordings into ``data/voice/<角色>/``;
those take precedence and stay out of git.

An optional ``manifest.json`` maps an exact quote to a file so the audio and the
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

from .paths import BUNDLED_VOICES, DATA_DIR

VOICE_DIR = DATA_DIR / "voice"
AUDIO_SUFFIXES = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".opus"}


class VoiceBank:
    """Looks up a recording for a speaker / quote across several folders."""

    def __init__(self, folders: list[str | Path] | None = None) -> None:
        if folders is None:
            # User files first so a personal replacement wins over the bundled one.
            folders = [VOICE_DIR, BUNDLED_VOICES]
        self.folders = [Path(folder) for folder in folders]

    def _manifests(self) -> list[dict]:
        merged: dict[str, dict] = {}
        for folder in reversed(self.folders):  # bundled first, user overrides
            path = folder / "manifest.json"
            if not path.exists():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(data, dict):
                continue
            for speaker, mapping in data.items():
                if isinstance(mapping, dict):
                    merged.setdefault(str(speaker), {}).update(
                        {str(k): str(v) for k, v in mapping.items()}
                    )
        return [merged] if merged else []

    def speakers(self) -> list[str]:
        names: set[str] = set()
        for folder in self.folders:
            if not folder.exists():
                continue
            for item in folder.iterdir():
                if item.is_dir() and any(
                    p.suffix.lower() in AUDIO_SUFFIXES for p in item.iterdir()
                ):
                    names.add(item.name)
        return sorted(names)

    def files_for(self, speaker: str) -> list[Path]:
        files: list[Path] = []
        seen: set[str] = set()
        for folder in self.folders:
            folder = folder / speaker
            if not folder.exists():
                continue
            for path in sorted(folder.iterdir()):
                if not path.is_file() or path.suffix.lower() not in AUDIO_SUFFIXES:
                    continue
                key = f"{path.parent.name}/{path.name}"
                if key in seen:
                    continue
                seen.add(key)
                files.append(path)
        return files

    def count(self) -> int:
        return sum(len(self.files_for(speaker)) for speaker in self.speakers())

    def line_for(self, speaker: str, text: str = "", *, loose: bool = True) -> Path | None:
        """Exact manifest match first, then (optionally) any line of that speaker."""
        speaker = str(speaker or "")
        if not speaker:
            return None
        for mapping in self._manifests():
            name = (mapping.get(speaker) or {}).get(str(text or ""))
            if not name:
                continue
            for folder in self.folders:
                candidate = folder / speaker / str(name)
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
