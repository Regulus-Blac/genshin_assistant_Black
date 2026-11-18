"""Exercise the important user flows with a temporary data directory."""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "flows"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from black.dialogs import ExamDetailDialog, ExamDialog, SubjectDialog
from black.mainwindow import MainWindow
from black.store import Store
from black.theme import apply_theme


def shot(widget, name):
    QTest.qWait(300)
    pix = widget.grab()
    path = TEST / name
    print("shot", path, pix.save(str(path)))


def wait_until(fn, timeout=15000):
    waited = 0
    while waited < timeout:
        QTest.qWait(250)
        waited += 250
        if fn():
            return True
    return False


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.show()
    QTest.qWait(500)

    # subject dialog round-trip
    dlg = SubjectDialog(window, None)
    dlg.name_edit.setText("阅读")
    dlg.goal_spin.setValue(30)
    dlg._save()
    print("subject dialog", dlg.result_data)
    assert dlg.result_data and dlg.result_data["name"] == "阅读"
    sub = store.add_subject(**dlg.result_data)
    window.study_page.rebuild()
    assert any(s["name"] == "阅读" for s in store.subjects())

    # edit it back
    dlg2 = SubjectDialog(window, sub)
    dlg2.name_edit.setText("阅读与写作")
    dlg2._save()
    assert dlg2.result_data
    store.update_subject(sub["id"], **dlg2.result_data)
    assert any(s["name"] == "阅读与写作" for s in store.subjects())
    store.delete_subject(sub["id"])
    window.study_page.rebuild()

    # exam dialog round-trip
    exam_dlg = ExamDialog(window, None)
    exam_dlg.name_edit.setText("模拟考试")
    exam_dlg.note_edit.setText("测试用")
    exam_dlg._save()
    print("exam dialog", exam_dlg.result_data)
    assert exam_dlg.result_data
    before = len(store.data["exams"])
    saved = store.save_exam(exam_dlg.result_data)
    assert len(store.data["exams"]) == before + 1
    window.study_page.rebuild()
    detail = ExamDetailDialog(window, store.exam_info(saved))
    detail.show()
    QTest.qWait(400)
    shot(detail, "detail_dialog.png")
    detail.close()
    store.delete_exam(saved["id"])
    window.study_page.rebuild()

    # timer toggle via the UI path
    window.study_page._toggle_subject("algo")
    QTest.qWait(1600)
    assert store.active_subject() is not None
    window.study_page._toggle_subject("algo")
    QTest.qWait(300)
    assert store.active_subject() is None
    assert store.total_today() > 0

    # offline chat
    window._goto_page(3)
    window.chat_page.input.setPlainText("我有点学不进去")
    window.chat_page.send()
    QTest.qWait(1400)
    print("chat messages", len(store.chat), store.chat[-1]["content"][:60])
    assert store.chat and store.chat[-1]["role"] == "assistant"
    shot(window, "chat_after.png")

    # online search in the UI
    window._goto_page(2)
    window.music_page.tabs.setCurrentIndex(2)
    window.music_page.search_edit.setText("原神")
    window.music_page.search_online()
    ok = wait_until(lambda: window.music_page.search_btn.isEnabled(), 30000)
    print("search done", ok, "results", window.music_page.online_list.count(), "status", window.music_page.search_status.text())
    shot(window, "online_search.png")
    assert window.music_page.online_list.count() > 0

    # play first online result
    item = window.music_page.online_list.item(0)
    window.music_page._play_online_item(item)
    playing = wait_until(lambda: window.music_engine.is_playing(), 45000)
    print("online playing", playing, "title", window.music_engine.current_text())
    shot(window, "online_playing.png")
    window.music_engine.stop()

    # maximize / restore
    window._toggle_maximize()
    QTest.qWait(300)
    print("maximized", window._maximized, window.outer.contentsMargins().left())
    shot(window, "maximized.png")
    window._toggle_maximize()
    QTest.qWait(300)
    print("restored", window._maximized, window.outer.contentsMargins().left())

    print("tray", bool(window.tray))
    print("OK")
    window._shutting_down = True
    window.close()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
