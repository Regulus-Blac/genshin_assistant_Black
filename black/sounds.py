from __future__ import annotations

from PyQt5.QtCore import QObject
from PyQt5.QtMultimedia import QSound

from .paths import AUDIO


class Sounds(QObject):
    """Tiny UI sound layer. QSound keeps playback off the main thread."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._cache: dict[str, QSound] = {}
        self.enabled = True

    def _sound(self, name: str) -> QSound | None:
        path = AUDIO / name
        if not path.exists():
            return None
        if name not in self._cache:
            self._cache[name] = QSound(str(path), self)
        return self._cache[name]

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self._sound(name)
        if sound is not None:
            sound.play()

    def chime(self) -> None:
        self.play("chime.wav")

    def levelup(self) -> None:
        self.play("levelup.wav")

    def interact(self) -> None:
        self.play("interact.wav")
