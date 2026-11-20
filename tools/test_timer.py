"""TimerEngine checks: idle heartbeat rollover and switching directions."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = Path(tempfile.mkdtemp(prefix="black-timer-"))
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")

from PyQt5.QtCore import QCoreApplication
from PyQt5.QtTest import QTest

from black.store import Store
from black.timer import TimerEngine


def main() -> int:
    app = QCoreApplication(sys.argv)
    store = Store(TEST / "data" / "black.json", TEST / "journal")
    timer = TimerEngine(store)
    days = []
    ticks = []
    sessions = []
    timer.day_changed.connect(days.append)
    timer.tick.connect(lambda: ticks.append(1))
    timer.session_finished.connect(sessions.append)
    timer._day = "2000-01-01"
    QTest.qWait(1250)
    assert days, "idle timer should detect a date change"
    assert ticks, "idle timer should tick"
    print("idle rollover ok", days[-1], "ticks", len(ticks))

    timer.start("algo")
    QTest.qWait(1100)
    timer.start("english")
    QTest.qWait(200)
    names = [sub["name"] for sub in store.active_subjects()]
    print("parallel timers", names)
    # 1.7: starting a second subject must not stop the first one.
    assert len(names) == 2, names
    assert not sessions, "starting a second timer must not finish the first"
    infos = {info["id"]: info for info in store.subjects()}
    assert infos["algo"]["active"] and infos["english"]["active"]
    today = datetime.now().date().isoformat()
    assert infos["algo"]["live_seconds"] >= 1
    assert infos["english"]["live_seconds"] >= 0

    # pausing one subject leaves the other running
    summary = timer.pause("algo")
    assert summary is not None and summary["subject_id"] == "algo"
    assert [sub["id"] for sub in store.active_subjects()] == ["english"]
    assert store.subject("algo")["days"].get(today, 0) >= 1
    print("one paused, still running:", [sub["name"] for sub in store.active_subjects()])

    # pause_all stops everything that is left
    timer.pause_all()
    assert store.actives() == []
    timer.shutdown()
    assert store.active() is None
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
