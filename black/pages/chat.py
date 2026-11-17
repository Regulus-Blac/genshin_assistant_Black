from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QEvent, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import ai, content, theme
from ..dialogs import ConfirmDialog
from ..widgets import Avatar, IconButton

_ORPHAN_WORKERS: list[ai.ChatWorker] = []


class ChatInput(QPlainTextEdit):
    send_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("和 Black 说点什么…   Enter 发送，Shift+Enter 换行")
        self.setFixedHeight(62)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setStyleSheet(
            f"QPlainTextEdit {{ background: rgba(8,14,21,185); border: 1px solid rgba(217,188,125,38); "
            "border-radius: 10px; padding: 9px 10px; font-size: 12px; color: #eee7da; } "
            "QPlainTextEdit:focus { border-color: rgba(217,188,125,120); }"
        )

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatBubble(QWidget):
    def __init__(
        self,
        role: str,
        text: str,
        *,
        time_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        assistant = role == "assistant"
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lay.setSpacing(8)
        if not assistant:
            lay.addStretch(1)
        else:
            avatar = Avatar("black.png", 32)
            lay.addWidget(avatar, 0, Qt.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(3)
        who = QLabel("Black" if assistant else "你")
        who.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 9px; color: {theme.GOLD_SOFT if assistant else theme.FAINT};"
        )
        who.setAlignment(Qt.AlignLeft if assistant else Qt.AlignRight)
        col.addWidget(who)
        bubble = QLabel(text)
        bubble.setTextFormat(Qt.PlainText)
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setMaximumWidth(520)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        if assistant:
            bg = "rgba(24, 38, 53, 230)"
            border = "rgba(217, 188, 125, 36)"
            color = theme.TEXT
            radius = "4px 12px 12px 12px"
        else:
            bg = "rgba(33, 60, 64, 215)"
            border = "rgba(114, 207, 212, 45)"
            color = "#e9f2ee"
            radius = "12px 4px 12px 12px"
        bubble.setStyleSheet(
            f"QLabel {{ background: {bg}; border: 1px solid {border}; border-radius: {radius}; "
            f"padding: 8px 11px; color: {color}; font-size: 12px; line-height: 150%; }}"
        )
        col.addWidget(bubble, 0, Qt.AlignLeft if assistant else Qt.AlignRight)
        if time_text:
            stamp = QLabel(time_text)
            stamp.setStyleSheet(f"font-size: 8px; color: {theme.FAINT};")
            stamp.setAlignment(Qt.AlignLeft if assistant else Qt.AlignRight)
            col.addWidget(stamp)
        lay.addLayout(col, 0)
        if assistant:
            lay.addStretch(1)


class TypingBubble(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 3, 0, 3)
        lay.setSpacing(8)
        lay.addWidget(Avatar("black.png", 32), 0, Qt.AlignTop)
        self.label = QLabel("Black 正在想")
        self.label.setStyleSheet(
            "background: rgba(24,38,53,220); border: 1px solid rgba(217,188,125,32); "
            "border-radius: 4px 12px 12px 12px; padding: 8px 12px; color: #a89d8b; font-size: 11px;"
        )
        lay.addWidget(self.label, 0, Qt.AlignTop)
        lay.addStretch(1)
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.setInterval(420)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def _tick(self) -> None:
        self._dots = (self._dots + 1) % 4
        self.label.setText("Black 正在想" + "·" * self._dots)


class ChatPage(QWidget):
    open_settings_requested = pyqtSignal()

    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._worker: ai.ChatWorker | None = None
        self._typing: TypingBubble | None = None
        self._busy = False
        self._build()
        self._render_history()
        self.refresh_status()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 2, 0)
        root.setSpacing(0)
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("交谈")
        title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 26px; font-weight: 600; color: {theme.TEXT}; letter-spacing: 2px;"
        )
        sub = QLabel("有些话不必说给整个世界听。Black 在这里。")
        sub.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch(1)
        self.status = QLabel("离线陪伴")
        self.status.setStyleSheet(
            f"font-size: 9px; color: {theme.GOLD_SOFT}; background: rgba(217,188,125,12); "
            "border: 1px solid rgba(217,188,125,35); border-radius: 8px; padding: 3px 8px;"
        )
        header.addWidget(self.status, 0, Qt.AlignBottom)
        config_btn = QPushButton("接口设置")
        config_btn.setObjectName("TextButton")
        config_btn.setCursor(Qt.PointingHandCursor)
        config_btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        config_btn.clicked.connect(self.open_settings_requested)
        header.addWidget(config_btn, 0, Qt.AlignBottom)
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("TextButton")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet(f"font-size: 10px; color: {theme.FAINT};")
        clear_btn.clicked.connect(self.clear_chat)
        header.addWidget(clear_btn, 0, Qt.AlignBottom)
        root.addLayout(header)
        root.addSpacing(10)

        self.banner = QFrame()
        self.banner.setStyleSheet(
            "QFrame { background: rgba(217,188,125,10); border: 1px solid rgba(217,188,125,26); border-radius: 9px; }"
        )
        bl = QHBoxLayout(self.banner)
        bl.setContentsMargins(10, 6, 8, 6)
        bl.setSpacing(7)
        icon = QLabel()
        icon.setPixmap(theme.icon("info", theme.GOLD_SOFT, 14).pixmap(14, 14))
        bl.addWidget(icon)
        self.banner_text = QLabel("当前为离线陪伴模式。配置兼容 OpenAI 的接口后，Black 可以和你自由对话。")
        self.banner_text.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        bl.addWidget(self.banner_text, 1)
        banner_btn = QPushButton("去配置")
        banner_btn.setObjectName("TextButton")
        banner_btn.setCursor(Qt.PointingHandCursor)
        banner_btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD};")
        banner_btn.clicked.connect(self.open_settings_requested)
        bl.addWidget(banner_btn, 0)
        root.addWidget(self.banner)
        root.addSpacing(8)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.chat_host = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_host)
        self.chat_layout.setContentsMargins(4, 4, 8, 4)
        self.chat_layout.setSpacing(3)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat_host)
        root.addWidget(self.scroll, 1)

        self.suggest_box = QWidget()
        sug = QHBoxLayout(self.suggest_box)
        sug.setContentsMargins(0, 2, 0, 6)
        sug.setSpacing(6)
        for text in ("帮我拆一下今晚的计划", "我有点学不进去", "离考试还有多久？", "夸夸我"):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background: rgba(255,255,255,5); border: 1px solid rgba(217,188,125,30); "
                "border-radius: 10px; padding: 5px 10px; font-size: 9px; color: #a89d8b; } "
                "QPushButton:hover { background: rgba(217,188,125,18); color: #f3ddaa; border-color: rgba(217,188,125,60); }"
            )
            btn.clicked.connect(lambda _=False, t=text: self._send_preset(t))
            sug.addWidget(btn)
        sug.addStretch(1)
        root.addWidget(self.suggest_box)

        input_frame = QFrame()
        input_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(0, 0, 0, 0)
        il.setSpacing(8)
        self.input = ChatInput()
        self.input.send_requested.connect(self.send)
        il.addWidget(self.input, 1)
        self.send_btn = QToolButton()
        self.send_btn.setObjectName("Play")
        self.send_btn.setFixedSize(46, 46)
        self.send_btn.setIcon(theme.icon("send", "#1c1810", 17))
        self.send_btn.setIconSize(QSize(17, 17))
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setToolTip("发送")
        self.send_btn.clicked.connect(self.send)
        il.addWidget(self.send_btn, 0, Qt.AlignBottom)
        root.addWidget(input_frame)
        hint = QLabel("对话内容只保存在本机 · AI 回复由你自己配置的接口生成")
        hint.setStyleSheet(f"font-size: 8px; color: {theme.FAINT};")
        hint.setAlignment(Qt.AlignRight)
        root.addWidget(hint)

    # ------------------------------------------------------------------
    def refresh_status(self) -> None:
        key = str(self.store.settings.get("api_key", "") or "").strip()
        base = str(self.store.settings.get("api_base", "") or "").strip()
        model = str(self.store.settings.get("api_model", "deepseek-flash") or "deepseek-flash")
        if key:
            self.status.setText(f"AI 已配置 · {model}")
            self.status.setStyleSheet(
                f"font-size: 9px; color: {theme.GREEN}; background: rgba(154,202,132,12); "
                "border: 1px solid rgba(154,202,132,38); border-radius: 8px; padding: 3px 8px;"
            )
            self.banner.setVisible(False)
        else:
            self.status.setText("离线陪伴")
            self.status.setStyleSheet(
                f"font-size: 9px; color: {theme.GOLD_SOFT}; background: rgba(217,188,125,12); "
                "border: 1px solid rgba(217,188,125,35); border-radius: 8px; padding: 3px 8px;"
            )
            self.banner.setVisible(True)
            if base:
                self.banner_text.setText(
                    f"还没有填写 API Key。到「接口设置」填入后，就可以使用 {model} 自由对话。"
                )

    def _render_history(self) -> None:
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        messages = self.store.chat[-40:]
        if not messages:
            welcome = ChatBubble(
                "assistant",
                "初次见面。我是 Black，一只负责看时间、记手札、偶尔催你喝水的黑猫。\n"
                "你可以直接和我说话——即使还没有接入 AI，我也会用自己的方式陪你。",
            )
            self.chat_layout.insertWidget(0, welcome)
        else:
            for i, m in enumerate(messages):
                text = str(m.get("content", ""))
                t = str(m.get("time", ""))
                try:
                    t = datetime.fromisoformat(t).strftime("%H:%M")
                except Exception:
                    t = ""
                bubble = ChatBubble(str(m.get("role", "assistant")), text, time_text=t)
                self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_bottom()

    def _add_bubble(self, role: str, text: str) -> None:
        now = datetime.now().strftime("%H:%M")
        bubble = ChatBubble(role, text, time_text=now)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        QTimer.singleShot(30, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def _set_typing(self, value: bool) -> None:
        if value and not self._typing:
            self._typing = TypingBubble()
            self.chat_layout.insertWidget(self.chat_layout.count() - 1, self._typing)
            self._scroll_bottom()
        elif not value and self._typing:
            self._typing.setParent(None)
            self._typing.deleteLater()
            self._typing = None

    def _send_preset(self, text: str) -> None:
        self.input.setPlainText(text)
        self.send()

    def send(self) -> None:
        if self._busy:
            return
        text = self.input.toPlainText().strip()
        if not text:
            return
        self.input.clear()
        self.suggest_box.setVisible(False)
        self.store.append_chat("user", text)
        self._add_bubble("user", text)
        self._busy = True
        self.send_btn.setEnabled(False)
        key = str(self.store.settings.get("api_key", "") or "").strip()
        if not key:
            self._set_typing(True)
            QTimer.singleShot(650, lambda: self._offline_reply(text))
            return
        context = self.store.context()
        messages = [{"role": "system", "content": ai.build_system_prompt(context)}]
        for m in self.store.chat[-14:]:
            messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})
        worker = ai.ChatWorker(
            str(self.store.settings.get("api_base", "")),
            key,
            str(self.store.settings.get("api_model", "deepseek-flash")),
            messages,
            self,
        )
        worker.ok.connect(self._on_ai_ok)
        worker.failed.connect(self._on_ai_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        self._set_typing(True)
        worker.start()

    def _offline_reply(self, text: str) -> None:
        try:
            reply = ai.offline_reply_for(text, self.store.context())
        except Exception:
            reply = "我在。虽然还没接上 AI，但这一会儿我会安静陪着你。"
        self._set_typing(False)
        self.store.append_chat("assistant", reply)
        self._add_bubble("assistant", reply)
        self._finish_busy()

    def _on_ai_ok(self, reply: str) -> None:
        self._set_typing(False)
        self.store.append_chat("assistant", reply)
        self._add_bubble("assistant", reply)

    def _on_ai_failed(self, message: str) -> None:
        self._set_typing(False)
        fallback = ai.offline_reply_for("在吗", self.store.context())
        text = f"（刚才的信号断了一下：{message}）\n先用离线的方式陪你：{fallback}"
        self.store.append_chat("assistant", text)
        self._add_bubble("assistant", text)

    def _on_worker_finished(self) -> None:
        self._finish_busy()

    def _finish_busy(self) -> None:
        self._busy = False
        self.send_btn.setEnabled(True)
        self.input.setFocus()

    def clear_chat(self) -> None:
        if not self.store.chat:
            return
        if not ConfirmDialog.ask(
            self.window(),
            "清空对话",
            "要清空和 Black 的本地对话记录吗？过去的文字会从这个窗口消失，但学习计时与手札不受影响。",
            "清空",
            danger=True,
        ):
            return
        self.store.clear_chat()
        self._render_history()
        self.suggest_box.setVisible(True)

    def shutdown(self) -> None:
        """Give a running API request a moment to finish before app exit."""
        if self._worker and self._worker.isRunning():
            try:
                self._worker.wait(1400)
            except Exception:
                pass
            if self._worker.isRunning():
                self._worker.setParent(None)
                _ORPHAN_WORKERS.append(self._worker)
                self._worker = None
