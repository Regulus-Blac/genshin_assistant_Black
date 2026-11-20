"""Tray music controls, composer popup sizing and batch add dialog."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "tray-music-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache", "music"):
    (TEST / name).mkdir(parents=True)
for name in ("a.mp3", "b.mp3", "c.mp3"):
    shutil.copyfile(ROOT / "assets" / "music" / "星落之庭.wav", TEST / "music" / name)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.pages.music import PlaylistAddDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    store = Store()
    store.update_settings(music_folder=str(TEST / "music"))
    for i in range(7):
        store.create_playlist(f"名字稍长的歌单 {i + 1}")
    win = MainWindow(store)
    win.sounds.enabled = False
    win.music_engine.player.setVolume(0)
    win.show()
    QTest.qWait(700)

    assert win.tray is not None, "no system tray in this session"
    player = win.tray_player
    print("tray player title:", player.title_label.text(),
          "modes:", [b.toolTip() for b in player.mode_buttons.values()])

    # controls work while the window is in the tray
    win.hide()
    QTest.qWait(150)
    player.play_btn.click()
    QTest.qWait(500)
    print("playing", win.music_engine.is_playing(), player.play_btn.toolTip(), win.tray.toolTip())
    assert win.music_engine.is_playing()
    assert player.play_btn.toolTip() == "暂停"
    assert "正在播放" in win.tray.toolTip()
    first = win.music_engine.current_playable().title
    player.next_btn.click()
    QTest.qWait(400)
    second = win.music_engine.current_playable().title
    print("next", first, "->", second)
    assert second != first
    player.prev_btn.click()
    QTest.qWait(300)
    assert win.music_engine.current_playable().title == first

    # the three play modes are reachable from the tray widget
    for mode in ("shuffle", "single", "sequence"):
        player.mode_buttons[mode].click()
        QTest.qWait(200)
        print("mode", mode, "->", win.music_engine.play_mode, "checked",
              [k for k, b in player.mode_buttons.items() if b.isChecked()])
        assert win.music_engine.play_mode == mode
        assert player.mode_buttons[mode].isChecked()

    player.play_btn.click()
    QTest.qWait(300)
    print("paused", win.music_engine.is_playing(), player.play_btn.toolTip())
    assert not win.music_engine.is_playing()
    assert player.play_btn.toolTip() == "播放"

    # combo popup shows several rows and fits the longest name
    win._show_from_tray()
    win._goto_page(2)
    QTest.qWait(250)
    combo = win.music_page.playlist_combo
    combo.showPopup()
    QTest.qWait(250)
    view = combo.view()
    widest = max(view.fontMetrics().horizontalAdvance(combo.itemText(i)) for i in range(combo.count()))
    print("popup", view.window().size(), "rows", combo.count(), "maxVisible", combo.maxVisibleItems())
    assert combo.maxVisibleItems() == 5
    assert view.window().width() >= widest
    assert view.window().height() >= 5 * view.sizeHintForRow(0)
    combo.hidePopup()

    # batch add dialog
    page = win.music_page
    entries = [page._entry_from_local(p) for p in page._local_paths]
    target = store.create_playlist("批量目标")
    dialog = PlaylistAddDialog(page, "批量目标",
                               [{"id": "local", "name": "本地曲库", "entries": entries}],
                               lambda e: store.add_to_playlist(target["id"], e))
    dialog.source_list.setCurrentRow(0)
    dialog._set_all(Qt.Checked)
    print("batch", dialog.selection_label.text())
    dialog._add_checked()
    assert len(store.playlist(target["id"])["tracks"]) == len(entries)
    dialog._set_all(Qt.Unchecked)
    assert dialog.add_selected_btn.isEnabled() is False
    dialog.close()

    win._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
