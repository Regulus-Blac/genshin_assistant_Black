"""Responsive window and landscape wheel-chaining regression test."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "responsive-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PyQt5.QtGui import QWheelEvent  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.characters import get_character, get_look  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    window = MainWindow(Store())
    window.show()
    QTest.qWait(500)

    window.resize(560, 700)
    QTest.qWait(400)
    print("compact", window.width(), window.height(), window._compact, window.stage.isVisible(), window.study_page._compact)
    assert window._compact
    assert not window.stage.isVisible()
    assert window.study_page._compact
    assert window.stack_scroll.horizontalScrollBar().maximum() == 0
    window.grab().save(str(TEST / "vertical_strip.png"))

    window.resize(900, 260)
    QTest.qWait(400)
    print("short strip", window.width(), window.height(), window.stage.isVisible())
    assert not window.stage.isVisible()
    assert window.stack_scroll.horizontalScrollBar().maximum() == 0
    window.grab().save(str(TEST / "short_strip.png"))

    window.resize(1380, 864)
    QTest.qWait(400)
    assert window.stage.isVisible()
    furina = get_character("furina")
    wide = get_look(furina, "wide")
    window._apply_stage_look(furina, wide)
    QTest.qWait(500)
    print("landscape", window.stage.size(), "expanded", window.study_page._expanded, "outer", window.stack_scroll.verticalScrollBar().maximum())
    assert window.study_page._expanded
    outer = window.stack_scroll.verticalScrollBar()
    assert outer.maximum() > 0
    viewport = window.study_page.scroll.viewport()
    pos = QPoint(viewport.width() // 2, viewport.height() // 2)
    global_pos = viewport.mapToGlobal(pos)
    event = QWheelEvent(
        QPointF(pos), QPointF(global_pos), QPoint(0, 0), QPoint(0, -120),
        Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False,
    )
    before = outer.value()
    QApplication.sendEvent(viewport, event)
    QTest.qWait(150)
    print("wheel", before, "->", outer.value())
    assert outer.value() > before
    window.grab().save(str(TEST / "landscape_scroll.png"))

    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
