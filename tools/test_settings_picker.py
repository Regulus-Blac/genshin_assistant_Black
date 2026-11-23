"""Settings (sound volume, random whisper) and the character picker (search/order)."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "settings-picker"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache", "music"):
    (TEST / name).mkdir(parents=True)
shutil.copyfile(ROOT / "data" / "black.json", TEST / "data" / "black.json")
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QGridLayout  # noqa: E402

from black import theme  # noqa: E402
from black.character_picker import CharacterPickerDialog  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.pages.settings import SettingsDialog  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402
from black.whispers import RANDOM_CHOICE, WHISPER_AVATARS  # noqa: E402


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    apply_theme(app)
    store = Store()
    store.update_settings(music_folder=str(TEST / "music"))
    win = MainWindow(store)
    win.sounds.enabled = False
    win.show()
    QTest.qWait(700)

    # --- settings: sound volume + random whisper avatar -------------------
    dialog = SettingsDialog(win, store)
    dialog.show()
    QTest.qWait(300)
    assert dialog.volume_slider.value() == int(store.settings.get("sound_volume", 80))
    print("volume slider", dialog.volume_slider.value(), dialog.volume_value.text())
    dialog.volume_slider.setValue(35)
    QTest.qWait(60)
    assert dialog.volume_value.text() == "35%"
    combo = dialog.whisper_avatar_combo
    assert combo.itemData(0) == RANDOM_CHOICE, "the random entry should come first"
    combo.setCurrentIndex(0)
    dialog._save()
    assert dialog.result_data["sound_volume"] == 35
    assert dialog.result_data["whisper_avatar"] == RANDOM_CHOICE
    win.sounds.enabled = True
    win._apply_settings(dialog.result_data)
    print("sounds volume", win.sounds.volume, "setting", store.settings["whisper_avatar"])
    assert abs(win.sounds.volume - 0.35) < 0.01
    assert store.settings["whisper_avatar"] == RANDOM_CHOICE

    # every popup may pick another face, and always a valid one
    speakers = {win._whisper_persona()["speaker"] for _ in range(14)}
    print("random personas", len(speakers), sorted(speakers)[:6])
    assert len(speakers) >= 2
    valid = {item["speaker"] for item in WHISPER_AVATARS}
    assert speakers <= valid
    dialog.close()

    # settings screenshot with the slider and the random entry
    dialog = SettingsDialog(win, store)
    dialog.show()
    QTest.qWait(250)
    dialog.grab().save(str(TEST / "settings.png"))
    dialog.close()

    # --- character picker: search + ordering ------------------------------
    picker = CharacterPickerDialog(win, "vodyanitsa", "", store=store)
    picker.show()
    QTest.qWait(300)
    total = len(picker._tiles)
    print("characters in picker", total)
    assert total >= 55, total
    picker.grab().save(str(TEST / "picker.png"))

    # search only shows matches, compacted to the top-left
    picker.search_edit.setText("蒲公英")
    QTest.qWait(150)
    visible = [cid for cid, tile in picker._tiles.items() if tile.isVisible()]
    print("search 蒲公英 ->", visible, picker.result_label.text())
    assert visible == ["jean"], visible
    grid = picker._grid
    assert grid.itemAtPosition(0, 0).widget() is picker._tiles["jean"]
    picker.grab().save(str(TEST / "picker_search.png"))
    picker.search_edit.clear()
    QTest.qWait(120)

    # right-click ordering: move Jean to the front, then persist
    picker._reorder("jean", "front")
    QTest.qWait(120)
    print("order head", store.settings["character_order"][:3], picker.order_status.text())
    assert store.settings["character_order"][0] == "jean"
    first = picker._grid.itemAtPosition(0, 0).widget()
    assert getattr(first, "meta", {}).get("id") == "jean"
    picker._reorder("jean", "down")
    QTest.qWait(80)
    assert store.settings["character_order"][1] == "jean"
    picker._reorder("jean", "reset")
    QTest.qWait(80)
    assert store.settings["character_order"][0] == "vodyanitsa"
    picker._reorder("qiqi", "front")
    QTest.qWait(80)
    picker.grab().save(str(TEST / "picker_order.png"))
    assert store.settings["character_order"][0] == "qiqi"
    picker.close()

    # the saved order is what the next picker shows
    again = CharacterPickerDialog(win, "vodyanitsa", "", store=store)
    again.show()
    QTest.qWait(200)
    head = [again._order[i] for i in range(3)]
    print("reopened order", head)
    assert head[0] == "qiqi"
    again.close()

    win._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
