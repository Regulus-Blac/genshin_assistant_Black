from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QObject
from PyQt5.QtMultimedia import QSound

from .paths import AUDIO, CUSTOM_AUDIO

# Logical event -> file name.  Every event can be overridden by dropping a file
# with the same name into ``data/sounds`` (kept out of git, see README).
SOUND_FILES = {
    "chime": "chime.wav",
    "levelup": "levelup.wav",
    "interact": "interact.wav",
    "click": "click.wav",
    "confirm": "confirm.wav",
    "open": "open.wav",
    "cancel": "cancel.wav",
    "error": "error.wav",
}


class Sounds(QObject):
    """Tiny UI sound layer. QSound keeps playback off the main thread."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cache: dict[str, QSound] = {}
        self.enabled = True

    def _path(self, name: str) -> Path | None:
        filename = SOUND_FILES.get(name, name)
        # data/sounds wins so a personal "official SFX" pack can replace the
        # bundled ones without editing tracked files.
        for folder in (CUSTOM_AUDIO, AUDIO):
            candidate = Path(folder) / filename
            if candidate.exists():
                return candidate
        return None

    def _sound(self, name: str) -> QSound | None:
        path = self._path(name)
        if path is None:
            return None
        key = str(path)
        if key not in self._cache:
            self._cache[key] = QSound(key, self)
        return self._cache[key]

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self._sound(name)
        if sound is not None:
            sound.play()

    # convenience wrappers -------------------------------------------------
    def chime(self) -> None:
        self.play("chime")

    def levelup(self) -> None:
        self.play("levelup")

    def interact(self) -> None:
        self.play("interact")

    def click(self) -> None:
        self.play("click")

    def confirm(self) -> None:
        self.play("confirm")

    def open(self) -> None:
        self.play("open")

    def cancel(self) -> None:
        self.play("cancel")

    def error(self) -> None:
        self.play("error")
