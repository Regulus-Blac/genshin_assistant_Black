"""Regression test for long character whispers in the stage and popup."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "whisper-size-test"
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
from black.mainwindow import MainWindow  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402

LONG = (
    "白鸦曾替旅人记下归途。别怕，风会把每一页翻到该去的地方；"
    "你只要把今天想做的事写下来，剩下的交给时间。"
)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("dark")
    apply_theme(app)
    store = Store()
    window = MainWindow(store)
    window.show()
    QTest.qWait(500)
    window._set_stage_quote({"speaker": "彩特琳德", "text": LONG})
    QTest.qWait(250)
    stage = window.stage
    print("stage quote", stage.quote_text.size(), stage.quote_text.heightForWidth(stage.quote_text.width()), "card", stage.quote_card.size())
    assert stage.quote_text.height() >= stage.quote_text.heightForWidth(stage.quote_text.width()) - 2
    window.grab().save(str(TEST / "stage_long_quote.png"))

    window._whisper_popup.update_quote({"speaker": "彩特琳德", "text": LONG}, "assets/avatars/brand_day.png", "白鸦的旅人")
    window._whisper_popup.pop({"speaker": "彩特琳德", "text": LONG}, "assets/avatars/brand_day.png", "白鸦的旅人")
    QTest.qWait(350)
    popup = window._whisper_popup
    print("popup", popup.size(), "quote", popup.quote.size(), "need", popup.quote.heightForWidth(popup.quote.width()))
    assert popup.height() > 231
    assert popup.quote.height() >= popup.quote.heightForWidth(popup.quote.width()) - 2
    popup.grab().save(str(TEST / "popup_long_quote.png"))
    popup.close()
    window._shutdown()
    app.quit()
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
