"""Double-click launcher: no console window, no working-directory surprises."""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

try:
    from app import run

    raise SystemExit(run())
except SystemExit:
    raise
except Exception:
    text = traceback.format_exc()
    try:
        (ROOT / "data").mkdir(parents=True, exist_ok=True)
        (ROOT / "data" / "launch_error.log").write_text(text, encoding="utf-8")
    except Exception:
        pass
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            0,
            "Black 启动失败。\n\n" + text[-1200:] + "\n\n完整信息见 data/launch_error.log",
            "Black",
            0x10,
        )
    except Exception:
        pass
    raise
