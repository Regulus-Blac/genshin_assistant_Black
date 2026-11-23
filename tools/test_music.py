"""Music page: playlist playback, per-tab queues, search, collection scopes, import."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "music-test"
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
from PyQt5.QtWidgets import QApplication, QDialog  # noqa: E402

from black import theme  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.media_import import ImportThread, bilibili_scopes  # noqa: E402
from black.pages import music_import as import_ui  # noqa: E402
from black.pages.music_import import CHECK_ROLE, CollectionDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    folder = TEST / "music"
    for name in ("alpha.mp3", "beta.mp3", "gamma.mp3", "delta.mp3"):
        shutil.copyfile(ROOT / "assets" / "music" / "星落之庭.wav", folder / name)
    store = Store()
    store.update_settings(music_folder=str(folder))
    window = MainWindow(store)
    window.sounds.enabled = False
    window.music_engine.player.setVolume(0)
    window.show()
    QTest.qWait(500)
    window._goto_page(2)
    page = window.music_page
    QTest.qWait(200)

    # 1. the selector only lists user playlists
    names = [page.playlist_combo.itemText(i) for i in range(page.playlist_combo.count())]
    print("playlists", names)
    assert "本地曲库" not in names
    assert names == []
    assert not page.playlist_sort_btn.isEnabled()

    # 2. the playlist selector only shows on the 歌单 tab
    assert page.tabs.currentIndex() == 0 and page.playlist_bar.isVisible()
    page.tabs.setCurrentIndex(1)
    QTest.qWait(80)
    assert not page.playlist_bar.isVisible()
    page.tabs.setCurrentIndex(2)
    QTest.qWait(80)
    assert not page.playlist_bar.isVisible()
    page.tabs.setCurrentIndex(0)
    QTest.qWait(80)
    assert page.playlist_bar.isVisible()

    # 3. playback queues follow the visible tab
    pl = store.create_playlist("顺序测试")
    for path in page._local_paths:
        store.add_to_playlist(pl["id"], page._entry_from_local(path))
    page._refresh_playlists(pl["id"])
    QTest.qWait(120)
    print("playlist rows", page.playlist_list.count())
    assert page.playlist_list.count() == 4

    page._set_play_mode("sequence")
    page.playlist_list.setCurrentRow(0)
    page.toggle_playback()
    QTest.qWait(400)
    assert page._queue_source == ("playlist", pl["id"])
    assert len(page.engine.queue) == 4
    first = page.engine.current_playable().title
    page.engine.next()
    QTest.qWait(150)
    second = page.engine.current_playable().title
    print("sequence", first, "->", second)
    assert first != second
    assert "歌单" in page.mode_text.text()

    # single-loop keeps the same track on automatic advance
    page._set_play_mode("single")
    page.engine.index = 2
    before = page.engine.queue[2].title
    page.engine.next(automatic=True)
    QTest.qWait(120)
    print("single loop", before, page.engine.current_playable().title)
    assert page.engine.current_playable().title == before
    page._set_play_mode("sequence")

    # the player bar is a transport control: pressing play while something is
    # playing pauses it instead of swapping the queue
    page.tabs.setCurrentIndex(1)
    assert page.engine.is_playing()
    page.toggle_playback()
    QTest.qWait(300)
    print("pause keeps queue", page._queue_source, page.engine.is_playing())
    assert not page.engine.is_playing()
    assert page._queue_source == ("playlist", pl["id"])

    # starting a track in the local library replaces the queue
    page.local_list.setCurrentRow(2)
    page._play_local_item(page.local_list.currentItem())
    QTest.qWait(350)
    print("local source", page._queue_source, "queue", len(page.engine.queue))
    assert page._queue_source == ("local",)
    assert len(page.engine.queue) == 4

    # starting a track in the playlist replaces the queue again
    page.tabs.setCurrentIndex(0)
    page.playlist_list.setCurrentRow(1)
    page._play_playlist_item(page.playlist_list.currentItem())
    QTest.qWait(300)
    print("back to playlist", page._queue_source)
    assert page._queue_source == ("playlist", pl["id"])

    # 4. search inside playlist and local library
    page.playlist_search.setText("alpha")
    QTest.qWait(100)
    print("playlist filter", page.playlist_list.count(), page.playlist_count.text())
    assert page.playlist_list.count() == 1
    assert "/ 4" in page.playlist_count.text()
    page.playlist_search.clear()
    QTest.qWait(80)

    page.tabs.setCurrentIndex(1)
    page.local_search.setText("beta")
    QTest.qWait(100)
    print("local filter", page.local_list.count(), page.local_count.text())
    assert page.local_list.count() == 1
    page.local_search.clear()
    QTest.qWait(80)

    # 5. local drag order still persists
    page._toggle_local_sort()
    assert page._local_sort
    item = page.local_list.takeItem(0)
    page.local_list.insertItem(3, item)
    page.local_list.reordered.emit()
    QTest.qWait(120)
    order = store.settings.get("local_order", [])
    print("local order", [Path(p).name for p in order])
    assert len(order) == 4 and order[-1].endswith("alpha.mp3")
    page._toggle_local_sort()

    # 6. collection dialog: long lists start unchecked, 全选 works
    entries = [
        {"title": f"part {i}", "url": f"https://example/{i}", "duration": 100 + i, "group": "分P"}
        for i in range(1, 31)
    ]
    dialog = CollectionDialog(window, {"title": "合集", "entries": entries})
    dialog.show()
    QTest.qWait(200)
    checked = sum(1 for i in range(dialog.list.count()) if dialog.list.item(i).data(CHECK_ROLE))
    print("collection default", checked, dialog.summary.text())
    assert checked == 0
    dialog._set_all(Qt.Checked)
    QTest.qWait(80)
    dialog._accept_selection()
    assert dialog.result() == QDialog.Accepted
    assert len(dialog.selected_urls) == 30
    dialog.close()

    short = CollectionDialog(window, {"title": "短合集", "entries": entries[:3]})
    short.show()
    QTest.qWait(150)
    checked = sum(1 for i in range(short.list.count()) if short.list.item(i).data(CHECK_ROLE))
    print("short collection default", checked)
    assert checked == 3
    short.close()

    # 6b. a video that is both multi-P and part of a season: the album's own
    # parts are the default scope, the season is an alternative.
    album = [
        {"title": f"track {i}", "url": f"https://example/p{i}", "duration": 120, "group": f"P{i}"}
        for i in range(1, 11)
    ]
    season = [
        {"title": f"other album {i}", "url": f"https://example/s{i}", "duration": 600, "group": "正片"}
        for i in range(1, 5)
    ]
    scoped = CollectionDialog(window, {
        "title": "至冬 OST",
        "scopes": [
            {"id": "pages", "label": f"本视频的分P（{len(album)} 段）", "entries": album},
            {"id": "season", "label": f"整个合集（{len(season)} 段）", "entries": season},
        ],
        "entries": album,
    })
    scoped.show()
    QTest.qWait(200)
    print("scope combo", scoped.scope_combo.currentText() if scoped.scope_combo else None,
          "rows", scoped.list.count())
    assert scoped.scope_combo is not None
    assert scoped.list.count() == len(album)
    assert "分P" in scoped.scope_combo.currentText()
    scoped.scope_combo.setCurrentIndex(1)
    QTest.qWait(150)
    print("after switch", scoped.scope_combo.currentText(), "rows", scoped.list.count())
    assert scoped.list.count() == len(season)
    scoped._set_all(Qt.Checked)
    scoped._accept_selection()
    assert scoped.selected_urls == [e["url"] for e in season]
    scoped.close()

    # 7. multi-URL import thread saves every file (download mocked)
    saved_paths = []

    def fake_download(url, output_dir, progress=None):
        target = Path(output_dir) / f"{url.rsplit('/', 1)[-1]}.mp3"
        target.write_bytes(b"x" * 4096)
        saved_paths.append(str(target))
        if progress:
            progress(100, "done")
        return target

    with patch("black.media_import.download_audio", side_effect=fake_download):
        thread = ImportThread(["https://example/1", "https://example/2"], folder)
        results = []
        thread.done.connect(lambda paths: results.extend(paths))
        thread.run()
    print("import thread saved", [Path(p).name for p in results])
    assert len(results) == 2 and len(saved_paths) == 2

    # 8. a collection probe routes into the selection dialog
    page.tabs.setCurrentIndex(2)
    dialog_import = import_ui.MusicImportDialog(window, store)
    dialog_import.show()
    QTest.qWait(200)
    captured = {}
    dialog_import._start_import = lambda urls: captured.setdefault("urls", list(urls))
    fake_dialog = type("D", (), {
        "exec_": lambda self: QDialog.Accepted,
        "selected_urls": ["https://example/1", "https://example/3"],
    })
    with patch.object(import_ui, "CollectionDialog", lambda parent, data: fake_dialog()):
        dialog_import._on_probed("https://example/x", {"kind": "collection", "title": "t", "entries": entries[:3]})
    print("collection routed", captured.get("urls"))
    assert captured["urls"] == ["https://example/1", "https://example/3"]

    # a single video goes straight to the download path
    captured.clear()
    dialog_import._on_probed("https://example/y", {"kind": "single", "title": "t", "entries": []})
    assert captured["urls"] == ["https://example/y"]
    dialog_import.close()
    dialog_import.deleteLater()
    QTest.qWait(120)

    # 9. Bilibili scope detection: the album wins over the UP's big collection
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def payload(pages: int, season_eps: list[int] | None, bvid: str):
        data = {
            "title": f"video {bvid}",
            "pages": [{"part": f"P{i}", "duration": 100} for i in range(1, pages + 1)],
        }
        if season_eps:
            data["ugc_season"] = {
                "title": "OST 大合集",
                "sections": [{
                    "title": "正片",
                    "episodes": [
                        {"bvid": f"BV{i:010d}", "title": f"album {i}", "arc": {"duration": 600}}
                        for i in season_eps
                    ] + [{"bvid": bvid, "title": "this one", "arc": {"duration": 600}}],
                }],
            }
        return {"code": 0, "data": data}

    # 102-part album that also belongs to a 45-episode season
    with patch("black.media_import.requests.get", return_value=FakeResponse(payload(102, list(range(1, 45)), "BV1xtYC6UEJz"))):
        info = bilibili_scopes("https://www.bilibili.com/video/BV1xtYC6UEJz")
    print("scopes", [(s["id"], len(s["entries"])) for s in info["scopes"]])
    assert info["scopes"][0]["id"] == "pages" and len(info["scopes"][0]["entries"]) == 102
    assert info["scopes"][1]["id"] == "section-0" and len(info["scopes"][1]["entries"]) == 45

    # single-part video inside a season: the season is the default scope
    with patch("black.media_import.requests.get", return_value=FakeResponse(payload(1, list(range(1, 30)), "BV1s8u667Eim"))):
        info = bilibili_scopes("https://www.bilibili.com/video/BV1s8u667Eim")
    print("single-part scopes", [(s["id"], len(s["entries"])) for s in info["scopes"]])
    assert len(info["scopes"]) == 1 and info["scopes"][0]["id"] == "section-0"
    assert len(info["scopes"][0]["entries"]) == 30

    window.hide()
    QTest.qWait(120)
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
