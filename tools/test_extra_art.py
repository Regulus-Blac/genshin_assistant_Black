"""User-collected extra art from data/art_extra (1.7.3)."""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "extra-art-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
shutil.copyfile(ROOT / "data" / "black.json", TEST / "data" / "black.json")
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PIL import Image  # noqa: E402
from PyQt5.QtTest import QTest  # noqa: E402
from PyQt5.QtWidgets import QApplication  # noqa: E402

from black import theme  # noqa: E402
from black.characters import art_path, get_character, set_show_extras  # noqa: E402
from black.character_picker import CharacterPickerDialog  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402

EXTRA = TEST / "data" / "art_extra" / "jean"
EXTRA.mkdir(parents=True)
art = EXTRA / "pxTEST.jpg"
thumb = EXTRA / "pxTEST_thumb.jpg"
Image.new("RGB", (900, 1300), (40, 60, 90)).save(art, quality=85)
Image.new("RGB", (300, 400), (40, 60, 90)).save(thumb, quality=85)
(TEST / "data" / "art_extra" / "manifest.json").write_text(
    json.dumps(
        {
            "jean": [
                {
                    "id": "pixiv-test",
                    "label": "人气测试",
                    "orientation": "portrait",
                    "art": str(art.resolve()),
                    "thumb": str(thumb.resolve()),
                    "source": "pixiv",
                    "credit": "测试作品 / 测试作者 / https://www.pixiv.net/artworks/0",
                }
            ]
        },
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


def main() -> int:
    meta = get_character("jean")
    labels = [look.get("label") for look in meta["looks"]]
    print("jean looks", len(labels), labels[-2:])
    assert "人气测试" in labels
    extra = next(look for look in meta["looks"] if look["label"] == "人气测试")
    assert Path(extra["art"]).is_absolute()
    assert art_path(extra["art"]).exists()
    assert art_path("gallery/furina_splash.jpg").is_absolute()
    # relative entries inside data/art_extra are resolved next to manifest.json
    manifest_path = TEST / "data" / "art_extra" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["jean"][0]["art"] = "jean/pxTEST.jpg"
    data["jean"][0]["thumb"] = "jean/pxTEST_thumb.jpg"
    manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    from black.characters import extra_looks
    look = extra_looks()["jean"][0]
    print("relative resolved", Path(look["art"]).name)
    assert Path(look["art"]).is_absolute() and Path(look["art"]).exists()

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    store = Store()
    win = MainWindow(store)
    win.sounds.enabled = False
    win.show()
    QTest.qWait(500)
    picker = CharacterPickerDialog(win, "jean", "", store=store)
    picker.show()
    QTest.qWait(250)
    print("look buttons", len(picker._look_buttons))
    assert "pixiv-test" in picker._look_buttons
    picker._select_look("pixiv-test")
    QTest.qWait(100)
    assert picker._selected_look == "pixiv-test"
    picker.grab().save(str(TEST / "picker_extra.png"))
    picker.close()

    # the stage must accept the absolute art path too
    win._apply_stage_look(meta, extra)
    QTest.qWait(200)
    print("stage art", win.stage._art_name if hasattr(win.stage, "_art_name") else "-")
    assert not win.stage._art.isNull()
    # settings switch hides the collected art from the picker
    set_show_extras(False)
    try:
        hidden = get_character("jean")
        print("hidden looks", len(hidden["looks"]))
        assert "人气测试" not in [look.get("label") for look in hidden["looks"]]
    finally:
        set_show_extras(True)
    restored = get_character("jean")
    assert "人气测试" in [look.get("label") for look in restored["looks"]]

    win._shutdown()
    QTest.qWait(200)
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
