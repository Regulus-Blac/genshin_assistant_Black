"""Check local/online audio, QMediaPlayer and Windows TTS."""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest

from black.music_service import MusicEngine, download_track, search_all, scan_folder
from black.paths import CACHE_DIR, MUSIC
from black.sounds import Sounds
from black.tts import TTSService


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    engine = MusicEngine(volume=15)

    def on_err(msg):
        print("PLAYER ERROR:", msg)

    def on_track(*args):
        print("TRACK:", args)

    def on_state(x):
        print("STATE:", x)

    engine.error_occurred.connect(on_err)
    engine.track_changed.connect(on_track)
    engine.state_changed.connect(on_state)

    paths = scan_folder(MUSIC)
    print("local files", [p.name for p in paths])
    engine.play_local_folder(MUSIC, 0)
    QTest.qWait(2600)
    print("state", engine.player.state(), "duration", engine.player.duration(), "pos", engine.player.position())
    print("media", engine.player.media().canonicalUrl().toString() if engine.player.media() else None)
    engine.stop()

    print("searching online...")
    t0 = time.time()
    try:
        tracks = search_all("原神", 4)
        print("search took", round(time.time() - t0, 1), "n", len(tracks))
        for t in tracks[:6]:
            print(" ", t.source, t.title, "|", t.artist, "|", t.duration, t.key)
    except Exception as e:
        print("SEARCH FAILED", type(e).__name__, e)
        tracks = []

    if tracks:
        netease = next((t for t in tracks if t.source == "netease"), tracks[0])
        print("downloading", netease.title)
        try:
            path = download_track(netease, progress=lambda p, s: print(" ", p, s) if p % 20 == 0 else None)
            print("downloaded", path, path.stat().st_size)
            engine.play_queue([__import__("black.music_service", fromlist=["Playable"]).Playable(
                title=netease.title, subtitle=netease.subtitle, track=netease
            )], 0)
            QTest.qWait(3500)
            print("online state", engine.player.state(), "duration", engine.player.duration(), "pos", engine.player.position())
            engine.stop()
        except Exception as e:
            print("DOWNLOAD/PLAY FAILED", type(e).__name__, e)

    sounds = Sounds()
    sounds.chime()
    QTest.qWait(800)
    print("sounds ok")

    tts = TTSService()
    tts.failed.connect(lambda m: print("TTS ERROR:", m))
    tts.spoken.connect(lambda: print("TTS spoken"))
    print("tts speak queued", tts.speak("你好，旅行者。我是 Black。", 0))
    QTest.qWait(3000)
    print("done")
    engine.player.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
