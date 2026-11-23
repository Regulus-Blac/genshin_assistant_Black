"""Collection checkboxes and partial-failure imports (1.7.3 fixes)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "import-fixes"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache", "music"):
    (TEST / name).mkdir(parents=True)
shutil.copyfile(ROOT / "data" / "black.json", TEST / "data" / "black.json")
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import QPoint, Qt  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import media_import, theme  # noqa: E402
from black.pages.music_import import CHECK_ROLE, CollectionDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def sample_data() -> dict:
    entries = [
        {"title": f"revolution-the score 第{i}段", "url": f"https://example/{i}", "duration": 200 + i, "group": "正片"}
        for i in range(1, 6)
    ]
    return {
        "title": "revolution-the score",
        "scopes": [{"id": "pages", "label": "本视频的分P（5 段）", "entries": entries}],
        "entries": entries,
    }


def check_collection_dialog(app) -> None:
    dialog = CollectionDialog(None, sample_data())
    dialog.show()
    QTest.qWait(250)
    item = dialog.list.item(0)
    row = dialog.list.itemWidget(item)
    print("checkbox visible", row.check.isVisible(), "checked", bool(item.data(CHECK_ROLE)))
    # clicking the real checkbox must toggle that row only
    before = bool(item.data(CHECK_ROLE))
    QTest.mouseClick(row.check, Qt.LeftButton)
    QTest.qWait(80)
    print("after checkbox click:", before, "->", bool(item.data(CHECK_ROLE)), dialog.summary.text())
    assert bool(item.data(CHECK_ROLE)) != before
    assert dialog._rows[0][1].check.isChecked() == bool(item.data(CHECK_ROLE))
    # clicking the row text also toggles
    QTest.mouseClick(row, Qt.LeftButton, pos=QPoint(row.width() - 30, row.height() // 2))
    QTest.qWait(80)
    assert dialog._rows[0][1].check.isChecked() == bool(item.data(CHECK_ROLE))
    # select-all keeps both the item data and the checkbox widget in sync
    dialog._set_all(Qt.Unchecked)
    QTest.qWait(60)
    assert all(not dialog.list.item(i).data(CHECK_ROLE) for i in range(dialog.list.count()))
    assert all(not row.check.isChecked() for _item, row in dialog._rows)
    dialog._set_all(Qt.Checked)
    QTest.qWait(60)
    dialog._accept_selection()
    print("selected urls", len(dialog.selected_urls), dialog.summary.text())
    assert len(dialog.selected_urls) == 5
    dialog.close()


def check_partial_import(monkeypatch_calls) -> None:
    class FakeYdl:
        pass

    def fake_download(url, output_dir, *, progress=None):
        if progress:
            progress(100, "已保存 MP3")
        if url.endswith("/3"):
            raise RuntimeError("yt-dlp 解析失败：B 站解析被拦截（多半需要登录或触发了风控）")
        path = Path(output_dir) / f"track-{url.rsplit('/', 1)[-1]}.mp3"
        path.write_bytes(b"ID3")
        return path

    media_import.download_audio = fake_download  # type: ignore[assignment]
    urls = [f"https://example/{i}" for i in range(1, 7)]
    worker = media_import.ImportThread(urls, TEST / "music")
    saved, skipped, failed = [], [], []
    worker.done.connect(lambda paths: saved.extend(paths))
    worker.skipped.connect(skipped.append)
    worker.failed.connect(failed.append)
    worker.run()
    print("saved", len(saved), "skipped", skipped, "failed", failed)
    assert len(saved) == 5, saved
    assert skipped and "已跳过 1 首" in skipped[0]
    assert not failed


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    apply_theme(app)
    check_collection_dialog(app)
    check_partial_import(None)
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
