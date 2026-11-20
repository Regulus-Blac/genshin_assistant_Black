"""Two subjects must be timeable at the same time (1.7)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "parallel"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
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

    ids = [sub["id"] for sub in store.subjects()][:2]
    cards = [win.study_page.cards[sid] for sid in ids]
    names = [store.subject(sid)["name"] for sid in ids]
    print("subjects", names)

    cards[0].play_btn.click()
    QTest.qWait(1200)
    print("after first:", [sub["name"] for sub in store.active_subjects()])
    assert [sub["id"] for sub in store.active_subjects()] == ids[:1]

    cards[1].play_btn.click()
    QTest.qWait(700)
    running = [sub["id"] for sub in store.active_subjects()]
    print("after second:", [sub["name"] for sub in store.active_subjects()])
    # both timers keep running
    assert running == ids, running
    for card in cards:
        assert card._active, "card should show the running state"
        assert card.play_btn.toolTip() == "暂停并记录"
    chip = win.study_page.active_chip.text()
    print("chip:", chip)
    assert names[0] in chip and names[1] in chip and "同时修习" in chip
    print("titlebar:", win.titlebar.status_text() if hasattr(win.titlebar, "status_text") else "-")
    # counters advance independently
    first = store.active_elapsed(None, subject_id=ids[0])
    second = store.active_elapsed(None, subject_id=ids[1])
    print("elapsed", names[0], first, names[1], second)
    assert first > second, (first, second)
    info = {s["id"]: s for s in store.subjects()}
    assert info[ids[0]]["today_seconds"] >= 1 and info[ids[1]]["today_seconds"] >= 0

    # pausing one card leaves the other counting
    cards[0].play_btn.click()
    QTest.qWait(400)
    assert [sub["id"] for sub in store.active_subjects()] == ids[1:]
    assert cards[0]._active is False and cards[1]._active is True
    assert store.subject(ids[0])["days"].get(store.context()["name"] and __import__("datetime").date.today().isoformat(), 0) >= 1

    # tray can pause everything left
    win._tray_pause()
    QTest.qWait(300)
    assert store.actives() == []
    assert win.study_page.active_chip.isVisible() is False
    win.grab().save(str(TEST / "parallel_after_pause.png"))

    # restart both to capture the UI state with two timers
    for card in cards:
        card.play_btn.click()
        QTest.qWait(300)
    QTest.qWait(600)
    win.study_page.grab().save(str(TEST / "parallel_chip.png"))
    print("two running again:", len(store.active_subjects()))
    win._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
