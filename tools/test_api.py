"""Test the OpenAI-compatible API path against a local fake server."""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TEST = ROOT / "build" / "api"
if TEST.exists():
    shutil.rmtree(TEST, ignore_errors=True)
(TEST / "data").mkdir(parents=True)
(TEST / "journal").mkdir()
(TEST / "cache").mkdir()
os.environ["BLACK_DATA_DIR"] = str(TEST / "data")
os.environ["BLACK_JOURNAL_DIR"] = str(TEST / "journal")
os.environ["BLACK_CACHE_DIR"] = str(TEST / "cache")
os.environ.setdefault("QT_QPA_PLATFORM", "windows")

from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from black.mainwindow import MainWindow
from black.store import Store
from black.theme import apply_theme

replies = []


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
            print("REQUEST", self.path, payload.get("model"), len(payload.get("messages", [])))
        except Exception:
            pass
        reply = "我在。先把今晚的目标缩小一点：做二十分钟算法，再休息五分钟。"
        replies.append(reply)
        data = json.dumps(
            {"id": "test", "choices": [{"index": 0, "message": {"role": "assistant", "content": reply}}]},
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print("fake API on", port)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_theme(app)
    store = Store()
    store.update_settings(
        api_base=f"http://127.0.0.1:{port}/v1",
        api_key="test-key",
        api_model="deepseek-flash",
    )
    window = MainWindow(store)
    window.show()
    QTest.qWait(400)
    window._goto_page(3)
    window.chat_page.input.setPlainText("我有点学不进去")
    window.chat_page.send()

    waited = 0
    while waited < 12000 and not (store.chat and store.chat[-1]["role"] == "assistant"):
        QTest.qWait(250)
        waited += 250
    print("waited", waited, "chat", [(m["role"], m["content"][:30]) for m in store.chat])
    assert replies, "fake server was not called"
    assert store.chat[-1]["role"] == "assistant"
    assert "二十分钟" in store.chat[-1]["content"]
    print("OK")
    window._shutting_down = True
    window.close()
    app.quit()
    server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
