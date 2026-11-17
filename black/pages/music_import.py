from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..dialogs import GenshinDialog
from ..media_import import (
    ImportThread,
    SearchThread,
    convert_local_media,
    dependencies_ready,
)
from ..store import Store
from ..stage import ElidedLabel
from ..widgets import ProgressBar

_ORPHAN_THREADS: list[QThread] = []


class ConvertThread(QThread):
    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, source: Path, output_dir: Path, parent=None) -> None:
        super().__init__(parent)
        self.source = source
        self.output_dir = output_dir

    def run(self) -> None:
        try:
            self.done.emit(str(convert_local_media(self.source, self.output_dir)))
        except Exception as e:
            self.failed.emit(str(e))


class ImportRow(QWidget):
    def __init__(self, title: str, meta: str, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(52)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(7, 4, 8, 4)
        lay.setSpacing(8)
        badge = QLabel("B站")
        badge.setStyleSheet(
            f"font-size: 8px; color: {theme.GOLD}; background: rgba(217,188,125,14); "
            "border: 1px solid rgba(217,188,125,38); border-radius: 6px; padding: 2px 5px;"
        )
        lay.addWidget(badge, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(0)
        name = ElidedLabel(title)
        name.setStyleSheet(f"font-size: 11px; color: {theme.TEXT};")
        sub = ElidedLabel(meta)
        sub.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        col.addWidget(name)
        col.addWidget(sub)
        lay.addLayout(col, 1)


class MusicImportDialog(GenshinDialog):
    imported = pyqtSignal(str)

    def __init__(self, parent, store: Store) -> None:
        super().__init__(
            parent,
            "导入音乐",
            "从 Bilibili 或任意 yt-dlp 支持的视频链接获取音频，保存到本地曲库。",
            width=650,
        )
        self.store = store
        self._search_worker: SearchThread | None = None
        self._import_worker: ImportThread | None = None
        self._convert_worker: ConvertThread | None = None
        self._results = []
        self._build()

    def _build(self) -> None:
        output_dir = Path(str(self.store.settings.get("music_folder", "") or ""))
        self.output_dir = output_dir
        ready, detail = dependencies_ready()
        if not ready:
            note = QLabel(f"导入工具不可用：{detail}")
            note.setWordWrap(True)
            note.setStyleSheet(f"font-size: 10px; color: {theme.ROSE};")
            self.body.addWidget(note)
        self.hint = QLabel(
            "搜索 B 站公开视频，选择一条后下载音频并转换为 192kbps MP3；也可以直接粘贴 Bilibili 链接。"
            "只用于个人本地试听。"
        )
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        self.body.addWidget(self.hint)

        # search row
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("搜索 B 站，例如：原神 OST / 久石让 / 钢琴")
        self.query_edit.returnPressed.connect(self._search)
        search_row.addWidget(self.query_edit, 1)
        self.search_btn = QPushButton("搜索 B 站")
        self.search_btn.setObjectName("Ghost")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedHeight(34)
        self.search_btn.clicked.connect(self._search)
        search_row.addWidget(self.search_btn)
        self.body.addLayout(search_row)

        self.results = QListWidget()
        self.results.setFixedHeight(176)
        self.results.setStyleSheet(
            "QListWidget { background: rgba(8,14,21,120); border: 1px solid rgba(217,188,125,28); border-radius: 8px; }"
            "QListWidget::item { border-bottom: 1px solid rgba(217,188,125,12); }"
            "QListWidget::item:selected { background: rgba(217,188,125,26); color: #f3ddaa; }"
        )
        self.results.itemDoubleClicked.connect(self._import_selected)
        self.body.addWidget(self.results)
        bottom_search = QHBoxLayout()
        bottom_search.setSpacing(6)
        self.results_status = QLabel("搜索后选择一条视频。")
        self.results_status.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        bottom_search.addWidget(self.results_status, 1)
        self.import_selected_btn = QPushButton("下载选中项为 MP3")
        self.import_selected_btn.setObjectName("Ghost")
        self.import_selected_btn.setCursor(Qt.PointingHandCursor)
        self.import_selected_btn.setFixedHeight(30)
        self.import_selected_btn.clicked.connect(self._import_selected)
        bottom_search.addWidget(self.import_selected_btn)
        self.body.addLayout(bottom_search)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(217,188,125,24); border: none;")
        self.body.addWidget(line)

        # direct URL
        link_row = QHBoxLayout()
        link_row.setSpacing(6)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("粘贴 Bilibili / YouTube 等视频链接")
        self.url_edit.returnPressed.connect(self._import_url)
        link_row.addWidget(self.url_edit, 1)
        self.url_btn = QPushButton("链接转 MP3")
        self.url_btn.setObjectName("Ghost")
        self.url_btn.setCursor(Qt.PointingHandCursor)
        self.url_btn.setFixedHeight(34)
        self.url_btn.clicked.connect(self._import_url)
        link_row.addWidget(self.url_btn)
        self.local_btn = QPushButton("本地视频")
        self.local_btn.setObjectName("Ghost")
        self.local_btn.setCursor(Qt.PointingHandCursor)
        self.local_btn.setFixedHeight(34)
        self.local_btn.clicked.connect(self._convert_local)
        link_row.addWidget(self.local_btn)
        self.body.addLayout(link_row)

        path_label = QLabel(f"保存到本地曲库：{output_dir}")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.body.addWidget(path_label)

        self.progress = ProgressBar(0, color=theme.TEAL, height=6)
        self.progress.setValue(0)
        self.body.addWidget(self.progress)
        self.status = QLabel("准备就绪。")
        self.status.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.body.addWidget(self.status)

        self.body.addStretch(1)
        self.footer.addStretch(1)
        close = self.add_button("关闭")
        close.clicked.connect(self.reject)
        if not ready:
            for w in (self.search_btn, self.import_selected_btn, self.url_btn, self.local_btn):
                w.setEnabled(False)

    def _set_busy(self, busy: bool, label: str = "") -> None:
        self.search_btn.setEnabled(not busy)
        self.import_selected_btn.setEnabled(not busy)
        self.url_btn.setEnabled(not busy)
        self.local_btn.setEnabled(not busy)
        if label:
            self.status.setText(label)

    def _search(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            self.status.setText("先写下想找的歌名或关键词。")
            return
        if self._search_worker and self._search_worker.isRunning():
            return
        self._set_busy(True, "正在搜索 B 站…")
        self.results.clear()
        worker = SearchThread(query, self)
        worker.ok.connect(self._on_search_ok)
        worker.failed.connect(self._on_search_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        self._search_worker = worker
        worker.start()

    def _on_search_ok(self, results: list) -> None:
        self._results = results
        self.results.clear()
        for r in results:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, r.url)
            item.setSizeHint(QSize(100, 52))
            item.setToolTip(f"{r.title}\n{r.author} · {r.duration}")
            self.results.addItem(item)
            self.results.setItemWidget(item, ImportRow(r.title, f"{r.author}  ·  {r.duration}"))
        if results:
            self.results.setCurrentRow(0)
            self.status.setText(f"找到 {len(results)} 条，双击或点击下方按钮下载。")
        else:
            self.status.setText("没有找到结果，换个关键词试试。")
        self._set_busy(False)

    def _on_search_failed(self, message: str) -> None:
        self.status.setText(message)
        self._set_busy(False)

    def _selected_url(self) -> str:
        item = self.results.currentItem()
        if not item:
            return ""
        return str(item.data(Qt.UserRole) or "")

    def _import_selected(self) -> None:
        url = self._selected_url()
        if not url:
            self.status.setText("先在列表里选一条视频。")
            return
        self._start_import(url)

    def _import_url(self) -> None:
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            self.status.setText("请粘贴完整视频链接（http/https）。")
            return
        self._start_import(url)

    def _start_import(self, url: str) -> None:
        if self._import_worker and self._import_worker.isRunning():
            return
        self._set_busy(True, "正在连接视频…")
        self.progress.setValue(0.02)
        worker = ImportThread(url, self.output_dir, self)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_done)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        self._import_worker = worker
        worker.start()

    def _on_progress(self, pct: int, text: str) -> None:
        self.progress.setValue(max(0.01, min(1.0, pct / 100)), animate=True)
        self.status.setText(text)

    def _on_done(self, path: str) -> None:
        self.progress.setValue(1.0, animate=True)
        self.status.setText(f"已保存：{Path(path).name}")
        self.imported.emit(path)
        self._set_busy(False)

    def _on_failed(self, message: str) -> None:
        self.progress.setValue(0)
        self.status.setText(message)
        self._set_busy(False)

    def _convert_local(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择本地视频 / 音频",
            str(Path.home()),
            "媒体文件 (*.mp4 *.mkv *.webm *.flv *.mov *.m4a *.wav *.flac);;所有文件 (*.*)",
        )
        if not path:
            return
        self._set_busy(True, "正在转换为 MP3…")
        self.progress.setValue(0.3)
        worker = ConvertThread(Path(path), self.output_dir, self)
        worker.done.connect(self._on_done)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        self._convert_worker = worker
        worker.start()

    def _wait_workers(self) -> None:
        for worker in (self._search_worker, self._import_worker, self._convert_worker):
            if worker and worker.isRunning():
                worker.wait(2200)
                if worker.isRunning():
                    worker.setParent(None)
                    _ORPHAN_THREADS.append(worker)

    def done(self, result: int) -> None:
        self._wait_workers()
        super().done(result)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._wait_workers()
        super().closeEvent(event)
