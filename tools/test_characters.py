"""Character switching visual/functional test."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "characters"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import QTimer  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black.character_picker import CharacterPickerDialog  # noqa: E402
from black.characters import get_character  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def shot(widget, name):
    QTest.qWait(400)
    pix = widget.grab()
    path = TEST / name
    print("shot", path.name, pix.save(str(path)), pix.size())


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.show()
    QTest.qWait(600)
    print("initial character", store.settings.get("character"), window.stage._look_kind)
    shot(window, "vodyanitsa_stage.png")

    window.stage.set_character(get_character("furina"), "splash")
    window._last_greeting_key = ""
    window._update_clock()
    QTest.qWait(1100)
    shot(window, "furina_stage.png")

    dlg = CharacterPickerDialog(window, "furina", "splash")
    dlg.show()
    QTest.qWait(500)
    shot(dlg, "picker_furina.png")
    dlg._select_character("vodyanitsa")
    QTest.qWait(300)
    shot(dlg, "picker_vody.png")
    dlg._select_look("tea")
    dlg._apply()
    print("picker result", dlg.result_data)
    assert dlg.result_data and dlg.result_data["character"] == "vodyanitsa"
    assert dlg.result_data["look"] == "tea"

    # Full modal flow through MainWindow: choose Furina, save, redraw.
    def choose_furina():
        modal = QApplication.activeModalWidget()
        assert modal is not None
        modal._tiles["furina"].setChecked(True)
        modal._select_character("furina")
        modal._select_look("splash")
        QTest.qWait(250)
        modal._apply()

    QTimer.singleShot(350, choose_furina)
    window._open_character_picker()
    QTest.qWait(900)
    print("selected", store.settings.get("character"), store.settings.get("look"), window.stage._art_name, window.stage.location.text())
    assert store.settings.get("character") == "furina"
    assert store.settings.get("look") == "splash"
    assert window.stage._art_name == "gallery/furina_splash.jpg"
    assert "芙宁娜" in window.stage.location.text()
    shot(window, "furina_applied.png")

    window._shutting_down = True
    window.close()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
