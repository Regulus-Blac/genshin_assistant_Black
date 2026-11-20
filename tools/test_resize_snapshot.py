"""Dragging resizes must freeze the content into a snapshot instead of repainting."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "resize-snapshot-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
shutil.copyfile(ROOT / "data" / "black.json", TEST / "data" / "black.json")
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import render_mode, theme  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    apply_theme(app)
    store = Store()
    win = MainWindow(store)
    win.sounds.enabled = False
    win.show()
    QTest.qWait(700)
    win.resize(1300, 820)
    QTest.qWait(400)

    # a single resize (maximise / restore / page layout) paints live
    win.resize(1300, 800)
    QTest.qWait(60)
    print("single resize:", win._in_size_move, getattr(win, "_resize_snapshot", None))
    assert win._in_size_move is False
    assert getattr(win, "_resize_snapshot", None) is None

    # a drag (resize burst) freezes the content, with the paint style untouched
    win.resize(1292, 800)
    QTest.qWait(20)
    win.resize(1282, 800)
    QTest.qWait(20)
    win.resize(1272, 800)
    QTest.qWait(60)
    snap = getattr(win, "_resize_snapshot", None)
    print("drag: frozen", win._in_size_move, "snapshot", snap is not None,
          "fast-paint flag", render_mode.is_fast())
    assert win._in_size_move is True and snap is not None
    assert render_mode.is_fast() is False, "the snapshot path must not restyle the cards"
    frozen = list(win._frozen_children)
    assert frozen and all(not child.updatesEnabled() for child in frozen)

    for width in range(1262, 900, -20):
        win.resize(width, 800)
        QTest.qWait(16)
    assert win._resize_snapshot.geometry() == win.root.rect()
    assert win._compact is False, "compact layout must wait for the gesture to end"

    QTest.qWait(700)
    print("after drag: frozen", win._in_size_move, "compact", win._compact)
    assert win._in_size_move is False
    assert getattr(win, "_resize_snapshot", None) is None
    assert all(child.updatesEnabled() for child in frozen)
    assert win._compact is True
    assert win.stage.isVisible() is False

    # shrinking further still ends in the narrow layout
    win.resize(700, 800)
    QTest.qWait(600)
    assert win._narrow is True
    win._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
