"""Smoke test for wide/landscape stage art and orientation swapping."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "landscape-test"
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
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QVBoxLayout  # noqa: E402

from black import theme  # noqa: E402
from black.characters import get_character, get_look  # noqa: E402
from black.landscape_stage import LandscapeStage  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.stage import CharacterStage  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def shot(widget, name):
    QTest.qWait(500)
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
    QTest.qWait(650)
    shot(window, "portrait.png")
    furina = get_character("furina")
    wide = get_look(furina, "wide")
    assert wide.get("orientation") == "landscape"
    window._apply_stage_look(furina, wide)
    QTest.qWait(800)
    print("stage", type(window.stage).__name__, window.stage.width(), window.stage.height())
    assert isinstance(window.stage, LandscapeStage)
    assert isinstance(window.body_lay, QVBoxLayout)
    assert window.stage.width() > 1000
    shot(window, "landscape.png")
    window.stage.add_hearts(window.stage.rect().center())
    QTest.qWait(200)
    shot(window, "landscape_hearts.png")
    window.stage.set_character(furina, "wide")
    window._refresh_global()
    window._set_initial_quote()
    window._update_clock()
    shot(window, "landscape_populated.png")
    window._apply_stage_look(furina, get_look(furina, "splash"))
    QTest.qWait(650)
    print("back", type(window.stage).__name__, window.stage.width())
    assert isinstance(window.stage, CharacterStage)
    assert isinstance(window.body_lay, QHBoxLayout)
    shot(window, "portrait_again.png")
    # The stage button itself must switch orientation and relayout the page.
    window.stage.orientation_btn.click()
    QTest.qWait(500)
    print("button to landscape", type(window.stage).__name__, window.stage.orientation_btn.text(), type(window.body_lay).__name__)
    assert isinstance(window.stage, LandscapeStage)
    assert isinstance(window.body_lay, QVBoxLayout)
    assert "竖屏" in window.stage.orientation_btn.text()
    window.stage.orientation_btn.click()
    QTest.qWait(500)
    print("button to portrait", type(window.stage).__name__, window.stage.orientation_btn.text(), type(window.body_lay).__name__)
    assert isinstance(window.stage, CharacterStage)
    assert isinstance(window.body_lay, QHBoxLayout)
    assert "横屏" in window.stage.orientation_btn.text()
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
