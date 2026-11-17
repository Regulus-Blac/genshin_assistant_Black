"""Local UI smoke test and screenshot generator.

Run:  python tools/ui_smoke.py
Screenshots land in build/screenshots/.
Data for the test lives in build/test-data (never in your real data folder).
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

TEST_ROOT = ROOT / "build" / "smoke"
if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT, ignore_errors=True)
(TEST_ROOT / "data").mkdir(parents=True, exist_ok=True)
(TEST_ROOT / "journal").mkdir(parents=True, exist_ok=True)
(TEST_ROOT / "cache").mkdir(parents=True, exist_ok=True)
(TEST_ROOT / "shots").mkdir(parents=True, exist_ok=True)
os.environ["BLACK_DATA_DIR"] = str(TEST_ROOT / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST_ROOT / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST_ROOT / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import Qt, QTimer  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import content  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.paths import IMAGES  # noqa: E402
from black.pages.settings import SettingsDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def seed(store: Store) -> None:
    now = datetime.now()
    s = store.data["subjects"]
    s[0]["days"] = {
        (now.date() - timedelta(days=i)).isoformat(): int(v)
        for i, v in enumerate([0, 2700, 3300, 2100, 4200, 3600, 1800])
    }
    s[0]["days"][now.date().isoformat()] = 3170
    s[0]["seen_level"] = 5
    s[1]["days"] = {
        (now.date() - timedelta(days=i)).isoformat(): v
        for i, v in enumerate([0, 1500, 1200, 900, 1800, 1500, 1200])
    }
    s[1]["days"][now.date().isoformat()] = 1550
    s[1]["seen_level"] = 4
    s[2]["days"] = {
        (now.date() - timedelta(days=i)).isoformat(): v
        for i, v in enumerate([0, 0, 2400, 0, 1800, 2000, 0])
    }
    s[2]["days"][now.date().isoformat()] = 720
    s[2]["seen_level"] = 3
    today = now.date().isoformat()
    for sub in s:
        sec = sub["days"].get(today, 0)
        if sec:
            start = now - timedelta(seconds=sec)
            store.data["sessions"].append(
                {
                    "id": "demo" + sub["id"],
                    "subject_id": sub["id"],
                    "date": today,
                    "start": start.isoformat(timespec="seconds"),
                    "end": now.isoformat(timespec="seconds"),
                    "seconds": sec,
                }
            )
    store.data["exams"][0]["date"] = (now.date() + timedelta(days=26)).isoformat()
    store.data["exams"][0]["time"] = "15:00"
    store.data["exams"][1]["date"] = (now.date() + timedelta(days=40)).isoformat()
    store.data["exams"][1]["time"] = "09:00"
    store.data["exams"][1]["note"] = "示例日期，点开卡片改成你的真实考试时间"
    store.data["settings"]["user_name"] = "旅行者"
    store.data["settings"]["desktop_whisper"] = False
    store.append_chat("user", "今晚有点学不进去。")
    store.append_chat(
        "assistant",
        "那就把今晚的目标缩小一点。先做二十分钟算法，再休息五分钟。不是每一晚都要打赢一场大战。",
    )
    store.save()
    store.write_daily_note(today, quote=content.daily_quote(today))


def shot(widget, name: str) -> None:
    QTest.qWait(450)
    pix = widget.grab()
    path = TEST_ROOT / "shots" / name
    ok = pix.save(str(path))
    print("shot", name, pix.size(), ok)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    seed(store)
    window = MainWindow(store)
    window.show()
    QTest.qWait(700)
    window.timer.start("algo")
    QTest.qWait(900)
    shot(window, "01_study.png")

    window._goto_page(1)
    QTest.qWait(500)
    shot(window, "02_journal.png")

    window._goto_page(2)
    QTest.qWait(500)
    shot(window, "03_music.png")

    window._goto_page(3)
    QTest.qWait(500)
    shot(window, "04_chat.png")

    dlg = SettingsDialog(window, store)
    dlg.show()
    QTest.qWait(500)
    shot(dlg, "05_settings.png")
    dlg.reject()
    QTest.qWait(200)

    window._goto_page(0)
    window._on_level_ups(
        [{"name": "算法", "level": 5, "title": "精进", "old_level": 4, "color": "#96cc8e", "element": "dendro"}]
    )
    QTest.qWait(500)
    shot(window, "06_levelup.png")
    window.overlay.hide_overlay()

    window._show_whisper(manual=True)
    QTest.qWait(500)
    if window._whisper_popup.isVisible():
        shot(window._whisper_popup, "07_whisper.png")
        window._whisper_popup.close()

    # basic behavior checks
    summary = window.timer.pause()
    assert summary is not None
    assert summary["seconds"] > 0
    assert store.journal_path(datetime.now().date().isoformat()).exists()
    print("session", summary)
    print("today", store.total_today())
    print("OK")

    window._shutting_down = True
    window.close()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
