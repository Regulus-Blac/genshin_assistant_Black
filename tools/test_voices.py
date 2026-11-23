"""User-imported voices from data/voice (1.7.3)."""
from __future__ import annotations

import json
import os
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "voices-test"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
for name in ("data", "journal", "cache"):
    (TEST / name).mkdir(parents=True)
shutil.copyfile(ROOT / "data" / "black.json", TEST / "data" / "black.json")
VOICE_DIR = TEST / "data" / "voice"
(VOICE_DIR / "琴").mkdir(parents=True)
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
from black.voices import VoiceBank  # noqa: E402


def make_wav(path: Path, seconds: float = 0.2) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * int(16000 * seconds))


def main() -> int:
    rest = VOICE_DIR / "琴" / "rest.wav"
    make_wav(rest)
    make_wav(VOICE_DIR / "琴" / "other.wav")
    (VOICE_DIR / "manifest.json").write_text(
        json.dumps({"琴": {"休息也是骑士团的规定。": "rest.wav"}}, ensure_ascii=False),
        encoding="utf-8",
    )

    # isolate the user folder for the resolution checks
    bank = VoiceBank(folders=[VOICE_DIR])
    print("speakers", bank.speakers(), "count", bank.count())
    assert bank.speakers() == ["琴"]
    assert bank.count() == 2
    merged = VoiceBank()
    print("merged voices", merged.count(), "speakers", len(merged.speakers()))
    assert merged.count() >= 2
    exact = bank.line_for("琴", "休息也是骑士团的规定。", loose=False)
    print("exact match", exact.name if exact else None)
    assert exact is not None and exact.name == "rest.wav"
    assert bank.line_for("琴", "完全不同的台词", loose=False) is None
    loose = bank.line_for("琴", "完全不同的台词", loose=True)
    assert loose is not None and loose.parent.name == "琴"
    assert bank.line_for("不存在的角色", "x") is None

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    apply_theme(app)
    store = Store()
    win = MainWindow(store)
    win.sounds.enabled = False
    win.show()
    QTest.qWait(500)
    assert win.voices.count() >= 2
    played = win._play_voice("琴", "休息也是骑士团的规定。")
    QTest.qWait(150)
    print("played", played, "file", Path(win.voice_player.current_file()).name)
    assert played
    assert Path(win.voice_player.current_file()).name == "rest.wav"
    win.voice_player.stop()

    store.settings["voice_enabled"] = False
    assert win._play_voice("琴", "休息也是骑士团的规定。") is False
    store.settings["voice_enabled"] = True
    store.settings["voice_loose"] = False
    assert win._play_voice("琴", "不对应的台词") is False
    # whisper popup exposes a speaker toggle that reflects the setting
    store.settings["whisper_avatar"] = "琴"
    store.settings["voice_loose"] = True
    win._show_whisper(manual=True)
    QTest.qWait(300)
    popup = win._whisper_popup
    print("popup voice button", popup.voice_btn.isEnabled(), popup.voice_btn.isChecked())
    assert popup.voice_btn.isEnabled() and popup.voice_btn.isChecked()
    popup.voice_btn.click()
    QTest.qWait(150)
    assert store.settings["voice_enabled"] is False
    assert popup.voice_btn.isChecked() is False
    popup.voice_btn.click()
    QTest.qWait(250)
    assert store.settings["voice_enabled"] is True
    assert popup.voice_btn.isChecked() is True

    win._shutdown()
    QTest.qWait(300)
    app.quit()
    QTest.qWait(200)
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
