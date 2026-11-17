"""Window behavior checks: pin, tray hiding, settings apply."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "window"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from black.mainwindow import MainWindow
from black.pages.settings import SettingsDialog
from black.store import Store
from black.theme import apply_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.show()
    QTest.qWait(500)
    print("initial topmost", bool(window.windowFlags() & Qt.WindowStaysOnTopHint), "visible", window.isVisible())
    window._on_pin_toggled(True)
    QTest.qWait(300)
    print("pinned topmost", bool(window.windowFlags() & Qt.WindowStaysOnTopHint), "visible", window.isVisible())
    window._on_pin_toggled(False)
    QTest.qWait(300)
    print("unpinned topmost", bool(window.windowFlags() & Qt.WindowStaysOnTopHint), "visible", window.isVisible())

    dlg = SettingsDialog(window, store)
    dlg.name_edit.setText("旅行者")
    dlg.interval_spin.setValue(15)
    dlg._save()
    assert dlg.result_data
    window._apply_settings(dlg.result_data)
    QTest.qWait(300)
    assert store.settings["quote_interval_min"] == 15
    print("settings applied", store.settings["quote_interval_min"])

    store.settings["close_to_tray"] = True
    store.save()
    window.close()
    QTest.qWait(300)
    print("after close visible", window.isVisible(), "tray", bool(window.tray))
    assert not window.isVisible()
    window._show_from_tray()
    QTest.qWait(300)
    assert window.isVisible()
    print("restored from tray")
    window._shutting_down = True
    window.close()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
