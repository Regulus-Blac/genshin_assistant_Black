from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
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
    ProbeThread,
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


CHECK_ROLE = Qt.UserRole + 1


class ImportRow(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, title: str, meta: str, badge_text: str = "B站", parent=None) -> None:
        super().__init__(parent)
        self.setFixedHeight(52)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(7, 4, 8, 4)
        lay.setSpacing(8)
        # A real checkbox: the item-widget covers the view's own check indicator,
        # which is why clicking the little box never worked before.
        self.check = QCheckBox()
        self.check.setCursor(Qt.PointingHandCursor)
        self.check.setToolTip("勾选这一段")
        lay.addWidget(self.check, 0, Qt.AlignVCenter)
        badge = QLabel(badge_text)
        badge_bg = theme.mix(theme.GOLD, theme.PANEL, 0.9).name()
        badge.setStyleSheet(
            f"font-size: 8px; color: {theme.GOLD}; background: {badge_bg}; "
            f"border: 1px solid {theme.mix(theme.GOLD, theme.PANEL, 0.7).name()}; border-radius: 6px; padding: 2px 5px;"
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
        self.check.toggled.connect(self.toggled.emit)

    def set_checked(self, checked: bool) -> None:
        self.check.blockSignals(True)
        self.check.setChecked(bool(checked))
        self.check.blockSignals(False)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        # Clicking anywhere on the row flips the checkbox (same as the playlist
        # batch dialog), so a near-miss doesn't silently do nothing.
        if event.button() == Qt.LeftButton and not self.check.geometry().contains(event.pos()):
            self.check.toggle()
        super().mousePressEvent(event)


def result_list_style() -> str:
    """Search result list colours that stay readable in both themes."""
    if theme.is_light():
        # A warm inset panel instead of a pure-white sheet on the cream card.
        bg = theme.PANEL2
        border = theme.mix(theme.GOLD, theme.PANEL, 0.55).name()
        row_line = theme.mix(theme.GOLD, theme.PANEL, 0.78).name()
        selected = "rgba(152, 117, 54, 52)"
        selected_text = theme.TEXT
        text = theme.TEXT_SOFT
    else:
        bg = "rgba(8, 14, 21, 140)"
        border = "rgba(217, 188, 125, 34)"
        row_line = "rgba(217, 188, 125, 14)"
        selected = "rgba(217, 188, 125, 26)"
        selected_text = "#f3ddaa"
        text = theme.TEXT
    return (
        f"QListWidget {{ background: {bg}; border: 1px solid {border}; border-radius: 8px; color: {text}; }}"
        # Qt falls back to the palette base (pure white) for item backgrounds,
        # so paint the items with the same colour as the list itself.
        f"QListWidget::item {{ background: {bg}; border-bottom: 1px solid {row_line}; color: {text}; }}"
        f"QListWidget::item:hover {{ background: {selected}; }}"
        f"QListWidget::item:selected {{ background: {selected}; color: {selected_text}; }}"
    )


class CollectionDialog(GenshinDialog):
    """Pick which parts of a Bilibili collection / multi-P video to import.

    A video can be both a multi-P upload (the album itself) and one episode of
    an UP's bigger collection.  When both exist the dialog offers a scope
    selector and defaults to the video's own parts, which is what people mean
    when they click one album in the search results.
    """

    def __init__(self, parent, data: dict) -> None:
        scopes = list(data.get("scopes") or [])
        if not scopes:
            scopes = [{"id": "default", "label": "片段", "entries": data.get("entries") or []}]
        entries = list(scopes[0].get("entries") or [])
        super().__init__(
            parent,
            "选择要下载的片段",
            self._scope_caption(data, scopes[0]),
            width=640,
        )
        self.scopes = scopes
        self.selected_urls: list[str] = []
        self._data = data
        self._rows: list[tuple[QListWidgetItem, ImportRow]] = []

        top = QHBoxLayout()
        top.setSpacing(8)
        if len(scopes) > 1:
            self.scope_combo = QComboBox()
            self.scope_combo.setFixedHeight(28)
            self.scope_combo.setMinimumWidth(260)
            for scope in scopes:
                self.scope_combo.addItem(str(scope.get("label") or "片段"))
            self.scope_combo.currentIndexChanged.connect(self._load_scope)
            top.addWidget(self.scope_combo)
        else:
            self.scope_combo = None
        self.summary = QLabel("")
        self.summary.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_SOFT};")
        top.addWidget(self.summary, 1)
        self.all_btn = QPushButton("全选")
        self.none_btn = QPushButton("全不选")
        for btn in (self.all_btn, self.none_btn):
            btn.setObjectName("TextButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
            top.addWidget(btn)
        self.body.addLayout(top)

        self.hint = QLabel("")
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet(f"font-size: 9px; color: {theme.ROSE};")
        self.body.addWidget(self.hint)

        self.list = QListWidget()
        self.list.setStyleSheet(result_list_style())
        self.list.setMinimumHeight(300)
        self.list.itemChanged.connect(self._refresh_summary)
        self.body.addWidget(self.list, 1)

        self.all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.none_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        self._load_scope(0)

        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        ok = self.add_button("下载选中片段", primary=True)
        ok.clicked.connect(self._accept_selection)

    @staticmethod
    def _scope_caption(data: dict, scope: dict) -> str:
        entries = scope.get("entries") or []
        total_seconds = sum(int(e.get("duration") or 0) for e in entries)
        hours, rem = divmod(total_seconds, 3600)
        minutes = rem // 60
        length = f"{hours} 小时 {minutes} 分" if hours else f"{minutes} 分钟"
        return f"「{data.get('title') or '合集'}」当前范围 {len(entries)} 段，总时长约 {length}。"

    def _load_scope(self, index: int) -> None:
        if not (0 <= index < len(self.scopes)):
            return
        scope = self.scopes[index]
        entries = list(scope.get("entries") or [])
        # Very long collections start unchecked so a stray double-click cannot
        # start a 200-file download.
        default_checked = 0 < len(entries) <= 25
        self.list.blockSignals(True)
        self.list.clear()
        self._rows = []
        for i, entry in enumerate(entries, 1):
            duration = int(entry.get("duration") or 0)
            minutes, seconds = divmod(duration, 60)
            meta = f"{entry.get('group') or '片段'} · {minutes}:{seconds:02d}"
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry.get("url", ""))
            item.setSizeHint(QSize(100, 52))
            # The row widget owns the checkbox; keep the state in a custom role
            # so the view never draws its own check indicator as well.
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            item.setData(CHECK_ROLE, bool(default_checked))
            row = ImportRow(f"{i:02d}. {entry.get('title', '')}", meta, "B站")
            row.set_checked(default_checked)
            row.toggled.connect(lambda checked, it=item: it.setData(CHECK_ROLE, bool(checked)))
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
            self._rows.append((item, row))
            item.setToolTip(entry.get("title", ""))
        self.list.blockSignals(False)
        if self.hint is not None:
            if len(entries) > 25:
                self.hint.setText("项目较多，默认没有勾选。请自己选择，或点「全选」下载这个范围的全部片段。")
            else:
                self.hint.setText("")
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setText(self._scope_caption(self._data, scope))
        self._refresh_summary()

    def _set_all(self, state) -> None:
        checked = state == Qt.Checked
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setData(CHECK_ROLE, checked)
        for _item, row in self._rows:
            row.set_checked(checked)
        self.list.blockSignals(False)
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        total = self.list.count()
        checked = sum(1 for i in range(total) if self.list.item(i).data(CHECK_ROLE))
        self.summary.setText(f"已选 {checked}/{total} 段")

    def _accept_selection(self) -> None:
        self.selected_urls = [
            str(self.list.item(i).data(Qt.UserRole) or "")
            for i in range(self.list.count())
            if self.list.item(i).data(CHECK_ROLE)
        ]
        if not self.selected_urls:
            self.summary.setText("至少选一段，或者点「取消」。")
            return
        self.accept()


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
        self._probe_worker: ProbeThread | None = None
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
            "搜索 B 站公开视频，选中后下载音频并转换为 192kbps MP3；也可以直接粘贴视频或合集链接。"
            "如果链接是一个合集（多 P / UP 主合集），会先让你勾选要下载哪几段。只用于个人本地试听。"
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
        self.results.setMinimumHeight(150)
        self.results.setStyleSheet(result_list_style())
        self.results.itemDoubleClicked.connect(self._import_selected)
        self.body.addWidget(self.results, 1)
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
        line.setStyleSheet(f"background: {theme.mix(theme.GOLD, theme.PANEL, 0.7).name()}; border: none;")
        self.body.addWidget(line)

        # direct URL
        link_row = QHBoxLayout()
        link_row.setSpacing(6)
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("粘贴 Bilibili / YouTube 等视频或合集链接")
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
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.body.addWidget(self.status)

        self.footer.addStretch(1)
        close = self.add_button("关闭")
        close.clicked.connect(self.reject)
        if not ready:
            for w in (self.search_btn, self.import_selected_btn, self.url_btn, self.local_btn):
                w.setEnabled(False)

    def _set_busy(self, busy: bool, label: str = "") -> None:
        for widget in (self.search_btn, self.import_selected_btn, self.url_btn, self.local_btn):
            widget.setEnabled(not busy)
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
        self._probe_then_import(url)

    def _import_url(self) -> None:
        url = self.url_edit.text().strip()
        if not url.startswith(("http://", "https://")):
            self.status.setText("请粘贴完整视频链接（http/https）。")
            return
        self._probe_then_import(url)

    # ------------------------------------------------------------------ probing
    def _probe_then_import(self, url: str) -> None:
        if self._import_worker and self._import_worker.isRunning():
            return
        if self._probe_worker and self._probe_worker.isRunning():
            return
        self._set_busy(True, "正在解析链接，确认是不是合集…")
        worker = ProbeThread(url, self)
        worker.ok.connect(lambda data: self._on_probed(url, data))
        worker.failed.connect(lambda message: self._on_probe_failed(url, message))
        worker.finished.connect(lambda: self._set_busy(False))
        self._probe_worker = worker
        worker.start()

    def _on_probed(self, url: str, data: dict) -> None:
        entries = data.get("entries") or []
        if data.get("kind") == "collection" and len(entries) > 1:
            dialog = CollectionDialog(self, data)
            if dialog.exec_() != QDialog.Accepted or not dialog.selected_urls:
                self.status.setText("已取消，没有下载。")
                return
            self._start_import(dialog.selected_urls)
            return
        self._start_import([url])

    def _on_probe_failed(self, url: str, message: str) -> None:
        # Probing is best-effort: if it fails we still try the plain download.
        self._start_import([url])

    # ------------------------------------------------------------------ importing
    def _start_import(self, urls) -> None:
        if isinstance(urls, str):
            urls = [urls]
        urls = [u for u in urls if u]
        if not urls:
            return
        if self._import_worker and self._import_worker.isRunning():
            return
        label = "正在连接视频…" if len(urls) == 1 else f"正在下载 {len(urls)} 段音频…"
        self._set_busy(True, label)
        self.progress.setValue(0.02)
        worker = ImportThread(urls, self.output_dir, self)
        worker.progress.connect(self._on_progress)
        worker.done.connect(self._on_done)
        worker.failed.connect(self._on_failed)
        worker.skipped.connect(self._on_skipped)
        worker.finished.connect(lambda: self._set_busy(False))
        self._import_worker = worker
        worker.start()

    def _on_progress(self, pct: int, text: str) -> None:
        self.progress.setValue(max(0.01, min(1.0, pct / 100)), animate=True)
        self.status.setText(text)

    def _on_done(self, paths) -> None:
        paths = list(paths or [])
        self.progress.setValue(1.0, animate=True)
        self.status.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        if len(paths) == 1:
            self.status.setText(f"已保存：{Path(paths[0]).name}")
        else:
            self.status.setText(f"已保存 {len(paths)} 首，最后一首：{Path(paths[-1]).name}")
        for path in paths:
            self.imported.emit(path)
        self._set_busy(False)

    def _on_skipped(self, message: str) -> None:
        # Partial success: the saved songs are kept, the broken links are listed.
        self.progress.setValue(1.0, animate=True)
        self.status.setText(message)
        self.status.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")

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
        worker.done.connect(lambda p: self._on_done([p]))
        worker.failed.connect(self._on_failed)
        worker.finished.connect(lambda: self._set_busy(False))
        self._convert_worker = worker
        worker.start()

    def _wait_workers(self) -> None:
        for worker in (
            self._search_worker,
            self._probe_worker,
            self._import_worker,
            self._convert_worker,
        ):
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
