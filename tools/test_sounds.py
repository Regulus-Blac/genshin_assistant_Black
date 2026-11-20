"""Sound layer: bundled files resolve, custom overrides win, all events load."""
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
for name in ("data", "journal", "cache", "custom"):
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

    print("bundled dir", AUDIO, "custom dir", CUSTOM_AUDIO)
    for event, filename in SOUND_FILES.items():
        path = sounds._path(event)
        assert path is not None, f"missing sound for {event}"
        print(f"  {event:9s} -> {path.parent.name}/{path.name:12s} {describe(path)}")

    # A file in the override directory wins over the bundled one.
    override = TEST / "custom"
    shutil.copyfile(AUDIO / "chime.wav", override / "chime.wav")
    tweaked = Sounds(override_dirs=[override])
    assert tweaked._path("chime") == override / "chime.wav", tweaked._path("chime")
    assert tweaked._path("click").parent == AUDIO
    print("override ok")

    # The project tree has the collected pack in place.
    collecton = CUSTOM_AUDIO.exists()
    print("assets/audio/custom exists:", collecton,
          "files:", len(list(CUSTOM_AUDIO.glob("*.wav"))) if collecton else 0)

    sounds.enabled = False
    sounds.play("chime")
    sounds.play("unknown-event")
    print("disabled/unknown ok")
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
