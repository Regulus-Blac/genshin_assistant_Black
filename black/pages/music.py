from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt5.QtGui import QColor, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..music_service import MusicEngine, Playable, SearchThread, Track, scan_folder
from ..stage import ElidedLabel
from ..widgets import Divider, IconButton, ProgressBar
from .music_import import MusicImportDialog

_ORPHAN_SEARCHES: list[SearchThread] = []


def ms_text(ms: int) -> str:
    if ms <= 0:
        return "0:00"
    seconds = int(ms // 1000)
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


class AlbumArt(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self._title = "Black"
        self._playing = False
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(60)
        self._timer.timeout.connect(self._tick)

    def set_track(self, title: str, playing: bool) -> None:
        self._title = title or "Black"
        self.set_playing(playing)
        self.update()

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        if playing and not self._timer.isActive():
            self._timer.start()
        elif not playing:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 0.6) % 360
        self.update()

    def _palette(self) -> tuple[QColor, QColor]:
        h = int(hashlib.md5(self._title.encode("utf-8")).hexdigest()[:4], 16)
        choices = [
            ("#1f4c58", "#79d0cf"),
            ("#3e3358", "#bca5e6"),
            ("#4f4028", "#e0be7d"),
            ("#263d4b", "#87b7d7"),
            ("#4a3238", "#dda1a0"),
        ]
        a, b = choices[h % len(choices)]
        return QColor(a), QColor(b)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0, 0, self.width(), self.height())
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        p.setClipPath(path)
        dark, bright = self._palette()
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, dark)
        grad.setColorAt(0.7, theme.mix(dark, "#0a1019", 0.45))
        grad.setColorAt(1, QColor(theme.mix(bright, dark, 0.5)))
        p.fillRect(rect, grad)

        # a little starfield / vinyl grooves
        c = rect.center()
        p.save()
        p.translate(c)
        p.rotate(self._angle)
        p.setBrush(Qt.NoBrush)
        for i in range(4, 0, -1):
            p.setPen(QPen(QColor(bright.red(), bright.green(), bright.blue(), 20 + i * 10), 0.9))
            p.drawEllipse(QPointF(0, 0), 18 + i * 8, 18 + i * 8)
        p.restore()

        # central sigil
        p.setPen(QPen(QColor(255, 245, 220, 170), 1.2))
        p.setBrush(QColor(8, 13, 20, 180))
        p.drawEllipse(c, 18, 18)
        theme.draw_star(p, c, 9, QColor(theme.GOLD_BRIGHT))
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 244, 213, 60), 1))
        p.drawEllipse(c, 24, 24)

        # corner light
        glow = QRadialGradient(QPointF(21, 18), 34)
        glow.setColorAt(0, QColor(255, 250, 230, 80))
        glow.setColorAt(1, QColor(255, 250, 230, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(21, 18), 34, 34)
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 241, 205, 45), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 13, 13)


