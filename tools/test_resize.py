"""Smoke test for the frameless window edge resizing."""
from __future__ import annotations

import ctypes
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "resize-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import QEvent, QPoint, Qt  # noqa: E402
from PyQt5.QtGui import QMouseEvent  # noqa: E402
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
    store = Store()
    window = MainWindow(store)
    window.show()
    QTest.qWait(500)
    print("handles", len(window._resize_handles), [(sorted(h.edges), h.geometry().getRect()) for h in window._resize_handles[:2]])
    assert len(window._resize_handles) == 8
    from PyQt5.QtGui import QCursor

    QCursor.setPos(window.mapToGlobal(QPoint(4, window.height() // 2)))
    QTest.qWait(80)
    hwnd = int(window.winId())
    screen_pt = QCursor.pos()
    lparam = ((screen_pt.y() & 0xFFFF) << 16) | (screen_pt.x() & 0xFFFF)
    hit = ctypes.windll.user32.SendMessageW(hwnd, 0x0084, 0, lparam)
    print("native hit", hit, "at", screen_pt)
    assert hit == 10, hit  # HTLEFT
    right = next(h for h in window._resize_handles if h.edges == {"right"})
    before = window.size()
    start = window.mapToGlobal(right.geometry().center())
    press = QMouseEvent(QEvent.MouseButtonPress, QPoint(3, 3), start, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    right.mousePressEvent(press)
    move = QMouseEvent(QEvent.MouseMove, QPoint(3, 3), start + QPoint(90, 0), Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
    right.mouseMoveEvent(move)
    release = QMouseEvent(QEvent.MouseButtonRelease, QPoint(3, 3), start + QPoint(90, 0), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    right.mouseReleaseEvent(release)
    QTest.qWait(200)
    after = window.size()
    print("size", before, after)
    assert after.width() > before.width()
    window.grab().save(str(TEST / "resized.png"))
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
