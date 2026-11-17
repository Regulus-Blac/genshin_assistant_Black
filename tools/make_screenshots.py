"""Create the screenshots used by README / presentation."""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "docs-data"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import content  # noqa: E402
from black.character_picker import CharacterPickerDialog  # noqa: E402
from black.characters import get_character  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.pages.settings import SettingsDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def seed(store: Store) -> None:
    now = datetime.now()
    today = now.date()
    subjects = store.data["subjects"]
    # Demo history: enough to show distinct levels and a 7-day streak.
    algo_days = [42, 55, 38, 61, 49, 70, 56]
    eng_days = [18, 25, 30, 20, 35, 25, 24]
    res_days = [0, 18, 22, 0, 28, 30, 22]
    for offset, (a, e, r) in enumerate(zip(algo_days, eng_days, res_days)):
        day = (today - timedelta(days=6 - offset)).isoformat()
        subjects[0]["days"][day] = a * 60
        subjects[1]["days"][day] = e * 60
        subjects[2]["days"][day] = r * 60
    # baseline total levels also account for older study hours
    for sub, old in zip(subjects, (12 * 3600, 4 * 3600, 1 * 3600)):
        past = (today - timedelta(days=7)).isoformat()
        sub["days"][past] = old
    subjects[0]["seen_level"] = 8
    subjects[1]["seen_level"] = 6
    subjects[2]["seen_level"] = 4

    # A finished morning session for the journal, plus the live session below.
    for offset, (sub, mins) in enumerate(((subjects[0], 56), (subjects[1], 24), (subjects[2], 22))):
        start = now.replace(hour=9 + offset, minute=5, second=0, microsecond=0)
        end = start + timedelta(minutes=mins)
        store.data["sessions"].append(
            {
                "id": f"demo-{sub['id']}",
                "subject_id": sub["id"],
                "date": today.isoformat(),
                "start": start.isoformat(timespec="seconds"),
                "end": end.isoformat(timespec="seconds"),
                "seconds": mins * 60,
            }
        )
    store.data["active"] = {
        "subject_id": subjects[0]["id"],
        "started_at": (now - timedelta(minutes=13, seconds=20)).isoformat(timespec="seconds"),
        "heartbeat": now.isoformat(timespec="seconds"),
    }
    store.data["exams"][0]["date"] = "2026-12-12"
    store.data["exams"][0]["time"] = "15:00"
    store.data["exams"][1]["date"] = "2026-12-26"
    store.data["exams"][1]["time"] = "09:00"
    store.data["settings"].update(
        {
            "user_name": "旅行者",
            "desktop_whisper": False,
            "tts_enabled": False,
            "music_volume": 36,
            "auto_play_bgm": False,
            "api_key": "",
            "launches": 3,
        }
    )
    store.chat = []
    store.chat_path.unlink(missing_ok=True)
    store.append_chat("user", "今晚有点学不进去。")
    store.append_chat(
        "assistant",
        "那就把今晚的目标缩小一点。先做二十分钟算法，再休息五分钟。不是每一晚都要打赢一场大战。",
    )
    store.append_chat("user", "六级还有不到一个月，有点慌。")
    store.append_chat(
        "assistant",
        "慌说明你在意。把今天的听力精听一段、阅读一篇做完，剩下的交给重复。明天我还会在这里。",
    )
    store.data["launches"] = 3
    store.save()
    store.write_daily_note(today.isoformat(), quote=content.daily_quote(today.isoformat()))


def shot(widget, name: str) -> None:
    QTest.qWait(400)
    pix = widget.grab()
    path = SHOTS / name
    pix.save(str(path))
    print("shot", path.name, pix.size())


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    seed(store)
    window = MainWindow(store)
    window.sounds.enabled = False
    window.show()
    QTest.qWait(700)
    window._set_stage_quote(
        {
            "speaker": "Black",
            "text": "今天也不用成为谁。把眼前这一页看完，就已经很好。我会替你守着时间。",
        }
    )
    window.stage.set_exam("六级考试 · D-26")
    QTest.qWait(400)
    shot(window, "study.png")

    window._goto_page(1)
    QTest.qWait(500)
    shot(window, "journal.png")

    window._goto_page(2)
    window.music_engine.player.setVolume(0)
    local = [
        p for p in sorted((ROOT / "assets" / "music").glob("*.wav"))
    ]
    if local:
        from black.music_service import Playable

        window.music_engine.play_queue(
            [Playable(title=p.stem, subtitle="Black 原声 · 环境乐", path=p) for p in local], 0
        )
        QTest.qWait(900)
    shot(window, "music.png")
    window.music_engine.player.stop()

    window._goto_page(3)
    QTest.qWait(400)
    shot(window, "chat.png")

    dlg = SettingsDialog(window, store)
    dlg.show()
    QTest.qWait(500)
    shot(dlg, "settings.png")
    dlg.reject()
    QTest.qWait(200)

    picker = CharacterPickerDialog(window, "vodyanitsa", "snow")
    picker.show()
    QTest.qWait(500)
    shot(picker, "character_picker.png")
    picker.reject()
    QTest.qWait(200)

    window._goto_page(0)
    furina = get_character("furina")
    window._character_meta = furina
    store.settings["character"] = "furina"
    store.settings["look"] = "splash"
    store.save()
    window.stage.set_character(furina, "splash")
    window._last_greeting_key = ""
    window._update_clock()
    window._set_stage_quote(
        {
            "speaker": "Black",
            "text": "……芙宁娜会坐在书桌边陪你。放心，计时和手札还是我来管。",
        }
    )
    QTest.qWait(1400)
    shot(window, "character_furina.png")

    window._on_level_ups(
        [{"name": "算法", "level": 8, "title": "勤学", "old_level": 7, "color": "#96cc8e", "element": "dendro"}]
    )
    QTest.qWait(500)
    shot(window, "levelup.png")
    window.overlay.hide_overlay()

    window._show_whisper(manual=True)
    QTest.qWait(500)
    if window._whisper_popup.isVisible():
        shot(window._whisper_popup, "whisper.png")
        window._whisper_popup.close()

    window.timer.pause()
    QTest.qWait(200)
    window._shutting_down = True
    window.close()
    app.quit()
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
