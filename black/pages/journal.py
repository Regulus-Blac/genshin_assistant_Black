from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

import markdown as md_lib
from PyQt5.QtCore import QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QTextDocument
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import content, theme
from ..paths import JOURNAL_DIR


class JournalPage(QWidget):
    data_changed = pyqtSignal()

    def __init__(self, store, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.current_key: str = date.today().isoformat()
        self._build()
        self.refresh(select_today=True)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 2, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("手札")
        title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 26px; font-weight: 600; color: {theme.TEXT}; letter-spacing: 2px;"
        )
        sub = QLabel("每一天的修习，会被写成一页本地 Markdown。")
        sub.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch(1)
        self.refresh_btn = QPushButton("刷新今日")
        self.refresh_btn.setObjectName("Ghost")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setFixedHeight(30)
        self.refresh_btn.clicked.connect(lambda: self.refresh(select_today=True, write_today=True))
        header.addWidget(self.refresh_btn, 0, Qt.AlignBottom)
        self.folder_btn = QPushButton("打开文件夹")
        self.folder_btn.setObjectName("Ghost")
        self.folder_btn.setCursor(Qt.PointingHandCursor)
        self.folder_btn.setFixedHeight(30)
        self.folder_btn.clicked.connect(self._open_folder)
        header.addWidget(self.folder_btn, 0, Qt.AlignBottom)
        root.addLayout(header)
        root.addSpacing(13)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(12)

        left = QFrame()
        left.setObjectName("GlassCard")
        left.setStyleSheet(
            "QFrame#GlassCard { background: rgba(20,31,45,190); border: 1px solid rgba(217,188,125,30); border-radius: 13px; }"
        )
        ll = QVBoxLayout(left)
        ll.setContentsMargins(11, 12, 11, 11)
        ll.setSpacing(6)
        rail_title = QLabel("页 面")
        rail_title.setStyleSheet(f"font-size: 9px; color: {theme.FAINT}; letter-spacing: 2px;")
        ll.addWidget(rail_title)
        self.list = QListWidget()
        self.list.setSpacing(1)
        self.list.itemSelectionChanged.connect(self._on_select)
        ll.addWidget(self.list, 1)
        hint = QLabel("自动保存于\njournal / 年-月-日.md\n\n可以在文件末尾的\n「旅行者手记」补充内容，\nBlack 重新生成时会保留。")
        hint.setStyleSheet(f"font-size: 9px; color: {theme.FAINT}; line-height: 150%;")
        ll.addWidget(hint)
        split.addWidget(left)

        right = QFrame()
        right.setObjectName("PreviewCard")
        right.setStyleSheet(
            "QFrame#PreviewCard { background: rgba(18,28,40,175); border: 1px solid rgba(217,188,125,30); border-radius: 13px; }"
        )
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 12, 14, 10)
        rl.setSpacing(6)
        top = QHBoxLayout()
        self.path_label = QLabel("")
        self.path_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.path_label, 1)
        self.open_file_btn = QPushButton("用系统应用打开")
        self.open_file_btn.setObjectName("TextButton")
        self.open_file_btn.setCursor(Qt.PointingHandCursor)
        self.open_file_btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        self.open_file_btn.clicked.connect(self._open_current)
        top.addWidget(self.open_file_btn)
        rl.addLayout(top)
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setFrameShape(QFrame.NoFrame)
        self.preview.setStyleSheet("QTextBrowser { background: transparent; border: none; }")
        self.preview.document().setDocumentMargin(16)
        rl.addWidget(self.preview, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([180, 650])
        root.addWidget(split, 1)

    # ------------------------------------------------------------------
    def refresh(self, *, select_today: bool = False, write_today: bool = True) -> None:
        today = date.today().isoformat()
        if write_today:
            try:
                self.store.write_daily_note(today, quote=content.daily_quote(today))
            except Exception:
                pass
        self._reload_list(today)
        if select_today or self.current_key not in self._dates:
            self.current_key = today
        self._select_key(self.current_key)
        self._render(self.current_key)

    def _reload_list(self, today: str) -> None:
        self._dates = self.store.journal_dates()
        self.list.blockSignals(True)
        self.list.clear()
        for key in self._dates[:120]:
            d = datetime.strptime(key, "%Y-%m-%d")
            weekday = "一二三四五六日"[d.weekday()]
            label = f"{d.month:02d} 月 {d.day:02d} 日   ·   周{weekday}"
            if key == today:
                label = f"今 天   ·   {d.month:02d}.{d.day:02d}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, key)
            item.setToolTip(key)
            self.list.addItem(item)
        self.list.blockSignals(False)

    def _select_key(self, key: str) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == key:
                self.list.setCurrentItem(item)
                break

    def _on_select(self) -> None:
        item = self.list.currentItem()
        if not item:
            return
        key = item.data(Qt.UserRole)
        if key:
            self.current_key = key
            self._render(key)

    def _render(self, key: str) -> None:
        self.current_key = key
        try:
            text = self.store.journal_text(key)
        except Exception as e:
            text = f"# 读取失败\n\n{e}"
        try:
            body = md_lib.markdown(
                text,
                extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
                output_format="html5",
            )
        except Exception:
            body = f"<pre>{text}</pre>"
        if theme.is_light():
            body_css = f"""
            body {{ color: #2f261b; font-family: 'Noto Sans SC'; font-size: 12.5px; line-height: 1.75; }}
            h1 {{ font-family: 'Noto Serif SC'; color: #7f5d28; font-size: 22px; margin: 2px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #d9cbb5; }}
            h2 {{ font-family: 'Noto Serif SC'; color: {theme.GOLD_SOFT}; font-size: 16px; margin: 20px 0 6px 0; }}
            h3 {{ font-family: 'Noto Serif SC'; color: #5f4b31; font-size: 13.5px; margin: 14px 0 4px 0; }}
            p {{ margin: 5px 0; }}
            blockquote {{ color: #6b583c; background: #f4ecde; border-left: 3px solid {theme.GOLD}; margin: 10px 0; padding: 8px 12px; }}
            strong {{ color: {theme.GOLD_SOFT}; }}
            em {{ color: {theme.MUTED}; }}
            table {{ border-collapse: collapse; width: 100%; margin: 8px 0 10px 0; }}
            th {{ background: #efe3d0; color: #4a3d2b; padding: 6px 7px; border: 1px solid #d9cbb5; font-weight: 600; text-align: left; }}
            td {{ padding: 5px 7px; border: 1px solid #e0d4c0; color: #5a4d3b; }}
            tr:nth-child(even) td {{ background: #f8f1e4; }}
            code {{ color: #8a5f24; background: #f0e5d3; }}
            hr {{ border: none; border-top: 1px solid #ddd0ba; margin: 18px 0; }}
            ul, ol {{ margin: 5px 0 5px 18px; }}
            li {{ margin: 2px 0; }}
            a {{ color: {theme.GOLD_SOFT}; }}
            """
        else:
            body_css = """
            body { color: #e9e1d2; font-family: 'Noto Sans SC'; font-size: 12.5px; line-height: 1.75; }
            h1 { font-family: 'Noto Serif SC'; color: #f3ddaa; font-size: 22px; margin: 2px 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #4b432f; }
            h2 { font-family: 'Noto Serif SC'; color: #d9bc7d; font-size: 16px; margin: 20px 0 6px 0; }
            h3 { font-family: 'Noto Serif SC'; color: #cbbd9d; font-size: 13.5px; margin: 14px 0 4px 0; }
            p { margin: 5px 0; }
            blockquote { color: #d5c5a3; background: #182331; border-left: 3px solid #a98e5c; margin: 10px 0; padding: 8px 12px; }
            strong { color: #f3ddaa; }
            em { color: #a89d8b; }
            table { border-collapse: collapse; width: 100%; margin: 8px 0 10px 0; }
            th { background: #1b2838; color: #e6d6b4; padding: 6px 7px; border: 1px solid #39404a; font-weight: 600; text-align: left; }
            td { padding: 5px 7px; border: 1px solid #303b47; color: #d9d1c2; }
            tr:nth-child(even) td { background: #141f2b; }
            code { color: #e5c98e; background: #17212c; }
            hr { border: none; border-top: 1px solid #3a403d; margin: 18px 0; }
            ul, ol { margin: 5px 0 5px 18px; }
            li { margin: 2px 0; }
            a { color: #d9bc7d; }
            """
        html = f"""
        <html><head><style>
        {body_css}
        </style></head><body>{body}</body></html>
        """
        self.preview.setHtml(html)
        self.preview.verticalScrollBar().setValue(0)
        path = self.store.journal_path(key)
        try:
            shown = path.relative_to(self.store.config_path.parent.parent)
        except Exception:
            shown = path
        self.path_label.setText(f"LOCAL NOTE  ·  {shown}")
        self.open_file_btn.setEnabled(path.exists())

    def _open_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.store.journal_dir)))

    def _open_current(self) -> None:
        path = self.store.journal_path(self.current_key)
        if path.exists():
            os.startfile(str(path))  # noqa: S606

    def show_today(self) -> None:
        self.refresh(select_today=True, write_today=True)
