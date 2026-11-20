"""Sound layer: custom pack overrides bundled files, all events resolve."""
from __future__ import annotations

import os
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "sounds-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black.paths import AUDIO, CUSTOM_AUDIO  # noqa: E402
from black.sounds import SOUND_FILES, Sounds  # noqa: E402


def describe(path: Path) -> str:
    with wave.open(str(path), "rb") as handle:
        return f"{handle.getnchannels()}ch {handle.getframerate()}Hz {handle.getnframes() / handle.getframerate():.2f}s"


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    sounds = Sounds()

    print("bundled dir", AUDIO)
    for event, filename in SOUND_FILES.items():
        path = sounds._path(event)
        assert path is not None, f"missing bundled sound for {event}"
        print(f"  {event:9s} -> {path.name:12s} {describe(path)}")
        assert path.parent == AUDIO

    # a personal pack in data/sounds wins over the bundled files
    CUSTOM_AUDIO.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(AUDIO / "chime.wav", CUSTOM_AUDIO / "chime.wav")
    custom = sounds._path("chime")
    print("custom override", custom)
    assert custom == CUSTOM_AUDIO / "chime.wav"
    sounds.play("chime")
    sounds.play("levelup")
    sounds.play("unknown-event")
    QTest.qWait(300)
    print("playback calls ok")

    sounds.enabled = False
    sounds.play("chime")
    print("disabled ok")
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
