from __future__ import annotations

import hashlib
import math
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QCursor, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSlider,
    QStyle,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..dialogs import ConfirmDialog, GenshinDialog, InputDialog, NoticeDialog
from ..music_service import MusicEngine, Playable, SearchThread, Track, save_track_to_folder, scan_folder
from ..stage import ElidedLabel
from ..widgets import Divider, IconButton, ProgressBar
from .music_import import MusicImportDialog

_ORPHAN_SEARCHES: list[SearchThread] = []


class _CopyTrackThread(QThread):
    """Download a cached online track and copy it into the local music folder."""

    done = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, track: Track, folder: Path, parent=None) -> None:
        super().__init__(parent)
        self.track = track
        self.folder = folder

    def run(self) -> None:
        try:
            self.done.emit(str(save_track_to_folder(self.track, self.folder)))
        except Exception as exc:  # noqa: BLE001 - surfaced in the dialog
            self.failed.emit(str(exc))


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

    def pause_animation(self) -> None:
        """Freeze the spinning record (used while the window is being resized)."""
        self._timer.stop()

    def resume_animation(self) -> None:
        if self._playing and not self._timer.isActive():
            self._timer.start()

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
        *,
        show_handle: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedHeight(48)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 8, 4)
        lay.setSpacing(9)
        if show_handle:
            handle = QLabel("⋮⋮")
            handle.setToolTip("拖动调整顺序")
            handle.setStyleSheet(f"font-size: 14px; color: {theme.GOLD_SOFT}; letter-spacing: -2px;")
            handle.setFixedWidth(17)
            lay.addWidget(handle, 0, Qt.AlignVCenter)
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


