"""Local-library playlist mode: sort/rename, and custom three actions."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "local-playlist-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache", "music"):
    (TEST / name).mkdir(parents=True)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    folder = TEST / "music"
    for i, name in enumerate(("alpha.mp3", "beta.mp3", "gamma.mp3")):
        shutil.copyfile(ROOT / "assets" / "music" / "星落之庭.wav", folder / name)
    store = Store()
    store.update_settings(music_folder=str(folder))
    window = MainWindow(store)
    window.show()
    QTest.qWait(500)
    window._goto_page(2)
    page = window.music_page
    page.load_local()
    page._refresh_playlists("local")
    QTest.qWait(100)

    assert page.playlist_sort_btn.isVisible()
    assert page.playlist_local_rename_btn.isVisible()
    assert not page.playlist_add_btn.isVisible()
    assert not page.playlist_remove_btn.isVisible()
    print("local actions", page.playlist_sort_btn.text(), page.playlist_local_rename_btn.text())

    page._set_playlist_mode("sort")
    assert page._playlist_mode == "sort"
    item = page.playlist_list.takeItem(0)
    page.playlist_list.insertItem(2, item)
    page.playlist_list.reordered.emit()
    QTest.qWait(120)
    order = store.settings.get("local_order", [])
    print("local order", [Path(p).name for p in order])
    assert len(order) == 3 and order[0].endswith("beta.mp3")

    page._set_playlist_mode("browse")
    page.playlist_list.setCurrentRow(0)
    selected = Path(str(page.playlist_list.currentItem().data(Qt.UserRole)["path"]))
    with patch("black.pages.music.QInputDialog.getText", return_value=("renamed", True)):
        page._rename_local_track()
    QTest.qWait(150)
    print("renamed exists", (folder / "renamed.mp3").exists(), "old", selected.exists())
    assert (folder / "renamed.mp3").exists()
    assert not selected.exists()

    custom = store.create_playlist("自定义")
    page._refresh_playlists(custom["id"])
    QTest.qWait(80)
    assert page.playlist_sort_btn.isVisible()
    assert page.playlist_add_btn.isVisible()
    assert page.playlist_remove_btn.isVisible()
    assert not page.playlist_local_rename_btn.isVisible()
    print("custom actions visible")
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
