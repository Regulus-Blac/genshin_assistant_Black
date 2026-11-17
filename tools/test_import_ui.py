"""UI smoke test for the Bilibili music importer dialog."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "import_ui"
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

from black.pages.music_import import MusicImportDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def shot(widget, name):
    QTest.qWait(300)
    path = TEST / name
    print("shot", path.name, widget.grab().save(str(path)), widget.size())


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    dlg = MusicImportDialog(None, store)
    dlg.show()
    QTest.qWait(350)
    shot(dlg, "import_empty.png")
    dlg.query_edit.setText("原神 钢琴")
    dlg._search()
    waited = 0
    while waited < 30000:
        QTest.qWait(250)
        waited += 250
        if dlg.search_btn.isEnabled():
            break
    QTest.qWait(300)
    print("waited", waited, "results", dlg.results.count(), "status", dlg.status.text())
    shot(dlg, "import_search.png")
    assert dlg.results.count() > 0
    dlg.close()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
