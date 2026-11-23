"""Regression test for playlist sort/remove and player controls."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "playlist-action-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import QPoint, Qt  # noqa: E402
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
    window = MainWindow(store)
    window.sounds.enabled = False
    window.music_engine.player.setVolume(0)
    window.show()
    QTest.qWait(500)
    window._goto_page(2)
    page = window.music_page

    pl = store.create_playlist("操作测试")
    page._refresh_playlists(pl["id"])
    for row in range(3):
        page.local_list.setCurrentRow(row)
        page._add_selected_local()
    assert len(store.playlist(pl["id"])["tracks"]) == 3, store.playlist(pl["id"])

    page._set_playlist_mode("sort")
    assert page._playlist_mode == "sort"
    print("sort rows", page.playlist_list.count())
    before = [page.playlist_list.item(i).data(Qt.UserRole).get("path") for i in range(3)]
    item = page.playlist_list.takeItem(0)
    page.playlist_list.insertItem(2, item)
    page.playlist_list.reordered.emit()
    QTest.qWait(80)
    after = [page.playlist_list.item(i).data(Qt.UserRole).get("path") for i in range(3)]
    print("order", before, after)
    assert before != after
    assert len(store.playlist(pl["id"])["tracks"]) == 3

    page._set_playlist_mode("remove")
    assert page._playlist_mode == "remove"
    assert page.remove_bar.isVisible()
    page.playlist_list.item(1).setCheckState(Qt.Checked)
    page._update_remove_count()
    print("remove label", page.remove_count_label.text())
    assert "1" in page.remove_count_label.text()
    page._confirm_remove_checked()
    assert len(store.playlist(pl["id"])["tracks"]) == 2

    # Add-song dialog: check one song from the local library and add it in
    # batch mode to the custom target playlist.
    local_entries = [page._entry_from_local(p) for p in page._local_paths]
    dlg = PlaylistAddDialog(
        page,
        "操作测试",
        [{"id": "local", "name": "本地曲库", "entries": local_entries}],
        lambda entry: store.add_to_playlist(pl["id"], entry),
    )
    dlg.source_list.setCurrentRow(0)
    added = False
    for i in range(dlg.song_list.count()):
        candidate = dlg.song_list.item(i)
        entry = candidate.data(Qt.UserRole)
        if entry and not any(t.get("path") == entry.get("path") for t in store.playlist(pl["id"])["tracks"]):
            candidate.setCheckState(Qt.Checked)
            added = True
            break
    assert added
    dlg._refresh_selection()
    print("batch selection", dlg.selection_label.text())
    dlg._add_checked()
    print("tracks after batch", len(store.playlist(pl["id"])["tracks"]),
          [t.get("title") for t in store.playlist(pl["id"])["tracks"]])
    assert len(store.playlist(pl["id"])["tracks"]) == 3

    # 搜索框：只留下匹配的歌，全选也只勾当前可见的
    first_title = dlg.song_list.item(0).text().splitlines()[0]
    needle = first_title[:4]
    dlg.song_search.setText(needle)
    QTest.qWait(80)
    visible = [i for i in range(dlg.song_list.count()) if not dlg.song_list.item(i).isHidden()]
    print("search", needle, "->", len(visible), dlg.song_title.text())
    assert 0 < len(visible) < dlg.song_list.count()
    dlg._set_all(Qt.Unchecked)
    dlg._set_all(Qt.Checked)
    checked = sum(1 for i in range(dlg.song_list.count()) if dlg.song_list.item(i).checkState() == Qt.Checked)
    print("checked after filtered select-all", checked)
    assert checked == len(visible)
    dlg.song_search.clear()
    QTest.qWait(80)
    dlg._set_all(Qt.Unchecked)

    # 全选 + 批量加入：结果等于本地曲库全部曲目，重复的不会再加一遍
    dlg._set_all(Qt.Checked)
    assert dlg.selection_label.text() == f"已选 {dlg.song_list.count()} 首"
    dlg._add_checked()
    final_tracks = store.playlist(pl["id"])["tracks"]
    print("after select-all", len(final_tracks), "local", len(local_entries))
    assert len(final_tracks) == len(local_entries)
    assert len({t.get("path") for t in final_tracks}) == len(final_tracks)
    dlg.close()

    page.speed_combo.setCurrentIndex(page.speed_combo.findData(1.5))
    assert page.engine.playback_rate == 1.5
    page.engine.queue = []
    page.engine.index = -1
    page.play_btn.click()
    QTest.qWait(450)
    print("playing", page.engine.current_playable(), page.engine.is_playing())
    assert page.engine.current_playable() is not None
    QTest.mouseClick(page.progress, Qt.LeftButton, pos=QPoint(page.progress.width() // 2, page.progress.height() // 2))
    print("seek value", page.progress.value())
    assert 350 <= page.progress.value() <= 650
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
