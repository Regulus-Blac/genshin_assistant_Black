"""Verify the iTunes 30s-preview path and download cache."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from black.music_service import MusicEngine, Playable, download_track, search_all


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    tracks = [t for t in search_all("Genshin Impact", 5) if t.source == "itunes"]
    print("itunes results", len(tracks))
    assert tracks, "no iTunes previews"
    track = tracks[0]
    print("download", track.title, track.artist)
    cache = Path(tempfile.mkdtemp(prefix="black-itunes-"))
    path = download_track(track, cache_dir=cache)
    print("file", path, path.stat().st_size)
    assert path.stat().st_size > 20000
    engine = MusicEngine(volume=0)
    errors = []
    engine.error_occurred.connect(errors.append)
    engine.play_queue([Playable(title=track.title, subtitle=track.subtitle, track=track)], 0)
    QTest.qWait(3000)
    print("state", engine.player.state(), "duration", engine.player.duration(), "errors", errors)
    assert engine.is_playing(), errors
    engine.shutdown()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
