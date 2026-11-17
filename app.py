from __future__ import annotations

import ctypes
import logging
import os
import sys
import traceback
from pathlib import Path

# Qt's DirectShow backend cannot decode the AAC/M4A previews returned by
# iTunes on every Windows install.  The Media Foundation backend handles both
# M4A previews and ordinary MP3/WAV files, so prefer it when available.
os.environ.setdefault("QT_MULTIMEDIA_PREFERRED_PLUGINS", "windowsmediafoundation")

# Make imports work even when the app is launched by a Windows shortcut.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PyQt5.QtCore import QLockFile, Qt  # noqa: E402
from PyQt5.QtGui import QIcon  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402

from black import __version__  # noqa: E402
from black.mainwindow import MainWindow  # noqa: E402
from black.paths import DATA_DIR, IMAGES, ensure_dirs  # noqa: E402
from black.store import Store  # noqa: E402
from black.theme import apply_theme  # noqa: E402


def _set_windows_app_id() -> None:
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Black.TeyvatDesk.1")
    except Exception:
        pass


def _setup_logging() -> None:
    ensure_dirs()
    log_path = DATA_DIR / "black.log"
    try:
        logging.basicConfig(
            filename=str(log_path),
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
            encoding="utf-8",
        )
    except Exception:
        logging.basicConfig(level=logging.INFO)


def _exception_hook(exc_type, exc, tb) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    text = "".join(traceback.format_exception(exc_type, exc, tb))
    logging.error("Unhandled exception:\n%s", text)
    app = QApplication.instance()
    if app is not None:
        try:
            QMessageBox.critical(
                None,
                "Black 遇到了一个错误",
                "这一处没有处理成功，但学习数据不会丢。\n\n"
                f"{exc_type.__name__}: {str(exc)[:400]}\n\n"
                f"详细日志：{DATA_DIR / 'black.log'}",
            )
        except Exception:
            pass
    else:
        print(text, file=sys.stderr)


def run() -> int:
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    _set_windows_app_id()
    _setup_logging()
    logging.info("Starting Black %s (data=%s)", __version__, DATA_DIR)

    app = QApplication(sys.argv)
    app.setApplicationName("Black")
    app.setApplicationDisplayName("Black · 提瓦特驻留终端")
    app.setOrganizationName("Black")
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(QIcon(str(IMAGES / "app_icon.png")))
    apply_theme(app)
    sys.excepthook = _exception_hook

    lock = QLockFile(str(DATA_DIR / "black.lock"))
    lock.setStaleLockTime(15000)
    if not lock.tryLock(150):
        QMessageBox.information(
            None,
            "Black 已经在运行",
            "小黑猫已经在书桌边了。\n请看看任务栏右下角的托盘，或关闭另一个 Black 后再试。",
        )
        return 0

    try:
        store = Store()
    except Exception as e:
        logging.exception("Failed to open the local store")
        QMessageBox.critical(None, "Black 无法启动", f"本地数据读取失败：\n{e}")
        return 1

    try:
        window = MainWindow(store)
        window.show()
        window.raise_()
        window.activateWindow()
        code = app.exec_()
    except Exception:
        logging.exception("Main window failed")
        QMessageBox.critical(None, "Black 无法启动", "主窗口初始化失败，详细日志已写入 data/black.log。")
        code = 1
    finally:
        try:
            lock.unlock()
        except Exception:
            pass
    logging.info("Black closed with code %s", code)
    return int(code)


if __name__ == "__main__":
    raise SystemExit(run())
