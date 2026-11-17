"""Core data tests: recovery, midnight split, levels, notes, exams."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black.levels import level_info  # noqa: E402
from black.store import Store  # noqa: E402


def new_store(now=None):
    root = Path(tempfile.mkdtemp(prefix="black-core-"))
    return Store(root / "black.json", root / "journal", now=now or datetime.now()), root


def test_timer_and_journal():
    store, root = new_store(datetime(2026, 11, 16, 9, 0))
    start = datetime(2026, 11, 16, 9, 0)
    store.start("algo", start)
    info = store.subject_info(store.subject("algo"), start + timedelta(minutes=30))
    assert info["today_seconds"] == 1800
    summary = store.pause(start + timedelta(minutes=30))
    assert summary["seconds"] == 1800
    assert store.subject_info(store.subject("algo"), start + timedelta(minutes=30))["today_seconds"] == 1800
    assert store.total_today(start + timedelta(minutes=30)) == 1800
    assert store.write_daily_note("2026-11-16", now=start + timedelta(minutes=30)).exists()
    print("timer/journal ok")


def test_midnight_split():
    store, root = new_store(datetime(2026, 11, 16, 23, 40))
    store.start("english", datetime(2026, 11, 16, 23, 40))
    store.pause(datetime(2026, 11, 17, 0, 20))
    days = store.subject("english")["days"]
    assert days["2026-11-16"] == 1200, days
    assert days["2026-11-17"] == 1200, days
    print("midnight split ok")


def test_streak_and_levels():
    store, root = new_store(datetime(2026, 11, 16, 12, 0))
    sub = store.subject("algo")
    for i in range(7):
        sub["days"][(datetime(2026, 11, 10) + timedelta(days=i)).date().isoformat()] = 1800
    store.save()
    info = store.subject_info(sub, datetime(2026, 11, 16, 12, 0))
    assert info["streak"] == 7, info
    assert info["best_streak"] == 7, info
    base = level_info(7 * 1800, 0)
    boosted = level_info(7 * 1800, 7)
    assert boosted.xp_seconds > base.xp_seconds
    assert boosted.level >= base.level
    print("streak/level ok", base.level, boosted.level)


def test_recover_stale_active():
    root = Path(tempfile.mkdtemp(prefix="black-recover-"))
    now = datetime(2026, 11, 16, 12, 0)
    store = Store(root / "black.json", root / "journal", now=now)
    store.start("algo", now - timedelta(minutes=30))
    store.heartbeat(now - timedelta(minutes=25), save=True)
    # force a stale active record by loading at now
    loaded = Store(root / "black.json", root / "journal", now=now)
    assert loaded.active() is None, loaded.active()
    assert loaded.recovered_note, loaded.recovered_note
    sec = loaded.subject("algo")["days"].get(now.date().isoformat(), 0)
    assert sec == 300, sec
    print("stale recovery ok", loaded.recovered_note)


def test_resume_recent_active():
    root = Path(tempfile.mkdtemp(prefix="black-resume-"))
    now = datetime(2026, 11, 16, 12, 0)
    store = Store(root / "black.json", root / "journal", now=now)
    store.start("english", now - timedelta(minutes=3))
    store.heartbeat(now - timedelta(seconds=10), save=True)
    loaded = Store(root / "black.json", root / "journal", now=now)
    assert loaded.active() is not None, "recent active should resume"
    print("resume active ok")


def test_journal_user_notes_preserved():
    store, root = new_store(datetime(2026, 11, 16, 9, 0))
    store.start("algo", datetime(2026, 11, 16, 9, 0))
    store.pause(datetime(2026, 11, 16, 9, 20))
    path = store.write_daily_note("2026-11-16", now=datetime(2026, 11, 16, 9, 21))
    text = path.read_text(encoding="utf-8")
    marker = "<!-- BLACK:USER-NOTES -->"
    assert marker in text
    path.write_text(text.replace(marker, marker + "\n- 今天发现自己还是喜欢写代码。\n"), encoding="utf-8")
    # regenerate as the UI does
    store.write_daily_note("2026-11-16", now=datetime(2026, 11, 16, 10, 0))
    text2 = path.read_text(encoding="utf-8")
    assert "今天发现自己还是喜欢写代码" in text2, text2
    print("user notes preserved ok")


def test_exams():
    store, root = new_store(datetime(2026, 11, 16, 9, 0))
    exams = store.exams(datetime(2026, 11, 16, 9, 0))
    cet = next(e for e in exams if "六级" in e["name"])
    assert cet["date"] == "2026-12-12"
    assert cet["date_label"].endswith("15:00")
    assert cet["hours_left"] <= 23
    # add / edit / delete
    saved = store.save_exam({"name": "测试考试", "date": "2026-11-20", "time": "14:30", "note": "x"})
    assert store.exam(saved["id"])
    store.save_exam({**saved, "time": "16:00"})
    assert store.exam(saved["id"])["time"] == "16:00"
    store.delete_exam(saved["id"])
    assert store.exam(saved["id"]) is None
    with_id = store.subject("algo")["id"]
    assert store.add_subject("自习", goal_min=30)["name"] == "自习"
    assert store.update_subject(with_id, name="算法与数据结构")
    assert store.delete_subject(with_id)
    print("exams/crud ok")


if __name__ == "__main__":
    test_timer_and_journal()
    test_midnight_split()
    test_streak_and_levels()
    test_recover_stale_active()
    test_resume_recent_active()
    test_journal_user_notes_preserved()
    test_exams()
    print("ALL CORE TESTS PASSED")
