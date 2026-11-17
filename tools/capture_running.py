"""Find the running Black window, capture the real desktop, and ask it to close."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import win32con
import win32gui
from PIL import ImageGrab

OUT = Path(__file__).resolve().parents[1] / "build" / "running.png"
TITLE = "Black · 提瓦特驻留终端"


def main() -> int:
    hwnd = 0
    for _ in range(30):
        hwnd = win32gui.FindWindow(None, TITLE)
        if hwnd:
            break
        time.sleep(0.5)
    if not hwnd:
        print("window not found")
        return 1
    print("hwnd", hwnd)
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception as e:
        print("foreground failed", e)
    time.sleep(0.8)
    rect = win32gui.GetWindowRect(hwnd)
    print("rect", rect)
    try:
        img = ImageGrab.grab(bbox=rect)
        img.save(OUT)
        print("captured", OUT, img.size)
    except Exception as e:
        print("capture failed", e)
    print("posting close")
    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    time.sleep(1.5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
