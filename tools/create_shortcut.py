"""Create a Windows desktop shortcut to Black."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "run_black.pyw"
ICON = ROOT / "assets" / "app.ico"


def main() -> int:
    try:
        import win32com.client
    except Exception:
        print("需要 pywin32 才能创建快捷方式：python -m pip install pywin32")
        return 1

    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    target = pythonw if pythonw.exists() else python
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = Path(shell.SpecialFolders("Desktop"))
    link_path = desktop / "Black · 提瓦特驻留终端.lnk"
    shortcut = shell.CreateShortCut(str(link_path))
    shortcut.TargetPath = str(target)
    shortcut.Arguments = f'"{SCRIPT}"'
    shortcut.WorkingDirectory = str(ROOT)
    shortcut.IconLocation = str(ICON)
    shortcut.Description = "Black · 本地学习陪伴桌面助手"
    shortcut.Save()
    print(f"已创建：{link_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
