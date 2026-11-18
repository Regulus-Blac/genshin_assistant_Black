"""Smoke test for playlists, playback modes and whisper persona settings."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "playlist-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.pages.settings import SettingsDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def shot(widget, name):
    QTest.qWait(350)
    path = TEST / name
    print("shot", path.name, widget.grab().save(str(path)), widget.size())


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.sounds.enabled = False
    window.music_engine.player.setVolume(0)
    window.show()
    QTest.qWait(700)
    window._goto_page(2)
    page = window.music_page
    page.tabs.setCurrentIndex(0)
    shot(window, "playlist_local.png")

    pl = store.create_playlist("测试歌单")
    page._refresh_playlists(pl["id"])
    assert page._current_playlist_id == pl["id"]
    page.local_list.setCurrentRow(0)
    page._add_selected_local()
    page.local_list.setCurrentRow(1)
    page._add_selected_local()
    page._refresh_playlist_tracks()
    print("playlist entries", len(store.playlist(pl["id"])["tracks"]))
    assert len(store.playlist(pl["id"])["tracks"]) == 2
    page.playlist_list.setCurrentRow(0)
    page._move_playlist_item(1)
    assert len(store.playlist(pl["id"])["tracks"]) == 2
    page._remove_playlist_item()
    assert len(store.playlist(pl["id"])["tracks"]) == 1
    shot(window, "playlist_custom.png")

    for mode in ("sequence", "shuffle", "single"):
        page._set_play_mode(mode)
        assert page.engine.play_mode == mode
        assert store.settings.get("music_mode") == mode
    # Verify the three playback modes against a small in-memory queue.  These
    # paths are intentionally non-existent; only index/loop logic is asserted.
    from black.music_service import Playable

    page.engine.queue = [Playable("a", "", Path("a")), Playable("b", "", Path("b")), Playable("c", "", Path("c"))]
    page.engine.index = 0
    page.engine.set_play_mode("single")
    page.engine.next(automatic=True)
    assert page.engine.index == 0
    page.engine.set_play_mode("sequence")
    page.engine.index = 2
    page.engine.next(automatic=True)
    assert page.engine.index == 2
    page.engine.set_play_mode("shuffle")
    page.engine.index = 0
    page.engine.next(automatic=True)
    assert 0 <= page.engine.index < 3
    print("modes", page.engine.play_mode, page.mode_buttons.keys())
    shot(window, "playlist_shuffle.png")

    settings = SettingsDialog(window, store)
    settings.show()
    QTest.qWait(350)
    print("avatar choices", settings.whisper_avatar_combo.count())
    assert settings.whisper_avatar_combo.count() > 5
    idx = settings.whisper_avatar_combo.findData("小王子")
    assert idx >= 0
    settings.whisper_avatar_combo.setCurrentIndex(idx)
    settings._save()
    result = dict(settings.result_data or {})
    window._apply_settings(result)
    QTest.qWait(400)
    assert store.settings.get("whisper_avatar") == "小王子"
    window._show_whisper(manual=True)
    QTest.qWait(350)
    print("popup title", window._whisper_popup.title.text())
    assert "小王子" in window._whisper_popup.title.text()
    shot(window._whisper_popup, "whisper_cat.png")
    window._whisper_popup.close()
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