class SeekSlider(QSlider):
    """A progress slider that seeks to the exact clicked position.

    QSlider's default groove click moves by a page step instead of the clicked
    point, which made the progress bar feel like drag-only.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setCursor(Qt.PointingHandCursor)

    def _value_at(self, x: int) -> int:
        return QStyle.sliderValueFromPosition(
            self.minimum(), self.maximum(), int(x), max(1, self.width() - 1), upsideDown=False
        )

    def _seek_at(self, x: int) -> None:
        value = self._value_at(x)
        if value != self.value():
            self.setValue(value)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and self.maximum() > self.minimum():
            self.setSliderDown(True)
            self._seek_at(event.pos().x())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self.isSliderDown() and event.buttons() & Qt.LeftButton:
            self._seek_at(event.pos().x())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if self.isSliderDown() and event.button() == Qt.LeftButton:
            self._seek_at(event.pos().x())
            self.setSliderDown(False)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class PlaylistList(QListWidget):
    reordered = pyqtSignal()

    def dropEvent(self, event) -> None:  # noqa: N802
        super().dropEvent(event)
        if self.dragDropMode() != QAbstractItemView.NoDragDrop:
            self.reordered.emit()


class PlaylistAddDialog(GenshinDialog):
    """Browse every playlist and add songs in batch with check boxes."""

    def __init__(self, parent, target_name: str, sources: list[dict], add_callback) -> None:
        super().__init__(
            parent,
            "添加歌曲",
            f"勾选要加入「{target_name}」的歌曲，可以一次加入多首。",
            width=760,
        )
        self._sources = sources
        self._add_callback = add_callback
        self._current_source = 0
        self._target_name = target_name

        row = QHBoxLayout()
        row.setSpacing(10)
        left_col = QVBoxLayout()
        left_col.setSpacing(5)
        left_title = QLabel("来源")
        left_title.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        left_col.addWidget(left_title)
        self.source_list = QListWidget()
        self.source_list.setFixedWidth(200)
        self.source_list.setMinimumHeight(320)
        self.source_list.currentRowChanged.connect(self._show_source)
        left_col.addWidget(self.source_list)
        row.addLayout(left_col, 0)

        right_col = QVBoxLayout()
        right_col.setSpacing(5)
        self.song_title = QLabel("歌曲")
        self.song_title.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        right_col.addWidget(self.song_title)
        self.song_list = QListWidget()
        self.song_list.setMinimumHeight(320)
        self.song_list.setStyleSheet(
            f"QListWidget {{ background: {theme.PANEL2}; border: 1px solid "
            f"{theme.mix(theme.GOLD, theme.PANEL, 0.55).name()}; border-radius: 8px; }}"
            f"QListWidget::item {{ min-height: 42px; padding: 3px 8px; }}"
        )
        self.song_list.itemClicked.connect(self._toggle_item)
        right_col.addWidget(self.song_list, 1)

        tools = QHBoxLayout()
        tools.setSpacing(6)
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("全不选")
        for btn in (self.select_all_btn, self.select_none_btn):
            btn.setObjectName("TextButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
            tools.addWidget(btn)
        tools.addStretch(1)
        self.selection_label = QLabel("已选 0 首")
        self.selection_label.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        tools.addWidget(self.selection_label)
        right_col.addLayout(tools)
        row.addLayout(right_col, 1)
        self.body.addLayout(row)

        self.add_status = QLabel("勾选左侧方框选择歌曲，再点「加入选中歌曲」。")
        self.add_status.setWordWrap(True)
        self.add_status.setStyleSheet(f"font-size: 10px; color: {theme.FAINT};")
        self.body.addWidget(self.add_status)

        # Footer first: selecting a source builds the song list, which updates
        # the "加入选中歌曲" button through _refresh_selection.
        self.footer.addStretch(1)
        close = self.add_button("关闭")
        close.clicked.connect(self.accept)
        self.add_selected_btn = self.add_button("加入选中歌曲", primary=True)
        self.add_selected_btn.clicked.connect(self._add_checked)
        self.add_selected_btn.setEnabled(False)

        for source in sources:
            item = QListWidgetItem(f"{source['name']}  ·  {len(source['entries'])} 首")
            item.setData(Qt.UserRole, source["id"])
            self.source_list.addItem(item)
        if sources:
            self.source_list.setCurrentRow(0)

        self.select_all_btn.clicked.connect(lambda: self._set_all(Qt.Checked))
        self.select_none_btn.clicked.connect(lambda: self._set_all(Qt.Unchecked))
        self._refresh_selection()

    def _show_source(self, index: int) -> None:
        self.song_list.blockSignals(True)
        self.song_list.clear()
        if not (0 <= index < len(self._sources)):
            self.song_list.blockSignals(False)
            return
        source = self._sources[index]
        self._current_source = index
        self.song_title.setText(f"{source['name']} · {len(source['entries'])} 首")
        for entry in source["entries"]:
            kind = str(entry.get("kind", "local"))
            title = str(entry.get("title") or Path(str(entry.get("path", ""))).stem)
            subtitle = str(entry.get("subtitle") or ("本地曲库" if kind == "local" else "在线曲目"))
            item = QListWidgetItem(f"{title}\n{subtitle}")
            item.setData(Qt.UserRole, entry)
            item.setSizeHint(QSize(10, 46))
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.song_list.addItem(item)
        self.song_list.blockSignals(False)
        if not source["entries"]:
            placeholder = QListWidgetItem("这里还没有歌曲")
            placeholder.setFlags(Qt.NoItemFlags)
            self.song_list.addItem(placeholder)
        self._refresh_selection()

    def _toggle_item(self, item: QListWidgetItem) -> None:
        if not (item.flags() & Qt.ItemIsUserCheckable):
            return
        item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)
        self._refresh_selection()

    def _set_all(self, state) -> None:
        self.song_list.blockSignals(True)
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(state)
        self.song_list.blockSignals(False)
        self._refresh_selection()

    def _checked_entries(self) -> list[dict]:
        entries = []
        for i in range(self.song_list.count()):
            item = self.song_list.item(i)
            if item.checkState() == Qt.Checked:
                entry = item.data(Qt.UserRole)
                if isinstance(entry, dict):
                    entries.append(entry)
        return entries

    def _refresh_selection(self) -> None:
        count = len(self._checked_entries())
        self.selection_label.setText(f"已选 {count} 首")
        self.add_selected_btn.setText(f"加入选中歌曲（{count}）" if count else "加入选中歌曲")
        self.add_selected_btn.setEnabled(count > 0)

    def _add_checked(self) -> None:
        entries = self._checked_entries()
        if not entries:
            self.add_status.setText("先勾选要加入的歌曲。")
            return
        added = 0
        duplicated = 0
        for entry in entries:
            if self._add_callback(entry):
                added += 1
            else:
                duplicated += 1
        if added:
            self.add_status.setText(
                f"已加入 {added} 首到「{self._target_name}」"
                + (f"，{duplicated} 首已在歌单里被跳过。" if duplicated else "。")
            )
            self.add_status.setStyleSheet(f"font-size: 10px; color: {theme.GREEN};")
        else:
            self.add_status.setText("选中的歌曲都已经在这个歌单里了。")
            self.add_status.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        self._show_source(self._current_source)


class MusicPage(QWidget):
    def __init__(self, store, engine: MusicEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.engine = engine
        self._seeking = False
        self._search_thread: SearchThread | None = None
        self._copy_thread: _CopyTrackThread | None = None
        self._local_paths: list[Path] = []
        self._local_visible: list[Path] = []
        self._online_tracks: list[Track] = []
        self._current_playlist_id = ""
        self._playlist_entries: list[dict] = []
        self._playlist_mode = "browse"
        self._compact = False
        self._local_sort = False
        # Which list the player queue currently belongs to: ("playlist", id),
        # ("local",) or ("online", query).  Keeping it lets the play button,
        # next/previous and the three play modes follow the visible list.
        self._queue_source: tuple = ("local",)
        self.engine.set_play_mode(str(self.store.settings.get("music_mode", "sequence")))
        self._build()
        self.engine.state_changed.connect(self._on_state)
        self.engine.track_changed.connect(self._on_track)
        self.engine.position_changed.connect(self._on_position)
        self.engine.loading_changed.connect(self._on_loading)
        self.engine.error_occurred.connect(self._on_error)
        self.engine.queue_changed.connect(self._on_queue_changed)
        self.engine.mode_changed.connect(lambda _mode: self._update_mode_buttons())
        self.engine.set_volume(int(self.store.settings.get("music_volume", 42) or 42))
        self.engine.set_playback_rate(float(self.store.settings.get("music_rate", 1.0) or 1.0))
        self.volume_slider.setValue(self.engine.volume)
        self.load_local(initial=True)
        self._refresh_playlists()
        self._on_tab_changed(self.tabs.currentIndex())

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
        speed_label = QLabel("倍率")
        speed_label.setFixedWidth(28)
        speed_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        speed_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        status_row.addWidget(speed_label)
        self.speed_combo = QComboBox()
        self.speed_combo.setFixedWidth(120)
        self.speed_combo.setFixedHeight(26)
        self.speed_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.speed_combo.setStyleSheet(
            "QComboBox { padding: 1px 4px; } QComboBox::drop-down { width: 16px; border: none; }"
        )
        for label, rate in (("0.5x", 0.5), ("0.75x", 0.75), ("1.0x", 1.0), ("1.5x", 1.5), ("2.0x", 2.0)):
            self.speed_combo.addItem(label, rate)
        current_rate = float(self.store.settings.get("music_rate", 1.0) or 1.0)
        rate_idx = self.speed_combo.findData(current_rate)
        self.speed_combo.setCurrentIndex(rate_idx if rate_idx >= 0 else 2)
        self.speed_combo.setToolTip("音乐播放倍速")
        self.speed_combo.currentIndexChanged.connect(self._on_speed_changed)
        status_row.addWidget(self.speed_combo)
        mid.addLayout(status_row)
        self.progress = SeekSlider()
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
        self.play_btn.clicked.connect(self.toggle_playback)
        self.next_btn = IconButton("next", "下一首", size=14, button_size=30, color=theme.MUTED)
        self.prev_btn.clicked.connect(self.previous_track)
        self.next_btn.clicked.connect(self.next_track)
        controls.addStretch(1)
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch(1)
        right.addLayout(controls)
        mode = QHBoxLayout()
        mode.setSpacing(3)
        mode.addStretch(1)
        self.mode_buttons: dict[str, QToolButton] = {}
        for mode_id, icon_name, tip in (
            ("sequence", "order", "顺序播放"),
            ("shuffle", "shuffle", "随机播放"),
            ("single", "repeat-one", "单曲循环"),
        ):
            btn = self._small_toggle(icon_name, tip)
            btn.clicked.connect(lambda _checked=False, m=mode_id: self._set_play_mode(m))
            self.mode_buttons[mode_id] = btn
            mode.addWidget(btn)
        self.mode_text = QLabel("顺序播放")
        self.mode_text.setStyleSheet(f"font-size: 8px; color: {theme.MUTED};")
        mode.addWidget(self.mode_text)
        mode.addStretch(1)
        right.addLayout(mode)
        self._update_mode_buttons()
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

        # playlist bar (only shown on the 歌单 tab) ---------------------------
        plbar = QWidget()
        self.playlist_bar = plbar
        pl = QHBoxLayout(plbar)
        pl.setContentsMargins(0, 0, 0, 2)
        pl.setSpacing(6)
        pl_label = QLabel("歌单")
        pl_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 12px; font-weight: 600; color: {theme.GOLD};"
        )
        pl.addWidget(pl_label)
        self.playlist_combo = QComboBox()
        self.playlist_combo.setMinimumWidth(150)
        self.playlist_combo.setFixedHeight(34)
        # The shared QComboBox rule uses 8px vertical padding, which squeezed
        # the text inside a 30px box and clipped the glyph bottoms.
        self.playlist_combo.setStyleSheet(
            "QComboBox { padding: 4px 8px; } QComboBox::drop-down { width: 20px; border: none; }"
        )
        self.playlist_combo.setMaxVisibleItems(5)
        self.playlist_combo.currentIndexChanged.connect(self._on_playlist_changed)
        pl.addWidget(self.playlist_combo)
        self.playlist_count = QLabel("0 首")
        self.playlist_count.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        pl.addWidget(self.playlist_count)
        pl.addStretch(1)
        self.playlist_new_btn = QPushButton("+ 新建")
        self.playlist_rename_btn = QPushButton("重命名")
        self.playlist_delete_btn = QPushButton("删除")
        for btn in (self.playlist_new_btn, self.playlist_rename_btn, self.playlist_delete_btn):
            btn.setObjectName("TextButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
            pl.addWidget(btn)
        self.playlist_new_btn.clicked.connect(self._new_playlist)
        self.playlist_rename_btn.clicked.connect(self._rename_playlist)
        self.playlist_delete_btn.clicked.connect(self._delete_playlist)
        root.addWidget(plbar)

        # library tabs ------------------------------------------------------
        self.tabs = QTabWidget()
        tab_idle = theme.MUTED
        tab_hover = theme.TEXT
        self.tabs.setStyleSheet(
            f"""
            QTabWidget::pane {{ border: none; background: transparent; }}
            QTabBar::tab {{
                background: transparent; color: {tab_idle}; padding: 8px 16px;
                border-bottom: 1px solid transparent; font-family: '{theme.SERIF}'; font-size: 12px;
            }}
            QTabBar::tab:selected {{ color: {theme.GOLD}; border-bottom: 1px solid {theme.mix(theme.GOLD, theme.BG, 0.45).name()}; }}
            QTabBar::tab:hover {{ color: {tab_hover}; }}
            """
        )
        self.tabs.currentChanged.connect(self._on_tab_changed)
        playlist_tab = QWidget()
        ptl = QVBoxLayout(playlist_tab)
        ptl.setContentsMargins(0, 8, 0, 8)
        ptl.setSpacing(5)
        self.playlist_search = QLineEdit()
        self.playlist_search.setPlaceholderText("在歌单里搜索歌曲…")
        self.playlist_search.setClearButtonEnabled(True)
        self.playlist_search.setFixedHeight(30)
        self.playlist_search.textChanged.connect(lambda _text: self._refresh_playlist_tracks())
        ptl.addWidget(self.playlist_search)
        self.playlist_hint = QLabel("当前歌单")
        self.playlist_hint.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        ptl.addWidget(self.playlist_hint)
        self.playlist_list = PlaylistList()
        self.playlist_list.setSpacing(1)
        self.playlist_list.itemDoubleClicked.connect(self._play_playlist_item)
        self.playlist_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._playlist_context_menu)
        self.playlist_list.reordered.connect(self._on_playlist_reordered)
        self.playlist_list.itemChanged.connect(self._update_remove_count)
        ptl.addWidget(self.playlist_list, 1)
        self.playlist_empty = QLabel("这个歌单还没有歌。点「添加歌曲」从其他歌单里选几首吧。")
        self.playlist_empty.setWordWrap(True)
        self.playlist_empty.setAlignment(Qt.AlignCenter)
        self.playlist_empty.setStyleSheet(f"font-size: 10px; color: {theme.FAINT}; padding: 14px;")
        ptl.addWidget(self.playlist_empty)
        manage = QHBoxLayout()
        manage.setSpacing(8)
        self.playlist_sort_btn = QPushButton("排序")
        self.playlist_add_btn = QPushButton("添加歌曲")
        self.playlist_remove_btn = QPushButton("移除歌曲")
        light = theme.is_light()
        for btn in (self.playlist_sort_btn, self.playlist_add_btn, self.playlist_remove_btn):
            btn.setObjectName("TextButton")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                f"QPushButton {{ background: {'rgba(228,211,178,240)' if light else 'rgba(8,14,21,150)'}; "
                f"border: 1px solid {'rgba(120,88,36,165)' if light else 'rgba(217,188,125,42)'}; "
                f"border-radius: 8px; padding: 3px 13px; font-size: 11px; color: {'#4a3618' if light else theme.GOLD_SOFT}; }} "
                f"QPushButton:hover {{ background: {'#f1dfbf' if light else 'rgba(217,188,125,22)'}; "
                f"border-color: {theme.GOLD}; color: {'#2f2518' if light else theme.GOLD_BRIGHT}; }}"
            )
            manage.addWidget(btn)
        manage.addStretch(1)
        self.playlist_sort_btn.clicked.connect(lambda: self._set_playlist_mode("sort"))
        self.playlist_add_btn.clicked.connect(self._open_add_songs)
        self.playlist_remove_btn.clicked.connect(lambda: self._set_playlist_mode("remove"))
        ptl.addLayout(manage)

        self.remove_bar = QWidget()
        rbl = QHBoxLayout(self.remove_bar)
        rbl.setContentsMargins(0, 2, 0, 0)
        rbl.setSpacing(8)
        self.remove_count_label = QLabel("勾选要移除的歌曲")
        self.remove_count_label.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        rbl.addWidget(self.remove_count_label)
        rbl.addStretch(1)
        self.remove_cancel_btn = QPushButton("取消")
        self.remove_confirm_btn = QPushButton("确认移除")
        self.remove_confirm_btn.setObjectName("Primary")
        self.remove_cancel_btn.setMinimumWidth(66)
        self.remove_confirm_btn.setMinimumWidth(134)
        for btn in (self.remove_cancel_btn, self.remove_confirm_btn):
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            rbl.addWidget(btn)
        self.remove_cancel_btn.setStyleSheet(
            f"QPushButton {{ background: {'rgba(255,250,240,235)' if theme.is_light() else 'rgba(8,14,21,110)'}; "
            f"border: 1px solid {'rgba(152,117,54,75)' if theme.is_light() else 'rgba(217,188,125,60)'}; "
            f"border-radius: 8px; padding: 0 12px; color: {theme.TEXT_SOFT}; font-size: 12px; }} "
            f"QPushButton:hover {{ border-color: {theme.GOLD}; color: {theme.GOLD_BRIGHT}; }}"
        )
        self.remove_confirm_btn.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #efdfb4, stop:0.5 #d9bc7d, stop:1 #bfa063); border: 1px solid #f4e2b6; "
            "border-radius: 8px; padding: 0 14px; color: #201b12; font-size: 12px; font-weight: 600; } "
            "QPushButton:hover { background: #f4e3b8; }"
        )
        self.remove_cancel_btn.clicked.connect(lambda: self._set_playlist_mode("browse"))
        self.remove_confirm_btn.clicked.connect(self._confirm_remove_checked)
        self.remove_bar.setVisible(False)
        ptl.addWidget(self.remove_bar)
        self.tabs.addTab(playlist_tab, "歌单")

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
        self.local_add_btn = QPushButton("加入歌单")
        self.local_add_btn.setObjectName("TextButton")
        self.local_add_btn.setCursor(Qt.PointingHandCursor)
        self.local_add_btn.setStyleSheet(f"font-size: 10px; color: {theme.TEAL};")
        self.local_add_btn.clicked.connect(lambda: self._add_selected_local())
        local_top.addWidget(self.local_add_btn)
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
        self.local_search = QLineEdit()
        self.local_search.setPlaceholderText("在本地曲库里搜索歌曲…")
        self.local_search.setClearButtonEnabled(True)
        self.local_search.setFixedHeight(30)
        self.local_search.textChanged.connect(lambda _text: self._refresh_local_list())
        ltl.addWidget(self.local_search)
        local_tools = QHBoxLayout()
        local_tools.setSpacing(8)
        self.local_sort_btn = QPushButton("排序")
        self.local_sort_btn.setObjectName("TextButton")
        self.local_sort_btn.setCursor(Qt.PointingHandCursor)
        self.local_sort_btn.setFixedHeight(28)
        local_tools.addWidget(self.local_sort_btn)
        local_tools.addStretch(1)
        ltl.addLayout(local_tools)
        self.local_sort_btn.clicked.connect(self._toggle_local_sort)
        self.local_list = PlaylistList()
        self.local_list.setSpacing(1)
        self.local_list.itemDoubleClicked.connect(self._play_local_item)
        self.local_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.local_list.customContextMenuRequested.connect(self._local_context_menu)
        self.local_list.reordered.connect(self._on_local_reordered)
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
        explain = QLabel(
            "「在线寻音」= 即点即听：流式播放并自动缓存，不进入本地曲库。"
            "「导入音乐」= 永久下载：把 B 站/链接里的音频转成 MP3 存进本地曲库。"
            "想把在线曲目留下来，选中后点「下载到本地曲库」。"
        )
        explain.setWordWrap(True)
        explain.setStyleSheet(
            f"font-size: 9px; color: {theme.TEXT_SOFT}; background: {theme.mix(theme.GOLD, theme.BG, 0.9).name()}; "
            f"border: 1px solid {theme.mix(theme.GOLD, theme.BG, 0.72).name()}; border-radius: 8px; padding: 6px 9px;"
        )
        otl.addWidget(explain)
        online_actions = QHBoxLayout()
        online_actions.setSpacing(6)
        self.online_add_btn = QPushButton("加入歌单")
        self.online_add_btn.setObjectName("TextButton")
        self.online_add_btn.setCursor(Qt.PointingHandCursor)
        self.online_add_btn.setStyleSheet(f"font-size: 10px; color: {theme.TEAL};")
        self.online_add_btn.clicked.connect(self._add_selected_online)
        online_actions.addWidget(self.online_add_btn)
        self.online_download_btn = QPushButton("下载到本地曲库")
        self.online_download_btn.setObjectName("TextButton")
        self.online_download_btn.setCursor(Qt.PointingHandCursor)
        self.online_download_btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        self.online_download_btn.setToolTip("把选中的在线曲目下载并复制到本地音乐文件夹")
        self.online_download_btn.clicked.connect(self._download_selected_online)
        online_actions.addWidget(self.online_download_btn)
        online_actions.addStretch(1)
        otl.addLayout(online_actions)
        self.online_list = QListWidget()
        self.online_list.setSpacing(1)
        self.online_list.itemDoubleClicked.connect(self._play_online_item)
        self.online_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.online_list.customContextMenuRequested.connect(self._online_context_menu)
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

    def set_compact(self, compact: bool) -> None:
        compact = bool(compact)
        if compact == self._compact:
            return
        self._compact = compact
        if hasattr(self, "album"):
            self.album.setVisible(not compact)
        if hasattr(self, "playlist_count"):
            self.playlist_count.setVisible(not compact)
        if hasattr(self, "mode_text"):
            self.mode_text.setVisible(not compact)
        if hasattr(self, "playlist_combo"):
            self.playlist_combo.setMinimumWidth(118 if compact else 150)

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

    # ------------------------------------------------------------------ playlists / modes
    def _set_play_mode(self, mode: str) -> None:
        mode = self.engine.set_play_mode(mode)
        self.store.settings["music_mode"] = mode
        self.store.save()
        self._update_mode_buttons()

    def _update_mode_buttons(self) -> None:
        if not hasattr(self, "mode_buttons"):
            return
        labels = {"sequence": "顺序播放", "shuffle": "随机播放", "single": "单曲循环"}
        for mode, btn in self.mode_buttons.items():
            active = mode == self.engine.play_mode
            btn.setChecked(active)
            btn.setIcon(theme.icon(
                {"sequence": "order", "shuffle": "shuffle", "single": "repeat-one"}[mode],
                theme.GOLD if active else theme.MUTED,
                13,
            ))
            btn.setToolTip(labels[mode] + (" · 当前" if active else ""))
        if hasattr(self, "mode_text"):
            self._update_queue_label()

    def _refresh_playlists(self, select_id: str | None = None) -> None:
        """Fill the selector with user playlists only.

        The local folder is not a playlist any more; it lives in its own tab and
        keeps its own order in ``settings.local_order``.
        """
        playlists = [pl for pl in self.store.playlists() if not pl.get("builtin")]
        wanted = select_id or self._current_playlist_id
        self.playlist_combo.blockSignals(True)
        self.playlist_combo.clear()
        for pl in playlists:
            self.playlist_combo.addItem(str(pl.get("name", "歌单")), str(pl.get("id", "")))
        if playlists:
            idx = self.playlist_combo.findData(wanted) if wanted else -1
            self.playlist_combo.setCurrentIndex(max(0, idx))
        self.playlist_combo.blockSignals(False)
        self._current_playlist_id = str(self.playlist_combo.currentData() or "")
        self._size_playlist_popup()
        self._on_playlist_changed()

    def _size_playlist_popup(self) -> None:
        """Let the dropdown be as wide as the longest playlist name."""
        combo = self.playlist_combo
        view = combo.view()
        metrics = view.fontMetrics()
        widest = 0
        for i in range(combo.count()):
            widest = max(widest, metrics.horizontalAdvance(combo.itemText(i)))
        view.setMinimumWidth(max(combo.width(), min(360, widest + 48)))

    def _selected_playlist(self) -> dict | None:
        if not self._current_playlist_id:
            return None
        pl = self.store.playlist(self._current_playlist_id)
        if pl and pl.get("builtin"):
            return None
        return pl

    def _on_playlist_changed(self) -> None:
        if not hasattr(self, "playlist_list"):
            return
        self._current_playlist_id = str(self.playlist_combo.currentData() or "")
        pl = self._selected_playlist()
        has_pl = pl is not None
        if not has_pl:
            self._playlist_mode = "browse"
        for widget in (
            self.playlist_rename_btn,
            self.playlist_delete_btn,
            self.playlist_sort_btn,
            self.playlist_add_btn,
            self.playlist_remove_btn,
            self.playlist_search,
            self.playlist_list,
        ):
            widget.setEnabled(has_pl)
        self.playlist_sort_btn.setText("排序")
        self.playlist_remove_btn.setText("移除歌曲")
        self._apply_playlist_mode_ui()
        self._refresh_playlist_tracks()

    def _apply_playlist_mode_ui(self) -> None:
        has_pl = self._selected_playlist() is not None
        sort_active = has_pl and self._playlist_mode == "sort"
        remove_active = has_pl and self._playlist_mode == "remove"
        self.playlist_sort_btn.setText("完成排序" if sort_active else "排序")
        self.playlist_remove_btn.setText("取消移除" if remove_active else "移除歌曲")
        self.remove_bar.setVisible(remove_active)
        if hasattr(self, "playlist_search"):
            self.playlist_search.setEnabled(has_pl and self._playlist_mode == "browse")
        self.playlist_list.setDragDropMode(
            QAbstractItemView.InternalMove if sort_active else QAbstractItemView.NoDragDrop
        )
        self.playlist_list.setDragEnabled(sort_active)
        self.playlist_list.setAcceptDrops(sort_active)
        self.playlist_list.setDropIndicatorShown(sort_active)
        self.playlist_list.setDefaultDropAction(Qt.MoveAction)
        self.playlist_list.setSelectionMode(
            QAbstractItemView.NoSelection if remove_active else QAbstractItemView.SingleSelection
        )
        if remove_active:
            self._update_remove_count()
        else:
            self.remove_count_label.setText("勾选要移除的歌曲")

    def _set_playlist_mode(self, mode: str) -> None:
        if not self._selected_playlist():
            return
        if self._playlist_mode == mode:
            mode = "browse"
        if mode in ("sort", "remove"):
            # Dragging and checkbox removal address rows by index, so they only
            # make sense on the complete list, not on a filtered view.
            self.playlist_search.blockSignals(True)
            self.playlist_search.clear()
            self.playlist_search.blockSignals(False)
        self._playlist_mode = mode
        self._apply_playlist_mode_ui()
        self._refresh_playlist_tracks()

    @staticmethod
    def _entry_search_text(entry: dict) -> str:
        track = entry.get("track") or {}
        bits = [
            str(entry.get("title", "")),
            str(entry.get("subtitle", "")),
            str(track.get("artist", "")),
            str(track.get("album", "")),
        ]
        path = str(entry.get("path", ""))
        if path:
            bits.append(Path(path).stem)
            bits.append(Path(path).parent.name)
        return " ".join(bits).casefold()

    def _playlist_filtered_entries(self) -> list[dict]:
        pl = self._selected_playlist()
        if not pl:
            return []
        entries = [e for e in pl.get("tracks", []) if isinstance(e, dict)]
        query = ""
        if hasattr(self, "playlist_search"):
            query = self.playlist_search.text().strip().casefold()
        if query:
            entries = [e for e in entries if query in self._entry_search_text(e)]
        return entries

    def _refresh_playlist_tracks(self) -> None:
        if not hasattr(self, "playlist_list"):
            return
        pl = self._selected_playlist()
        self.playlist_list.blockSignals(True)
        self.playlist_list.clear()
        if not pl:
            self._playlist_entries = []
            self.playlist_list.blockSignals(False)
            self.playlist_list.setVisible(False)
            self.playlist_empty.setVisible(True)
            self.playlist_empty.setText(
                "还没有歌单。点上方「+ 新建」给自己建一个，再从本地曲库或在线寻音里挑歌加进来。"
            )
            self.playlist_hint.setText("歌单需要自己创建和维护；本地文件夹在「本地曲库」页。")
            self.playlist_count.setText("0 首")
            return
        entries = self._playlist_filtered_entries()
        mode = self._playlist_mode
        total = len([e for e in pl.get("tracks", []) if isinstance(e, dict)])
        filtered = bool(self.playlist_search.text().strip())
        hint = "拖动左侧标志调整顺序" if mode == "sort" else (
            "勾选歌曲后点击下方确认移除" if mode == "remove" else "双击播放 · 右键管理"
        )
        self.playlist_hint.setText(f"{pl.get('name', '歌单')} · {hint}")
        if filtered:
            self.playlist_empty.setText("这个歌单里没有匹配的歌曲。换个关键词，或清空搜索框。")
        else:
            self.playlist_empty.setText("这个歌单还没有歌。点「添加歌曲」从本地曲库或其他歌单里选几首吧。")
        for entry in entries:
            item = QListWidgetItem()
            kind = str(entry.get("kind", "local"))
            title = str(entry.get("title") or (Path(str(entry.get("path", ""))).stem if kind == "local" else "在线曲目"))
            if kind == "local":
                path = Path(str(entry.get("path", "")))
                subtitle = "本地曲库"
                badge = path.suffix.lstrip(".").upper() or "LOCAL"
                color = theme.GOLD_SOFT
                meta = f"{path.stat().st_size/1024/1024:.1f} MB" if path.exists() else "文件缺失"
            else:
                track = entry.get("track") or {}
                subtitle = str(entry.get("subtitle") or f"{track.get('artist', '在线音源')} · 在线")
                badge = "网易" if track.get("source") == "netease" else "试听"
                color = theme.GREEN if track.get("source") == "netease" else theme.TEAL
                meta = "ONLINE"
            item.setData(Qt.UserRole, entry)
            item.setSizeHint(QSize(10, 50))
            if mode == "remove":
                item.setText(f"{title}  ·  {subtitle}")
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.playlist_list.addItem(item)
            else:
                row = TrackRow(
                    title,
                    subtitle,
                    badge,
                    badge_color=color,
                    meta=meta,
                    show_handle=mode == "sort",
                )
                if mode == "sort":
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
                self.playlist_list.addItem(item)
                self.playlist_list.setItemWidget(item, row)
        self.playlist_list.blockSignals(False)
        self._playlist_entries = entries
        has_tracks = bool(entries)
        self.playlist_list.setVisible(has_tracks)
        self.playlist_empty.setVisible(not has_tracks)
        self.playlist_count.setText(f"{len(entries)} / {total} 首" if filtered else f"{total} 首")
        if mode == "remove":
            self._update_remove_count()

    def _update_remove_count(self, *_args) -> None:
        if self._playlist_mode != "remove" or not hasattr(self, "playlist_list"):
            return
        count = sum(
            1 for i in range(self.playlist_list.count())
            if self.playlist_list.item(i).checkState() == Qt.Checked
        )
        self.remove_count_label.setText(f"已勾选 {count} 首，确认后只从歌单移除，不删除本地文件。")
        self.remove_confirm_btn.setText(f"确认移除 {count} 首" if count else "确认移除")

    def _on_playlist_reordered(self) -> None:
        if self._playlist_mode != "sort":
            return
        pl = self._selected_playlist()
        if not pl:
            return
        entries = []
        for i in range(self.playlist_list.count()):
            entry = self.playlist_list.item(i).data(Qt.UserRole)
            if isinstance(entry, dict):
                entries.append(entry)
        self.store.set_playlist_tracks(str(pl["id"]), entries)
        QTimer.singleShot(0, self._refresh_playlist_tracks)

    def _confirm_remove_checked(self) -> None:
        pl = self._selected_playlist()
        if not pl:
            return
        rows = [
            i for i in range(self.playlist_list.count())
            if self.playlist_list.item(i).checkState() == Qt.Checked
        ]
        if not rows:
            return
        for row in reversed(rows):
            self.store.remove_from_playlist(str(pl["id"]), row)
        self._playlist_mode = "browse"
        self._apply_playlist_mode_ui()
        self._refresh_playlist_tracks()

    def _open_add_songs(self) -> None:
        pl = self._selected_playlist()
        if not pl:
            return
        sources = []
        online_entries = self._online_entries()
        if online_entries:
            sources.append({
                "id": "online",
                "name": f"在线寻音结果（{len(online_entries)} 首）",
                "entries": online_entries,
            })
        sources.append({
            "id": "local",
            "name": "本地曲库",
            "entries": [self._entry_from_local(p) for p in self._local_paths],
        })
        for source in self.store.playlists():
            if source.get("builtin") or source.get("id") == pl.get("id"):
                continue
            sources.append({
                "id": str(source.get("id", "")),
                "name": str(source.get("name", "歌单")),
                "entries": list(source.get("tracks", [])),
            })
        target_id = str(pl["id"])
        dialog = PlaylistAddDialog(
            self,
            str(pl.get("name", "歌单")),
            sources,
            lambda entry: self.store.add_to_playlist(target_id, entry),
        )
        dialog.exec_()
        self._refresh_playlist_tracks()

    def _online_entries(self) -> list[dict]:
        return [self._entry_from_track(t) for t in self._online_tracks]

    def _entry_from_local(self, path: Path) -> dict:
        return {
            "kind": "local",
            "path": str(path),
            "title": path.stem,
            "subtitle": "本地曲库",
        }

    def _entry_from_track(self, track: Track) -> dict:
        return {
            "kind": "online",
            "title": track.title,
            "subtitle": track.subtitle,
            "track": {
                "source": track.source,
                "id": track.id,
                "title": track.title,
                "artist": track.artist,
                "album": track.album,
                "duration": track.duration,
                "preview_url": track.preview_url,
                "cover": track.cover,
            },
        }

    def _playable_from_entry(self, entry: dict) -> Playable | None:
        kind = str(entry.get("kind", "local"))
        if kind == "local":
            path = Path(str(entry.get("path", "")))
            if not path.exists():
                return None
            return Playable(
                title=str(entry.get("title") or path.stem),
                subtitle=str(entry.get("subtitle") or "本地曲库"),
                path=path,
            )
        data = entry.get("track") or {}
        if not data:
            return None
        track = Track(
            source=str(data.get("source", "")),
            id=str(data.get("id", "")),
            title=str(data.get("title", "在线曲目")),
            artist=str(data.get("artist", "")),
            album=str(data.get("album", "")),
            duration=int(data.get("duration", 0) or 0),
            preview_url=str(data.get("preview_url", "")),
            cover=str(data.get("cover", "")),
        )
        return Playable(
            title=track.title,
            subtitle=track.subtitle,
            track=track,
            duration=track.duration,
        )

    def _playlist_playables(self) -> list[Playable]:
        """Playable queue for the visible playlist rows (search results included)."""
        items: list[Playable] = []
        for entry in self._playlist_entries or self._playlist_filtered_entries():
            item = self._playable_from_entry(entry)
            if item:
                items.append(item)
        return items

    def _local_playables(self) -> list[Playable]:
        return [
            Playable(title=p.stem, subtitle="本地曲库", path=p)
            for p in (self._local_visible or self._local_paths)
        ]

    def _playlist_source(self) -> tuple:
        return ("playlist", self._current_playlist_id)

    def _play_playlist_item(self, item: QListWidgetItem) -> None:
        row = self.playlist_list.row(item)
        items = self._playlist_playables()
        if 0 <= row < len(items):
            self._queue_source = self._playlist_source()
            self.engine.play_queue(items, row)
            self._update_queue_label()

    def _new_playlist(self) -> None:
        name, ok = InputDialog.get_text(self, "新建歌单", "歌单名称", "我的收藏")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        pl = self.store.create_playlist(name)
        self._refresh_playlists(str(pl["id"]))

    def _rename_playlist(self) -> None:
        pl = self._selected_playlist()
        if not pl:
            return
        name, ok = InputDialog.get_text(self, "重命名歌单", "新的歌单名称", str(pl.get("name", "")))
        if ok and name.strip():
            self.store.rename_playlist(str(pl["id"]), name)
            self._refresh_playlists(str(pl["id"]))
            self._update_queue_label()

    def _delete_playlist(self) -> None:
        pl = self._selected_playlist()
        if not pl:
            return
        if not ConfirmDialog.ask(
            self,
            "删除歌单",
            f"确定删除「{pl.get('name')}」吗？歌单里的歌曲不会从本地删除。",
            confirm_text="删除",
            danger=True,
        ):
            return
        self.store.delete_playlist(str(pl["id"]))
        self._refresh_playlists("")

    def _choose_add_target(self) -> dict | None:
        current = self._selected_playlist()
        if current and not current.get("builtin"):
            return current
        custom = [p for p in self.store.playlists() if not p.get("builtin")]
        if not custom:
            name, ok = InputDialog.get_text(self, "新建歌单", "还没有自定义歌单，先建一个吧。", "我的收藏")
            if not ok or not name.strip():
                return None
            return self.store.create_playlist(name)
        menu = QMenu(self)
        for pl in custom:
            action = menu.addAction(str(pl.get("name", "歌单")))
            action.setData(str(pl.get("id", "")))
        chosen = menu.exec_(QCursor.pos())
        if not chosen:
            return None
        return self.store.playlist(str(chosen.data() or ""))

    def _add_entry_to_playlist(self, entry: dict) -> None:
        target = self._choose_add_target()
        if not target:
            return
        if self.store.add_to_playlist(str(target["id"]), entry):
            self.tabs.setCurrentIndex(0)
            self._refresh_playlists(str(target["id"]))
        else:
            NoticeDialog.show_message(self, "加入歌单", "这首歌已经在歌单里了，或无法加入。")

    def _add_selected_local(self) -> None:
        item = self.local_list.currentItem()
        if not item:
            return
        path = Path(str(item.data(Qt.UserRole)))
        if path.exists():
            self._add_entry_to_playlist(self._entry_from_local(path))

    def _add_selected_online(self) -> None:
        item = self.online_list.currentItem()
        if not item:
            return
        key = str(item.data(Qt.UserRole) or "")
        track = next((t for t in self._online_tracks if t.key == key), None)
        if track:
            self._add_entry_to_playlist(self._entry_from_track(track))

    def _local_context_menu(self, pos) -> None:
        item = self.local_list.itemAt(pos)
        if not item:
            return
        self.local_list.setCurrentItem(item)
        menu = QMenu(self)
        add = menu.addAction("加入歌单…")
        play = menu.addAction("播放")
        rename = menu.addAction("重命名文件…")
        action = menu.exec_(self.local_list.mapToGlobal(pos))
        if action == add:
            self._add_selected_local()
        elif action == play:
            self._play_local_item(item)
        elif action == rename:
            self._rename_local_track(Path(str(item.data(Qt.UserRole))))

    def _online_context_menu(self, pos) -> None:
        item = self.online_list.itemAt(pos)
        if not item:
            return
        self.online_list.setCurrentItem(item)
        menu = QMenu(self)
        add = menu.addAction("加入歌单…")
        play = menu.addAction("播放")
        action = menu.exec_(self.online_list.mapToGlobal(pos))
        if action == add:
            self._add_selected_online()
        elif action == play:
            self._play_online_item(item)

    def _playlist_context_menu(self, pos) -> None:
        if self._playlist_mode != "browse":
            return
        item = self.playlist_list.itemAt(pos)
        if not item:
            return
        self.playlist_list.setCurrentItem(item)
        pl = self._selected_playlist()
        if not pl or pl.get("builtin"):
            return
        menu = QMenu(self)
        up = menu.addAction("上移")
        down = menu.addAction("下移")
        move = menu.addAction("移到其他歌单…")
        remove = menu.addAction("从歌单移除")
        action = menu.exec_(self.playlist_list.mapToGlobal(pos))
        if action == up:
            self._move_playlist_item(-1)
        elif action == down:
            self._move_playlist_item(1)
        elif action == move:
            self._move_playlist_item_to_other()
        elif action == remove:
            self._remove_playlist_item()

    def _remove_playlist_item(self) -> None:
        item = self.playlist_list.currentItem()
        if not item or not self._selected_playlist() or self._selected_playlist().get("builtin"):
            return
        row = self.playlist_list.row(item)
        self.store.remove_from_playlist(self._current_playlist_id, row)
        self._refresh_playlist_tracks()
        if self.playlist_list.count():
            self.playlist_list.setCurrentRow(min(row, self.playlist_list.count() - 1))

    def _rename_local_track(self, path: Path | None = None) -> None:
        if path is None:
            item = self.local_list.currentItem()
            if not item:
                NoticeDialog.show_message(self, "重命名本地音乐", "先在本地曲库列表里选中一首歌。")
                return
            path = Path(str(item.data(Qt.UserRole)))
        path = Path(path)
        if not path.exists():
            NoticeDialog.show_message(self, "重命名本地音乐", "这个音频文件不存在。")
            return
        name, ok = InputDialog.get_text(self, "重命名本地音乐", "新的文件名", path.stem)
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if any(ch in name for ch in '<>:"/\\|?*'):
            NoticeDialog.show_message(self, "重命名本地音乐", "文件名不能包含 < > : \" / \\ | ? * 这些字符。")
            return
        suffix = path.suffix
        if suffix and name.lower().endswith(suffix.lower()):
            name = name[: -len(suffix)].rstrip()
        if not name:
            return
        target = path.with_name(name + suffix)
        if target == path:
            return
        if target.exists():
            NoticeDialog.show_message(self, "重命名本地音乐", "同目录下已经有同名文件了。")
            return
        try:
            path.rename(target)
        except OSError as e:
            NoticeDialog.show_message(self, "重命名本地音乐", f"重命名失败：{e}")
            return
        self.store.update_local_path(str(path), str(target))
        self.load_local(initial=False)
        self._refresh_playlist_tracks()

    def _move_playlist_item(self, delta: int) -> None:
        item = self.playlist_list.currentItem()
        if not item:
            return
        row = self.playlist_list.row(item)
        if self.store.move_playlist_track(self._current_playlist_id, row, delta):
            self._refresh_playlist_tracks()
            self.playlist_list.setCurrentRow(row + delta)

    def _move_playlist_item_to_other(self) -> None:
        item = self.playlist_list.currentItem()
        if not item:
            return
        current = self._selected_playlist()
        if not current or current.get("builtin"):
            return
        targets = [p for p in self.store.playlists() if not p.get("builtin") and p.get("id") != current.get("id")]
        if not targets:
            NoticeDialog.show_message(self, "移到其他歌单", "还没有别的自定义歌单，先新建一个吧。")
            return
        menu = QMenu(self)
        for pl in targets:
            action = menu.addAction(str(pl.get("name", "歌单")))
            action.setData(str(pl.get("id", "")))
        chosen = menu.exec_(QCursor.pos())
        if not chosen:
            return
        target_id = str(chosen.data() or "")
        row = self.playlist_list.row(item)
        if self.store.move_track_between_playlists(self._current_playlist_id, target_id, row):
            self._refresh_playlist_tracks()
            self.playlist_combo.setCurrentIndex(self.playlist_combo.findData(target_id))
        else:
            NoticeDialog.show_message(self, "移到其他歌单", "目标歌单里已经有这首歌了。")

    # ------------------------------------------------------------------ local
    def load_local(self, *, initial: bool = False) -> None:
        folder = str(self.store.settings.get("music_folder", "") or "")
        self.folder_label.setText(folder)
        self.folder_label.setToolTip(folder)
        paths = scan_folder(folder)
        order = [str(p) for p in self.store.settings.get("local_order", []) if str(p)]
        order_index = {p: i for i, p in enumerate(order)}
        paths.sort(key=lambda p: (order_index.get(str(p), len(order)), p.name.casefold()))
        new_order = [str(p) for p in paths]
        if new_order != order:
            self.store.settings["local_order"] = new_order
            self.store.save()
        self._local_paths = paths
        self._refresh_local_list()
        if paths and not self.engine.current_playable():
            self.now_title.setText(paths[0].stem)
            self.now_sub.setText("本地曲库 · 双击曲目开始播放")
            self.album.set_track(paths[0].stem, False)
        if paths and initial and self.store.settings.get("auto_play_bgm"):
            self._queue_source = ("local",)
            self.engine.play_queue(self._local_playables(), 0)
            self._update_queue_label()
        self._refresh_playlist_tracks()

    @staticmethod
    def _path_search_text(path: Path) -> str:
        return f"{path.stem} {path.parent.name} {path.suffix}".casefold()

    def _local_filtered_paths(self) -> list[Path]:
        query = ""
        if hasattr(self, "local_search"):
            query = self.local_search.text().strip().casefold()
        if not query:
            return list(self._local_paths)
        return [p for p in self._local_paths if query in self._path_search_text(p)]

    def _refresh_local_list(self) -> None:
        if not hasattr(self, "local_list"):
            return
        paths = self._local_filtered_paths()
        self._local_visible = paths
        filtered = bool(self.local_search.text().strip())
        sorting = self._local_sort and not filtered
        self.local_list.blockSignals(True)
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
                show_handle=sorting,
            )
            item.setSizeHint(QSize(10, 50))
            if sorting:
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            self.local_list.addItem(item)
            self.local_list.setItemWidget(item, row)
        self.local_list.blockSignals(False)
        self.local_list.setDragDropMode(
            QAbstractItemView.InternalMove if sorting else QAbstractItemView.NoDragDrop
        )
        self.local_list.setDragEnabled(sorting)
        self.local_list.setAcceptDrops(sorting)
        self.local_list.setDropIndicatorShown(sorting)
        self.local_list.setDefaultDropAction(Qt.MoveAction)
        if filtered:
            self.local_count.setText(f"{len(paths)} / {len(self._local_paths)} 首")
            self.local_empty.setText("本地曲库里没有匹配的歌曲，换个关键词试试。")
        else:
            self.local_count.setText(f"{len(paths)} 首")
            self.local_empty.setText("这个文件夹里还没有音频。把 mp3 / wav / flac / m4a 放进来，或选择别的文件夹。")
        self.local_empty.setVisible(not paths)
        self.local_list.setVisible(bool(paths))

    def _toggle_local_sort(self) -> None:
        if not self._local_paths:
            return
        self._local_sort = not self._local_sort
        self.local_sort_btn.setText("完成排序" if self._local_sort else "排序")
        self.local_search.setEnabled(not self._local_sort)
        if self._local_sort:
            self.local_search.blockSignals(True)
            self.local_search.clear()
            self.local_search.blockSignals(False)
        self._refresh_local_list()

    def _on_local_reordered(self) -> None:
        if not self._local_sort:
            return
        paths = []
        for i in range(self.local_list.count()):
            data = self.local_list.item(i).data(Qt.UserRole)
            if data:
                paths.append(str(data))
        if not paths:
            return
        self.store.set_local_order(paths)
        self._local_paths = [Path(p) for p in paths]
        QTimer.singleShot(0, self._refresh_local_list)

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
        self.tabs.setCurrentIndex(1)
        try:
            index = self._local_visible.index(Path(path))
        except ValueError:
            return
        self._queue_source = ("local",)
        self.engine.play_queue(self._local_playables(), index)
        self._select_local_index(index)
        self._update_queue_label()

    def _select_local_index(self, index: int) -> None:
        if 0 <= index < self.local_list.count():
            self.local_list.blockSignals(True)
            self.local_list.setCurrentRow(index)
            self.local_list.blockSignals(False)

    def _play_local_item(self, item: QListWidgetItem) -> None:
        path = Path(str(item.data(Qt.UserRole)))
        self.tabs.setCurrentIndex(1)
        try:
            index = self._local_visible.index(path)
        except ValueError:
            index = 0
        self._queue_source = ("local",)
        self.engine.play_queue(self._local_playables(), index)
        self._select_local_index(index)
        self._update_queue_label()

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
        self._queue_source = ("online", self.search_edit.text().strip())
        self.engine.play_queue(items, index)
        self._online_selection = index
        self._update_queue_label()

    def _selected_online_track(self) -> Track | None:
        item = self.online_list.currentItem()
        if not item:
            return None
        key = str(item.data(Qt.UserRole) or "")
        return next((t for t in self._online_tracks if t.key == key), None)

    def _download_selected_online(self) -> None:
        """Save a streamed track into the local music folder."""
        track = self._selected_online_track()
        if not track:
            self.search_status.setText("先在结果里选中一首在线曲目。")
            return
        folder = Path(str(self.store.settings.get("music_folder", "") or ""))
        if not folder.exists():
            folder.mkdir(parents=True, exist_ok=True)
        self.online_download_btn.setEnabled(False)
        self.search_status.setText(f"正在把「{track.title}」保存到本地曲库…")
        thread = _CopyTrackThread(track, folder, self)
        thread.done.connect(lambda path: self._on_online_saved(path, track))
        thread.failed.connect(self._on_online_save_failed)
        self._copy_thread = thread
        thread.start()

    def _on_online_saved(self, path: str, track: Track) -> None:
        self.online_download_btn.setEnabled(True)
        self.search_status.setText(f"已保存到本地曲库：{Path(path).name}")
        self.load_local(initial=False)
        try:
            index = self._local_visible.index(Path(path))
        except ValueError:
            return
        self._select_local_index(index)

    def _on_online_save_failed(self, message: str) -> None:
        self.online_download_btn.setEnabled(True)
        self.search_status.setText(f"保存失败：{message}")

    # ------------------------------------------------------------------ engine events
    def _on_state(self, playing: bool) -> None:
        self.play_btn.setIcon(theme.icon("pause" if playing else "play", "#1c1810", 17))
        self.album.set_playing(playing)
        if not playing:
            self.progress.setEnabled(True)

    def _on_track(self, title: str, subtitle: str, kind: str, playing: bool) -> None:
        self.now_title.setText(title)
        self.now_sub.setText(subtitle)
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
        self._update_queue_label()
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

    def _on_speed_changed(self) -> None:
        rate = float(self.speed_combo.currentData() or 1.0)
        self.engine.set_playback_rate(rate)
        self.store.settings["music_rate"] = rate
        self.store.save()

    # ------------------------------------------------------------------ queue source
    def _tab_source(self) -> tuple:
        index = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        if index == 0:
            # No user playlist yet: the 歌单 tab behaves like the local library
            # so the global play/next/prev controls (and the tray menu) keep
            # working instead of silently falling back.
            if self._selected_playlist() is None:
                return ("local",)
            return self._playlist_source()
        if index == 1:
            return ("local",)
        return ("online", self.search_edit.text().strip())

    def _queue_matches_tab(self) -> bool:
        return self._queue_source == self._tab_source()

    def _queue_display_name(self) -> str:
        kind = self._queue_source[0] if self._queue_source else "local"
        if kind == "playlist":
            pl = self.store.playlist(str(self._queue_source[1]))
            return f"歌单「{pl.get('name', '歌单')}」" if pl else "歌单"
        if kind == "online":
            query = str(self._queue_source[1] or "").strip()
            return f"在线寻音「{query}」" if query else "在线寻音"
        return "本地曲库"

    def _update_queue_label(self) -> None:
        if not hasattr(self, "mode_text"):
            return
        labels = {"sequence": "顺序播放", "shuffle": "随机播放", "single": "单曲循环"}
        mode = labels.get(self.engine.play_mode, "顺序播放")
        self.mode_text.setText(f"{mode} · {self._queue_display_name()}")
        self.mode_text.setToolTip(
            f"当前队列：{self._queue_display_name()}，共 {len(self.engine.queue)} 首；"
            "播放模式作用于这个队列。"
        )

    def _current_row(self) -> int:
        index = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        if index == 0 and self.playlist_list.currentRow() >= 0:
            return self.playlist_list.currentRow()
        if index == 1 and self.local_list.currentRow() >= 0:
            return self.local_list.currentRow()
        return 0

    def _start_current_tab(self, index: int | None = None) -> bool:
        """Load the list visible in the active tab into the player queue."""
        if index is None:
            index = self._current_row()
        tab = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        if tab == 0 and self._selected_playlist() is not None:
            items = self._playlist_playables()
            source = self._playlist_source()
        elif tab == 0 or tab == 1:
            items = self._local_playables()
            source = ("local",)
        else:
            return False
        if not items:
            return False
        self._queue_source = source
        self.engine.play_queue(items, max(0, min(index, len(items) - 1)))
        self._update_queue_label()
        return True

    def _on_tab_changed(self, index: int) -> None:
        if hasattr(self, "playlist_bar"):
            self.playlist_bar.setVisible(index == 0)
        if index == 2:
            self._update_queue_label()
        self._update_mode_buttons()

    def previous_track(self) -> None:
        if self.engine.queue and self._queue_matches_tab():
            self.engine.previous()
            return
        if not self._start_current_tab() and self.engine.queue:
            self.engine.previous()

    def start_default(self) -> None:
        if self._start_current_tab():
            return
        folder = str(self.store.settings.get("music_folder", "") or "")
        self.engine.ensure_playing(folder)

    def toggle_playback(self) -> None:
        # A playing song must always be pausable, even if the player queue came
        # from another tab (or from the tray menu).  Only a *stopped* player
        # switches over to the list currently on screen.
        if self.engine.is_playing() or (self.engine.current_playable() and self._queue_matches_tab()):
            self.engine.toggle()
            return
        if not self._start_current_tab():
            if self.engine.current_playable():
                self.engine.toggle()
            else:
                # Nothing playable on this tab (e.g. an empty playlist):
                # fall back to the local library instead of doing nothing.
                self.start_default()

    def next_track(self) -> None:
        if self.engine.queue and self._queue_matches_tab():
            self.engine.next()
            return
        if not self._start_current_tab() and self.engine.queue:
            self.engine.next()

    def shutdown(self) -> None:
        for worker in (self._search_thread, getattr(self, "_copy_thread", None)):
            if worker and worker.isRunning():
                worker.wait(1500)
                if worker.isRunning():
                    worker.setParent(None)
                    _ORPHAN_SEARCHES.append(worker)
        self._search_thread = None
