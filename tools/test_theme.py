"""Visual and behavioural smoke test for the night / daylight palettes."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "theme-test"
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
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.character_picker import CharacterPickerDialog  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.pages.settings import SettingsDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def shot(widget, name):
    QTest.qWait(450)
    path = TEST / name
    print("shot", path.name, widget.grab().save(str(path)), widget.size())


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    store = Store()
    assert store.settings.get("appearance") == "dark"
    theme.set_mode("dark")
    apply_theme(app)
    window = MainWindow(store)
    window.sounds.enabled = False
    window.music_engine.player.setVolume(0)
    window.show()
    QTest.qWait(800)
    window.timer.start("algo")
    QTest.qWait(900)
    shot(window, "dark_study.png")

    # Switch through the real settings dialog (not a direct theme call).
    settings = SettingsDialog(window, store)
    settings.show()
    QTest.qWait(300)
    assert settings.appearance_group.checkedButton().property("mode") == "dark"
    for button in settings.appearance_group.buttons():
        if button.property("mode") == "light":
            button.setChecked(True)
            break
    settings._save()
    result = dict(settings.result_data or {})
    assert result.get("appearance") == "light"
    window._apply_settings(result)
    QTest.qWait(700)
    assert theme.MODE == "light"
    assert store.settings.get("appearance") == "light"
    assert store.active_subject() is not None
    window._goto_page(0)
    shot(window, "light_study.png")

    window._goto_page(1)
    shot(window, "light_journal.png")
    window._goto_page(2)
    shot(window, "light_music.png")
    window._goto_page(3)
    shot(window, "light_chat.png")

    settings2 = SettingsDialog(window, store)
    settings2.show()
    QTest.qWait(450)
    assert settings2.appearance_group.checkedButton().property("mode") == "light"
    shot(settings2, "light_settings.png")
    settings2.reject()
    QTest.qWait(200)

    picker = CharacterPickerDialog(window, "vodyanitsa", "snow")
    picker.show()
    QTest.qWait(450)
    shot(picker, "light_picker.png")
    picker.reject()
    QTest.qWait(200)

    window._show_whisper(manual=True)
    QTest.qWait(400)
    shot(window._whisper_popup, "light_paimon.png")
    window._whisper_popup.close()
    QTest.qWait(150)

    window._toggle_appearance()
    QTest.qWait(650)
    assert theme.MODE == "dark"
    assert store.settings.get("appearance") == "dark"
    assert store.active_subject() is not None
    window._goto_page(0)
    shot(window, "back_to_dark.png")
    print("mode", theme.MODE, "art", window.stage._art_name, "sessions", len(store.data["sessions"]))
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