class TrackRow(QWidget):
    def __init__(
        self,
        title: str,
        subtitle: str,
        badge: str,
        badge_color: str = theme.GOLD_SOFT,
        meta: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(48)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 8, 4)
        lay.setSpacing(9)
        note = QLabel()
        note.setPixmap(theme.icon("music", badge_color, 15).pixmap(15, 15))
        note.setFixedWidth(18)
        lay.addWidget(note, 0, Qt.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(0)
        self.title = ElidedLabel(title)
        self.title.setStyleSheet(f"font-size: 12px; color: {theme.TEXT};")
        self.sub = ElidedLabel(subtitle)
        self.sub.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        col.addWidget(self.title)
        col.addWidget(self.sub)
        lay.addLayout(col, 1)
        if meta:
            m = QLabel(meta)
            m.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
            lay.addWidget(m, 0, Qt.AlignVCenter)
        chip = QLabel(badge)
        chip.setStyleSheet(
            f"font-size: 8px; color: {badge_color}; background: rgba(217,188,125,10); "
            "border: 1px solid rgba(217,188,125,28); border-radius: 7px; padding: 2px 5px;"
        )
        lay.addWidget(chip, 0, Qt.AlignVCenter)


class MusicPage(QWidget):
    def __init__(self, store, engine: MusicEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.engine = engine
        self._seeking = False
        self._search_thread: SearchThread | None = None
        self._local_paths: list[Path] = []
        self._online_tracks: list[Track] = []
        self._build()
        self.engine.state_changed.connect(self._on_state)
        self.engine.track_changed.connect(self._on_track)
        self.engine.position_changed.connect(self._on_position)
        self.engine.loading_changed.connect(self._on_loading)
        self.engine.error_occurred.connect(self._on_error)
        self.engine.queue_changed.connect(self._on_queue_changed)
        self.engine.set_volume(int(self.store.settings.get("music_volume", 42) or 42))
        self.volume_slider.setValue(self.engine.volume)
        self.load_local(initial=True)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 2, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("乐音")
        title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 26px; font-weight: 600; color: {theme.TEXT}; letter-spacing: 2px;"
        )
        sub = QLabel("让风替你翻页，也让音乐替你守住这一小段安静。")
        sub.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        header.addLayout(title_box)
        header.addStretch(1)
        self.import_quick = QPushButton("导入音乐")
        self.import_quick.setObjectName("Ghost")
        self.import_quick.setCursor(Qt.PointingHandCursor)
        self.import_quick.setFixedHeight(30)
        self.import_quick.setToolTip("从 Bilibili 链接或搜索下载并转为 MP3")
        self.import_quick.clicked.connect(self.open_import_dialog)
        header.addWidget(self.import_quick, 0, Qt.AlignBottom)
        self.folder_quick = QPushButton("打开音乐文件夹")
        self.folder_quick.setObjectName("Ghost")
        self.folder_quick.setCursor(Qt.PointingHandCursor)
        self.folder_quick.setFixedHeight(30)
        self.folder_quick.clicked.connect(self.open_music_folder)
        header.addWidget(self.folder_quick, 0, Qt.AlignBottom)
        root.addLayout(header)
        root.addSpacing(12)

        # now playing -------------------------------------------------------
        now = QFrame()
        now.setObjectName("NowPlaying")
        now.setStyleSheet(
            "QFrame#NowPlaying { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 rgba(27,42,59,235), stop:1 rgba(13,21,31,235)); "
            "border: 1px solid rgba(217,188,125,48); border-radius: 14px; }"
        )
        nl = QHBoxLayout(now)
        nl.setContentsMargins(14, 12, 14, 12)
        nl.setSpacing(14)
        self.album = AlbumArt()
        nl.addWidget(self.album, 0, Qt.AlignTop)
        mid = QVBoxLayout()
        mid.setSpacing(3)
        self.now_title = ElidedLabel("还没有开始播放")
        self.now_title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 18px; font-weight: 600; color: {theme.TEXT};"
        )
        self.now_sub = ElidedLabel("从本地曲库或在线寻音里选一首吧。")
        self.now_sub.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        mid.addWidget(self.now_title)
        mid.addWidget(self.now_sub)
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        self.source_label = QLabel("BGM")
        self.source_label.setStyleSheet(
            f"font-size: 8px; color: {theme.GOLD_SOFT}; background: rgba(217,188,125,12); "
            "border: 1px solid rgba(217,188,125,30); border-radius: 7px; padding: 1px 6px;"
        )
        status_row.addWidget(self.source_label)
        mid.addLayout(status_row)
        self.progress = QSlider(Qt.Horizontal)
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setMinimumHeight(18)
        self.progress.setCursor(Qt.PointingHandCursor)
        self.progress.sliderPressed.connect(self._on_seek_start)
        self.progress.sliderReleased.connect(self._on_seek_end)
        self.progress.valueChanged.connect(self._on_slider_value)
        mid.addWidget(self.progress)
        times = QHBoxLayout()
        self.time_now = QLabel("0:00")
        self.time_now.setStyleSheet(f"font-family: '{theme.MONO}'; font-size: 9px; color: {theme.FAINT};")
        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet(f"font-family: '{theme.MONO}'; font-size: 9px; color: {theme.FAINT};")
        times.addWidget(self.time_now)
        times.addStretch(1)
        times.addWidget(self.time_total)
        mid.addLayout(times)
        nl.addLayout(mid, 1)

        right = QVBoxLayout()
        right.setSpacing(4)
        controls = QHBoxLayout()
        controls.setSpacing(2)
        self.prev_btn = IconButton("prev", "上一首", size=14, button_size=30, color=theme.MUTED)
        self.play_btn = QToolButton()
        self.play_btn.setObjectName("Play")
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setIcon(theme.icon("play", "#1c1810", 17))
        self.play_btn.setIconSize(QSize(17, 17))
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setToolTip("播放 / 暂停")
        self.play_btn.clicked.connect(self.engine.toggle)
        self.next_btn = IconButton("next", "下一首", size=14, button_size=30, color=theme.MUTED)
        self.prev_btn.clicked.connect(self.engine.previous)
        self.next_btn.clicked.connect(self.engine.next)
        controls.addStretch(1)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch(1)
        right.addLayout(controls)
        mode = QHBoxLayout()
        mode.setSpacing(3)
        self.repeat_btn = self._small_toggle("repeat", "循环模式")
        self.repeat_btn.clicked.connect(self._cycle_repeat)
        self.shuffle_btn = self._small_toggle("shuffle", "随机播放")
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        # MusicEngine defaults to list repeat; reflect that in the control.
        self.repeat_btn.setChecked(True)
        self.repeat_btn.setIcon(theme.icon("repeat", theme.GOLD, 13))
        self.repeat_btn.setToolTip("列表循环")
        mode.addStretch(1)
        mode.addWidget(self.repeat_btn)
        mode.addWidget(self.shuffle_btn)
        mode.addStretch(1)
        right.addLayout(mode)
        volume_row = QHBoxLayout()
        volume_row.setSpacing(4)
        vol = QLabel()
        vol.setPixmap(theme.icon("volume", theme.MUTED, 13).pixmap(13, 13))
        volume_row.addWidget(vol)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(78)
        self.volume_slider.setCursor(Qt.PointingHandCursor)
        self.volume_slider.valueChanged.connect(self._on_volume)
        self.volume_slider.sliderReleased.connect(self._save_volume)
        volume_row.addWidget(self.volume_slider)
        right.addLayout(volume_row)
        nl.addLayout(right, 0)
        root.addWidget(now)
        root.addSpacing(10)

        # library tabs ------------------------------------------------------
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            """
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: transparent; color: #a89d8b; padding: 8px 16px;
                border-bottom: 1px solid transparent; font-family: 'Noto Serif SC'; font-size: 12px;
            }
            QTabBar::tab:selected { color: #d9bc7d; border-bottom: 1px solid rgba(217,188,125,110); }
            QTabBar::tab:hover { color: #eee7da; }
            """
        )
        local_tab = QWidget()
        ltl = QVBoxLayout(local_tab)
        ltl.setContentsMargins(0, 8, 0, 0)
        ltl.setSpacing(6)
        local_top = QHBoxLayout()
        local_top.setSpacing(6)
        folder_icon = QLabel()
        folder_icon.setPixmap(theme.icon("folder", theme.GOLD_SOFT, 14).pixmap(14, 14))
        local_top.addWidget(folder_icon)
        self.folder_label = ElidedLabel(str(self.store.settings.get("music_folder", "")))
        self.folder_label.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        local_top.addWidget(self.folder_label, 1)
        choose = QPushButton("选择文件夹")
        choose.setObjectName("TextButton")
        choose.setCursor(Qt.PointingHandCursor)
        choose.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        choose.clicked.connect(self.choose_folder)
        rescan = QPushButton("重新扫描")
        rescan.setObjectName("TextButton")
        rescan.setCursor(Qt.PointingHandCursor)
        rescan.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        rescan.clicked.connect(lambda: self.load_local(initial=False))
        local_top.addWidget(choose)
        local_top.addWidget(rescan)
        ltl.addLayout(local_top)
        self.local_list = QListWidget()
        self.local_list.setSpacing(1)
        self.local_list.itemDoubleClicked.connect(self._play_local_item)
        ltl.addWidget(self.local_list, 1)
        self.local_empty = QLabel("这个文件夹里还没有音频。把 mp3 / wav / flac / m4a 放进来，或选择别的文件夹。")
        self.local_empty.setStyleSheet(f"font-size: 10px; color: {theme.FAINT}; padding: 16px;")
        self.local_empty.setAlignment(Qt.AlignCenter)
        ltl.addWidget(self.local_empty)
        local_foot = QHBoxLayout()
        self.local_count = QLabel("0 首")
        self.local_count.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        local_foot.addWidget(self.local_count)
        local_foot.addStretch(1)
        hint = QLabel("双击曲目开始播放 · 支持 BGM 后台播放")
        hint.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        local_foot.addWidget(hint)
        ltl.addLayout(local_foot)
        self.tabs.addTab(local_tab, "本地曲库")

        online_tab = QWidget()
        otl = QVBoxLayout(online_tab)
        otl.setContentsMargins(0, 8, 0, 0)
        otl.setSpacing(6)
        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索原神 OST、钢琴、久石让、周杰伦……")
        self.search_edit.returnPressed.connect(self.search_online)
        search_row.addWidget(self.search_edit, 1)
        self.search_btn = QPushButton("寻音")
        self.search_btn.setObjectName("Primary")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedHeight(34)
        self.search_btn.clicked.connect(self.search_online)
        search_row.addWidget(self.search_btn)
        otl.addLayout(search_row)
        self.search_status = QLabel("网易云提供完整音源，iTunes 提供 30 秒试听；需要联网。")
        self.search_status.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        otl.addWidget(self.search_status)
        self.online_list = QListWidget()
        self.online_list.setSpacing(1)
        self.online_list.itemDoubleClicked.connect(self._play_online_item)
        otl.addWidget(self.online_list, 1)
        online_foot = QHBoxLayout()
        foot_hint = QLabel("在线曲目会自动缓存到本地 · 仅供个人学习时聆听")
        foot_hint.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        online_foot.addWidget(foot_hint)
        online_foot.addStretch(1)
        self.cache_hint = QLabel("")
        self.cache_hint.setStyleSheet(f"font-size: 9px; color: {theme.GOLD_SOFT};")
        online_foot.addWidget(self.cache_hint)
        otl.addLayout(online_foot)
        self.tabs.addTab(online_tab, "在线寻音")
        root.addWidget(self.tabs, 1)

    def _small_toggle(self, name: str, tip: str) -> QToolButton:
        btn = QToolButton()
        btn.setCheckable(True)
        btn.setIcon(theme.icon(name, theme.MUTED, 13))
        btn.setIconSize(QSize(13, 13))
        btn.setFixedSize(24, 24)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(tip)
        btn.setStyleSheet("QToolButton { border-radius: 6px; } QToolButton:hover { background: rgba(217,188,125,25); }")
        return btn

    # ------------------------------------------------------------------ local
    def load_local(self, *, initial: bool = False) -> None:
        folder = str(self.store.settings.get("music_folder", "") or "")
        self.folder_label.setText(folder)
        self.folder_label.setToolTip(folder)
        paths = scan_folder(folder)
        self._local_paths = paths
        self.local_list.clear()
        for p in paths:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, str(p))
            subtitle = "Black 原声 · 环境乐" if "assets" in str(p).lower() else str(p.parent.name)
            row = TrackRow(
                p.stem,
                subtitle,
                p.suffix.lstrip(".").upper(),
                badge_color=theme.TEAL,
                meta=f"{p.stat().st_size/1024/1024:.1f} MB" if p.exists() else "",
            )
            item.setSizeHint(QSize(10, 50))
            self.local_list.addItem(item)
            self.local_list.setItemWidget(item, row)
        self.local_count.setText(f"{len(paths)} 首")
        self.local_empty.setVisible(not paths)
        self.local_list.setVisible(bool(paths))
        if paths and not self.engine.current_playable():
            self.now_title.setText(paths[0].stem)
            self.now_sub.setText("本地曲库 · 双击曲目开始播放")
            self.album.set_track(paths[0].stem, False)
        if paths and initial and self.store.settings.get("auto_play_bgm"):
            self.engine.play_queue(
                [Playable(title=p.stem, subtitle="本地曲库", path=p) for p in paths],
                0,
            )

    def choose_folder(self) -> None:
        current = str(self.store.settings.get("music_folder", "") or "")
        folder = QFileDialog.getExistingDirectory(self.window(), "选择本地音乐文件夹", current)
        if folder:
            self.store.update_settings(music_folder=folder)
            self.load_local(initial=False)

    def open_music_folder(self) -> None:
        folder = Path(str(self.store.settings.get("music_folder", "") or ""))
        if folder.exists():
            import os

            os.startfile(str(folder))  # noqa: S606
        else:
            self.choose_folder()

    def open_import_dialog(self) -> None:
        dialog = MusicImportDialog(self.window(), self.store)
        dialog.imported.connect(self._on_imported)
        dialog.exec_()

    def _on_imported(self, path: str) -> None:
        self.load_local(initial=False)
        try:
            index = self._local_paths.index(Path(path))
        except ValueError:
            return
        items = [Playable(title=p.stem, subtitle="本地曲库", path=p) for p in self._local_paths]
        self.engine.play_queue(items, index)
        self._select_local_index(index)

    def _play_local_item(self, item: QListWidgetItem) -> None:
        path = Path(str(item.data(Qt.UserRole)))
        try:
            index = self._local_paths.index(path)
        except ValueError:
            index = 0
        items = [Playable(title=p.stem, subtitle="本地曲库", path=p) for p in self._local_paths]
        self.engine.play_queue(items, index)
        self._select_local_index(index)

    def _select_local_index(self, index: int) -> None:
        if 0 <= index < self.local_list.count():
            self.local_list.blockSignals(True)
            self.local_list.setCurrentRow(index)
            self.local_list.blockSignals(False)

    # ------------------------------------------------------------------ online
    def search_online(self) -> None:
        query = self.search_edit.text().strip()
        if not query:
            self.search_status.setText("先写下想听的歌名或关键词。")
            self.search_edit.setFocus()
            return
        if self._search_thread and self._search_thread.isRunning():
            return
        self.search_btn.setEnabled(False)
        self.search_btn.setText("寻音中…")
        self.search_status.setText("正在连接提瓦特之外的音源，请稍等…")
        self.online_list.clear()
        thread = SearchThread(query, self)
        thread.ok.connect(self._on_search_ok)
        thread.failed.connect(self._on_search_failed)
        thread.finished.connect(lambda: self._set_searching(False))
        self._search_thread = thread
        thread.start()

    def _set_searching(self, value: bool) -> None:
        self.search_btn.setEnabled(not value)
        self.search_btn.setText("寻音" if not value else "寻音中…")

    def _on_search_ok(self, tracks: list) -> None:
        self._online_tracks = list(tracks)
        self.online_list.clear()
        for t in self._online_tracks:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, t.key)
            item.setSizeHint(QSize(10, 50))
            badge = "网易云" if t.source == "netease" else "iTunes 试听"
            color = "#8fd0a0" if t.source == "netease" else "#85bfe0"
            row = TrackRow(
                t.title,
                t.subtitle,
                badge,
                badge_color=color,
                meta=ms_text(t.duration * 1000) if t.duration else "",
            )
            self.online_list.addItem(item)
            self.online_list.setItemWidget(item, row)
        count = len(tracks)
        self.search_status.setText(f"找到 {count} 首。双击播放；在线曲目会在首次播放时缓存。")
        self._set_searching(False)

    def _on_search_failed(self, message: str) -> None:
        self.search_status.setText(message)
        self._set_searching(False)

    def _play_online_item(self, item: QListWidgetItem) -> None:
        key = str(item.data(Qt.UserRole))
        index = 0
        for i, t in enumerate(self._online_tracks):
            if t.key == key:
                index = i
                break
        items = [
            Playable(title=t.title, subtitle=t.subtitle, track=t, duration=t.duration)
            for t in self._online_tracks
        ]
        self.engine.play_queue(items, index)
        self._online_selection = index

    # ------------------------------------------------------------------ engine events
    def _on_state(self, playing: bool) -> None:
        self.play_btn.setIcon(theme.icon("pause" if playing else "play", "#1c1810", 17))
        self.album.set_playing(playing)
        if not playing:
            self.progress.setEnabled(True)

    def _on_track(self, title: str, subtitle: str, kind: str, playing: bool) -> None:
        self.now_title.setText(title)
        self.now_sub.setText(subtitle)
        item = self.engine.current_playable()
        if item and item.track:
            self.source_label.setText("在线 · 网易云" if item.track.source == "netease" else "在线 · iTunes 试听")
        else:
            self.source_label.setText("本地 BGM")
        self.album.set_track(title, playing)
        if kind == "online":
            self.cache_hint.setText("首次播放在本地生成缓存")
        else:
            self.cache_hint.setText("")

    def _on_position(self, pos: int, duration: int) -> None:
        self.time_total.setText(ms_text(duration))
        if not self._seeking:
            self.time_now.setText(ms_text(pos))
            if duration > 0:
                self.progress.blockSignals(True)
                self.progress.setValue(int(pos / duration * 1000))
                self.progress.blockSignals(False)

    def _on_slider_value(self, value: int) -> None:
        if self._seeking:
            # show the target time while dragging
            duration = self.engine.player.duration()
            self.time_now.setText(ms_text(int(duration * value / 1000)))

    def _on_seek_start(self) -> None:
        self._seeking = True

    def _on_seek_end(self) -> None:
        self._seeking = False
        duration = self.engine.player.duration()
        if duration > 0:
            self.engine.seek(int(duration * self.progress.value() / 1000))

    def _on_loading(self, loading: bool, text: str) -> None:
        if loading:
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"font-size: 9px; color: {theme.GOLD_SOFT};")
        else:
            self.status_label.setText("已就绪")
            self.status_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")

    def _on_error(self, message: str) -> None:
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"font-size: 9px; color: {theme.RED};")
        self.play_btn.setIcon(theme.icon("play", "#1c1810", 17))
        self.album.set_playing(False)

    def _on_queue_changed(self) -> None:
        item = self.engine.current_playable()
        if not item:
            return
        if item.track:
            # selected online row, if it is in current results
            for i in range(self.online_list.count()):
                list_item = self.online_list.item(i)
                if list_item.data(Qt.UserRole) == item.track.key:
                    self.online_list.blockSignals(True)
                    self.online_list.setCurrentItem(list_item)
                    self.online_list.blockSignals(False)
                    break
        else:
            for i in range(self.local_list.count()):
                list_item = self.local_list.item(i)
                if list_item.data(Qt.UserRole) == str(item.path):
                    self.local_list.blockSignals(True)
                    self.local_list.setCurrentItem(list_item)
                    self.local_list.blockSignals(False)
                    break

    # ------------------------------------------------------------------ volume/modes
    def _on_volume(self, value: int) -> None:
        self.engine.set_volume(value)

    def _save_volume(self) -> None:
        self.store.settings["music_volume"] = int(self.volume_slider.value())
        self.store.save()

    def _cycle_repeat(self) -> None:
        self.engine.repeat_mode = (self.engine.repeat_mode + 1) % 3
        labels = {0: "顺序播放", 1: "列表循环", 2: "单曲循环"}
        self.repeat_btn.setToolTip(labels[self.engine.repeat_mode])
        self.repeat_btn.setIcon(
            theme.icon("repeat", theme.GOLD if self.engine.repeat_mode else theme.MUTED, 13)
        )
        self.repeat_btn.setChecked(self.engine.repeat_mode != 0)

    def _toggle_shuffle(self) -> None:
        self.engine.shuffle = not self.engine.shuffle
        self.shuffle_btn.setChecked(self.engine.shuffle)
        self.shuffle_btn.setIcon(theme.icon("shuffle", theme.GOLD if self.engine.shuffle else theme.MUTED, 13))

    def start_default(self) -> None:
        folder = str(self.store.settings.get("music_folder", "") or "")
        if not self.engine.current_playable():
            paths = scan_folder(folder)
            if paths:
                self.engine.play_queue(
                    [Playable(title=p.stem, subtitle="本地曲库", path=p) for p in paths],
                    0,
                )
                return
        self.engine.ensure_playing(folder)

    def toggle_playback(self) -> None:
        if self.engine.current_playable():
            self.engine.toggle()
        else:
            self.start_default()

    def next_track(self) -> None:
        if self.engine.queue:
            self.engine.next()
        else:
            self.start_default()

    def shutdown(self) -> None:
        thread = self._search_thread
        if thread and thread.isRunning():
            thread.wait(1500)
            if thread.isRunning():
                thread.setParent(None)
                _ORPHAN_SEARCHES.append(thread)
                self._search_thread = None
