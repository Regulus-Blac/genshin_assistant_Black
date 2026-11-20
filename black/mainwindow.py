from __future__ import annotations

import ctypes
import random
import sys
from ctypes import wintypes
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QColor, QCursor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QLayout,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
    QAction,
)

from . import content, render_mode, theme
from .character_picker import CharacterPickerDialog
from .dialogs import NoticeDialog
from .characters import (
    DEFAULT_CHARACTER_ID,
    get_character,
    get_look,
    legacy_look_id,
)
from .landscape_stage import LandscapeStage
from .levels import format_duration, format_short_duration
from .music_service import MusicEngine
from .overlay import LevelUpOverlay
from .pages.chat import ChatPage
from .pages.journal import JournalPage
from .pages.music import MusicPage
from .pages.settings import SettingsDialog
from .pages.study import StudyPage
from .paimon_popup import PaimonWhisperPopup
from .paths import IMAGES, avatar_path
from .sounds import Sounds
from .stage import CharacterStage
from .store import Store
from .timer import TimerEngine
from .tts import TTSService
from .whispers import get_whisper_avatar
from .widgets import Divider, IconButton, NavTab, TitleBar, TrayPlayer

WEEKDAYS = "一二三四五六日"


class _ResizeHandle(QWidget):
    """Invisible edge/corner grip for the frameless main window."""

    def __init__(self, parent: "MainWindow", edges: tuple[str, ...]) -> None:
        super().__init__(parent)
        self.edges = set(edges)
        self._start = None
        self._start_geo = None
        self._raised = False
        self.setMouseTracking(True)
        self.setStyleSheet("background: transparent;")
        self.setCursor(self._cursor_for_edges())
        self.setToolTip("拖动边缘调整窗口大小")

    def _cursor_for_edges(self):
        if {"left", "right"} & self.edges and {"top", "bottom"} & self.edges:
            return Qt.SizeFDiagCursor if ("left" in self.edges) == ("top" in self.edges) else Qt.SizeBDiagCursor
        if {"left", "right"} & self.edges:
            return Qt.SizeHorCursor
        return Qt.SizeVerCursor

    def update_zone(self) -> None:
        parent = self.parentWidget()
        if parent is None:
            return
        w, h = parent.width(), parent.height()
        # The visible rounded card starts 18px inside the translucent top-level
        # window.  Put the fallback grip on that visible border, not in the
        # invisible shadow area.
        b, inset, c = 16, 12, 28
        x, y, ww, hh = 0, 0, w, h
        if self.edges == {"left"}:
            x, y, ww, hh = inset, c, b, max(1, h - 2 * c)
        elif self.edges == {"right"}:
            x, y, ww, hh = w - inset - b, c, b, max(1, h - 2 * c)
        elif self.edges == {"top"}:
            x, y, ww, hh = c, inset, max(1, w - 2 * c), b
        elif self.edges == {"bottom"}:
            x, y, ww, hh = c, h - inset - b, max(1, w - 2 * c), b
        else:
            x = inset if "left" in self.edges else w - inset - b
            y = inset if "top" in self.edges else h - inset - b
            ww = hh = b
        changed = self.geometry() != QRect(x, y, ww, hh)
        if changed:
            self.setGeometry(x, y, ww, hh)
        if not self._raised:
            # Raising a widget forces a repaint of its area; doing that for all
            # eight grips on every resize event is a large part of the visible
            # flicker while the window is being dragged smaller.
            self.raise_()
            self._raised = True

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._start = event.globalPos()
            self._start_geo = self.parentWidget().geometry()
            begin = getattr(self.parentWidget(), "_begin_interactive_resize", None)
            if begin is not None:
                begin()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._start is None or self._start_geo is None or not (event.buttons() & Qt.LeftButton):
            return super().mouseMoveEvent(event)
        parent = self.parentWidget()
        dx = event.globalPos().x() - self._start.x()
        dy = event.globalPos().y() - self._start.y()
        geo = QRect(self._start_geo)
        min_w = max(560, parent.minimumWidth())
        min_h = max(260, parent.minimumHeight())
        if "left" in self.edges:
            new_left = min(self._start_geo.left() + dx, self._start_geo.right() - min_w + 1)
            geo.setLeft(new_left)
        if "right" in self.edges:
            geo.setRight(max(self._start_geo.right() + dx, self._start_geo.left() + min_w - 1))
        if "top" in self.edges:
            new_top = min(self._start_geo.top() + dy, self._start_geo.bottom() - min_h + 1)
            geo.setTop(new_top)
        if "bottom" in self.edges:
            geo.setBottom(max(self._start_geo.bottom() + dy, self._start_geo.top() + min_h - 1))
        parent.setGeometry(geo)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._start = None
        self._start_geo = None
        end = getattr(self.parentWidget(), "_end_interactive_resize", None)
        if end is not None:
            end()
        super().mouseReleaseEvent(event)
class MainWindow(QMainWindow):
    def __init__(self, store: Store) -> None:
        super().__init__(None)
        self.store = store
        self._shutting_down = False
        self._maximized = False
        self._compact = False
        self._narrow = False
        self._in_size_move = False
        self._normal_geometry: QRect | None = None
        self._recent_quotes: list[str] = []
        self._last_greeting_key = ""
        self._portrait_memory: dict[str, str] = {}
        self._character_meta = get_character(DEFAULT_CHARACTER_ID)
        self._whisper_popup = PaimonWhisperPopup()
        self._whisper_popup.another_requested.connect(self._whisper_another)
        self._whisper_popup.accepted.connect(lambda: self.sounds.interact())
        self._rng = random.Random()

        flags = Qt.Window | Qt.FramelessWindowHint
        if self.store.settings.get("always_on_top", False):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowTitle("Black · 提瓦特驻留终端")
        self.setWindowIcon(QIcon(str(IMAGES / "app_icon.png")))
        self.setMinimumSize(560, 260)

        self.timer = TimerEngine(self.store, self)
        self.sounds = Sounds(self)
        self.tts = TTSService(self)
        self.music_engine = MusicEngine(
            self, volume=int(self.store.settings.get("music_volume", 42) or 42)
        )

        self._build_ui()
        self._resize_handles: list[_ResizeHandle] = []
        self._build_resize_handles()
        self._setup_tray()
        self._wire_signals()
        self._apply_window_size()
        self._restore_character()
        self._refresh_global()
        self._set_initial_quote()
        self._schedule_whisper(first=True)
        self._clock = QTimer(self)
        self._clock.setInterval(1000)
        self._clock.timeout.connect(self._update_clock)
        self._clock.start()
        self.overlay = LevelUpOverlay(self)
        self.overlay.dismissed.connect(self.overlay.hide)
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._about_to_quit)
            app.installEventFilter(self)
        QTimer.singleShot(400, self._startup)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        self.outer = QVBoxLayout(central)
        # The layout must not advertise its content minimum as the window
        # minimum: otherwise Windows clamps a shrinking window at the wide
        # pre-compact layout size and the window visibly jumps when the
        # compact layout finally kicks in.  Content reflows and scrolls
        # instead, and setMinimumSize() below stays authoritative.
        self.outer.setSizeConstraint(QLayout.SetNoConstraint)
        self.outer.setContentsMargins(18, 18, 18, 18)
        self.outer.setSpacing(0)
        self.root = QWidget()
        self.root.setObjectName("RootCard")
        self.root.setAttribute(Qt.WA_StyledBackground, True)
        self.outer.addWidget(self.root)
        root_lay = QVBoxLayout(self.root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)
        self.root_lay = root_lay

        self.titlebar = TitleBar()
        root_lay.addWidget(self.titlebar)

        _meta, _look = self._stored_character_look()
        self.stage = self._make_stage(str(_look.get("art") or "art_snow.jpg"), _look)

        content_host = QWidget()
        self.content_host = content_host
        content_lay = QVBoxLayout(content_host)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)

        nav_row = QWidget()
        nav_lay = QHBoxLayout(nav_row)
        nav_lay.setContentsMargins(2, 0, 2, 0)
        nav_lay.setSpacing(3)
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_tabs: list[NavTab] = []
        for i, label in enumerate(("修习", "手札", "乐音", "交谈")):
            tab = NavTab(label)
            self.nav_group.addButton(tab, i)
            nav_lay.addWidget(tab)
            self.nav_tabs.append(tab)
        nav_lay.addStretch(1)
        self.whisper_btn = IconButton("sparkle", "让 Black 说一句", size=16, button_size=30, color=theme.GOLD_SOFT)
        self.whisper_btn.clicked.connect(lambda: self._show_whisper(manual=True))
        nav_lay.addWidget(self.whisper_btn)
        self.theme_btn = IconButton(
            "moon" if theme.is_light() else "sun",
            "切换到夜晚模式" if theme.is_light() else "切换到白天模式",
            size=16,
            button_size=30,
            color=theme.GOLD_SOFT,
        )
        self.theme_btn.clicked.connect(self._toggle_appearance)
        nav_lay.addWidget(self.theme_btn)
        self.settings_btn = IconButton("settings", "设置", size=16, button_size=30, color=theme.MUTED)
        self.settings_btn.clicked.connect(self._open_settings)
        nav_lay.addWidget(self.settings_btn)
        content_lay.addWidget(nav_row)
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet("background: rgba(217,188,125,26); border: none;")
        content_lay.addWidget(line)
        content_lay.addSpacing(13)

        self.study_page = StudyPage(self.store, self.timer)
        self.journal_page = JournalPage(self.store)
        self.music_page = MusicPage(self.store, self.music_engine)
        self.chat_page = ChatPage(self.store)
        self.stack = QStackedWidget()
        for page in (self.study_page, self.journal_page, self.music_page, self.chat_page):
            self.stack.addWidget(page)
        self.stack_scroll = QScrollArea()
        self.stack_scroll.setFrameShape(QFrame.NoFrame)
        self.stack_scroll.setWidgetResizable(True)
        self.stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack_scroll.setMinimumWidth(0)
        self.stack_scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.stack_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.stack_scroll.setWidget(self.stack)
        self.stack.setMinimumWidth(0)
        self.stack.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Minimum)
        content_lay.addWidget(self.stack_scroll, 1)
        self.nav_tabs[0].setChecked(True)
        self.nav_group.idClicked.connect(self._goto_page)
        self.stack.currentChanged.connect(lambda _idx: self._sync_stack_min_height())
        self._sync_stack_min_height()

        self._layout_body(str(_look.get("orientation", "portrait")))
        self.stage.set_orientation(str(_look.get("orientation", "portrait")))

        self.size_grip = QSizeGrip(self)
        self.size_grip.setFixedSize(18, 18)
        self.size_grip.setStyleSheet("background: transparent;")
        self.size_grip.setToolTip("拖动调整窗口大小")
        self.size_grip.raise_()

        self.titlebar.minimize_clicked.connect(self.showMinimized)
        self.titlebar.close_clicked.connect(self.close)
        self.titlebar.maximize_toggled.connect(self._toggle_maximize)
        self.titlebar.pin_toggled.connect(self._on_pin_toggled)
        self.titlebar.set_pinned(bool(self.store.settings.get("always_on_top", False)))

        self._connect_stage_signals(self.stage)
        QTimer.singleShot(0, self._apply_compact_mode)

    # Hysteresis bands: enter compact below the first value, only leave it
    # above the second one.  Without the gap a window hovering on the border
    # flips between layouts and flickers.
    COMPACT_ENTER_W, COMPACT_EXIT_W = 980, 1012
    COMPACT_ENTER_H, COMPACT_EXIT_H = 620, 650
    NARROW_ENTER_W, NARROW_EXIT_W = 760, 790

    def _apply_compact_mode(self) -> None:
        if not hasattr(self, "stage") or not hasattr(self, "study_page"):
            return
        if self._in_size_move:
            # Never swap the layout while the user is still dragging an edge;
            # the structural change is applied once on WM_EXITSIZEMOVE.
            return
        width, height = self.width(), self.height()
        if self._compact:
            compact = not (width >= self.COMPACT_EXIT_W and height >= self.COMPACT_EXIT_H)
        else:
            compact = width < self.COMPACT_ENTER_W or height < self.COMPACT_ENTER_H
        if self._narrow:
            narrow = width < self.NARROW_EXIT_W
        else:
            narrow = width < self.NARROW_ENTER_W
        structural = compact != self._compact or narrow != self._narrow
        expanded = self.body_orientation == "landscape" and not compact

        if structural:
            # Bundle the widget-tree changes into one repaint so no half-built
            # frame is ever shown.
            self.setUpdatesEnabled(False)
        try:
            if narrow != self._narrow:
                self._narrow = narrow
                if hasattr(self, "titlebar"):
                    self.titlebar.set_compact(narrow)
                self.study_page.set_compact(narrow)
                self.music_page.set_compact(narrow)
            if compact != self._compact:
                self._compact = compact
                self.stage.setVisible(not compact)
            self.study_page.set_expanded(expanded)
        finally:
            if structural:
                self.setUpdatesEnabled(True)
                self.update()

        if self.stack_scroll.horizontalScrollBarPolicy() != Qt.ScrollBarAlwaysOff:
            self.stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sync_stack_min_height()
        if expanded:
            QTimer.singleShot(0, self._sync_stack_min_height)

    def eventFilter(self, obj, event):  # noqa: N802
        if (
            event.type() == QEvent.Wheel
            and getattr(self, "body_orientation", "portrait") == "landscape"
            and not self._compact
            and isinstance(obj, QWidget)
        ):
            on_stage = obj is self.stage or (self.stage.isVisible() and self.stage.isAncestorOf(obj))
            on_study = obj is self.study_page or self.study_page.isAncestorOf(obj)
            if on_stage or on_study:
                bar = self.stack_scroll.verticalScrollBar()
                if bar.maximum() > 0:
                    bar.setValue(bar.value() - event.angleDelta().y())
                    event.accept()
                    return True
        return super().eventFilter(obj, event)

    def _layout_body(self, orientation: str) -> None:
        """Switch the main body between portrait (side-by-side) and landscape
        (stacked banner + full-width pages).  Widgets are reparented rather than
        rebuilt, so the timer, music queue and journal state survive the switch.
        """
        orientation = "landscape" if orientation == "landscape" else "portrait"
        stage = self.stage
        content = self.content_host
        old = getattr(self, "body", None)
        if old is not None:
            old_layout = old.layout()
            if old_layout is not None:
                old_layout.removeWidget(stage)
                old_layout.removeWidget(content)
            stage.setParent(None)
            content.setParent(None)
            self.root_lay.removeWidget(old)
            old.setParent(None)
            old.deleteLater()
        self.body = QWidget()
        self.root_lay.addWidget(self.body, 1)
        if orientation == "landscape":
            self.body_lay = QVBoxLayout(self.body)
            self.body_lay.setContentsMargins(16, 0, 16, 15)
            self.body_lay.setSpacing(10)
        else:
            self.body_lay = QHBoxLayout(self.body)
            self.body_lay.setContentsMargins(16, 0, 16, 15)
            self.body_lay.setSpacing(18)
        self.body_lay.addWidget(stage)
        self.body_lay.addWidget(content, 1)
        self.body_orientation = orientation
        self.body_lay.activate()
        self._position_resize_handles()
        self._apply_compact_mode()

    def _sync_stack_min_height(self) -> None:
        if not hasattr(self, "stack"):
            return
        page = self.stack.currentWidget()
        if page is not None:
            needed = max(1, page.sizeHint().height(), page.minimumSizeHint().height())
            if self.stack.minimumHeight() != needed:
                self.stack.setMinimumHeight(needed)

    def _wire_signals(self) -> None:
        self.study_page.note_preview_requested.connect(self._open_journal)
        self.study_page.data_changed.connect(self._on_data_changed)
        self.chat_page.open_settings_requested.connect(self._open_settings)
        # The timer and music engine outlive a theme rebuild.  Connect their
        # signals only once so a palette switch cannot duplicate callbacks.
        if getattr(self, "_engine_wired", False):
            return
        self._engine_wired = True
        self.timer.tick.connect(self._on_timer_tick)
        self.timer.active_changed.connect(self._on_active_changed)
        self.timer.session_finished.connect(self._on_session_finished)
        self.timer.level_ups.connect(self._on_level_ups)
        self.timer.day_changed.connect(self._on_day_changed)
        self.music_engine.track_changed.connect(self._on_track_changed)
        self.music_engine.loading_changed.connect(self._on_music_loading)
        self.music_engine.error_occurred.connect(self._on_music_error)
        self.music_engine.state_changed.connect(self._on_music_state)

    def _apply_window_size(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            w = min(1380, max(560, avail.width() - 60))
            h = min(864, max(260, avail.height() - 60))
            self.resize(w, h)
            self.move(
                avail.left() + max(0, (avail.width() - w) // 2),
                avail.top() + max(0, (avail.height() - h) // 2),
            )
        else:
            self.resize(1380, 860)

    def _build_resize_handles(self) -> None:
        for edges in (
            ("left",),
            ("right",),
            ("top",),
            ("bottom",),
            ("left", "top"),
            ("right", "top"),
            ("left", "bottom"),
            ("right", "bottom"),
        ):
            handle = _ResizeHandle(self, edges)
            self._resize_handles.append(handle)
        self._position_resize_handles()

    def _position_resize_handles(self) -> None:
        if not hasattr(self, "_resize_handles"):
            return
        for handle in self._resize_handles:
            if self._maximized:
                if handle.isVisible():
                    handle.hide()
            else:
                if not handle.isVisible():
                    handle.show()
                handle.update_zone()

    def _stored_character_look(self) -> tuple[dict, dict]:
        meta = get_character(self.store.settings.get("character", DEFAULT_CHARACTER_ID))
        look_id = str(self.store.settings.get("look", "") or "")
        if not look_id:
            look_id = legacy_look_id(meta["id"], self.store.settings.get("art")) or ""
        return meta, get_look(meta, look_id)

    def _make_stage(self, art: str, look: dict):
        stage_cls = LandscapeStage if str(look.get("orientation", "portrait")) == "landscape" else CharacterStage
        return stage_cls(art)

    def _connect_stage_signals(self, stage) -> None:
        stage.petted.connect(self._on_stage_petted)
        stage.chat_requested.connect(lambda: self._goto_page(3))
        stage.character_requested.connect(self._open_character_picker)
        stage.orientation_requested.connect(self._toggle_stage_orientation)
        stage.music_toggle_requested.connect(self.music_page.toggle_playback)
        stage.music_next_requested.connect(self.music_page.next_track)

    def _apply_stage_look(self, meta: dict, look: dict) -> None:
        self._character_meta = meta
        orientation = str(look.get("orientation", "portrait"))
        desired = LandscapeStage if orientation == "landscape" else CharacterStage
        if getattr(self.stage, "ORIENTATION", "portrait") != orientation:
            old = self.stage
            new = desired(str(look.get("art") or "art_snow.jpg"))
            self.stage = new
            self._connect_stage_signals(new)
            self._layout_body(orientation)
            new.set_character(meta, look["id"])
            self.stage.set_orientation(orientation)
            self._last_greeting_key = ""
            self._refresh_global()
            self._set_initial_quote()
            self._update_clock()
            self._update_music_initial()
            if self.overlay.isVisible():
                self.overlay.setGeometry(self.rect())
                self.overlay.raise_()
        else:
            self.stage.set_character(meta, look["id"])
            self.stage.set_orientation(orientation)

    def _toggle_stage_orientation(self) -> None:
        meta = self._character_meta
        looks = list(meta.get("looks", []))
        landscape = getattr(self.stage, "ORIENTATION", "portrait") == "landscape"
        if landscape:
            wanted = str(self._portrait_memory.get(meta["id"], ""))
            candidates = [l for l in looks if l.get("orientation", "portrait") == "portrait"]
            look = next((l for l in candidates if l["id"] == wanted), None)
            if look is None and candidates:
                look = candidates[0]
        else:
            current_look = str(self.store.settings.get("look", "") or "")
            if current_look:
                self._portrait_memory[meta["id"]] = current_look
            candidates = [l for l in looks if l.get("orientation") == "landscape"]
            look = candidates[0] if candidates else None
        if not look:
            NoticeDialog.show_message(self, "切换立绘", "这个角色还没有对应方向的立绘。")
            return
        # If the character has several art pieces in the requested direction
        # (Vodyanitsa has eight), let the user pick one instead of silently
        # choosing the first.  Official characters usually have exactly one.
        if not landscape and len(candidates) > 1 and hasattr(self.stage, "orientation_btn"):
            menu = QMenu(self)
            for candidate in candidates:
                action = menu.addAction(str(candidate.get("label", "立绘")))
                action.setData(str(candidate.get("id", "")))
            chosen = menu.exec_(
                self.stage.orientation_btn.mapToGlobal(
                    QPoint(0, self.stage.orientation_btn.height() + 2)
                )
            )
            if not chosen:
                return
            chosen_look = get_look(meta, str(chosen.data() or ""))
            if chosen_look.get("orientation") != look.get("orientation"):
                return
            look = chosen_look
        self.store.settings["character"] = meta["id"]
        self.store.settings["look"] = look["id"]
        self.store.save()
        self._apply_stage_look(meta, look)
        self.sounds.interact()

    def _restore_character(self) -> None:
        meta, look = self._stored_character_look()
        self._character_meta = meta
        self.store.settings["character"] = meta["id"]
        self.store.settings["look"] = look["id"]
        self.stage.set_character(meta, look["id"])

    def _open_character_picker(self) -> None:
        dialog = CharacterPickerDialog(
            self,
            str(self._character_meta.get("id", DEFAULT_CHARACTER_ID)),
            str(self.store.settings.get("look", "") or ""),
        )
        self.sounds.open()
        if dialog.exec_() != dialog.Accepted or not dialog.result_data:
            self.sounds.cancel()
            return
        cid = str(dialog.result_data.get("character", DEFAULT_CHARACTER_ID))
        meta = get_character(cid)
        look = get_look(meta, str(dialog.result_data.get("look", "")))
        self._character_meta = meta
        if look.get("orientation", "portrait") == "portrait":
            self._portrait_memory[meta["id"]] = look["id"]
        self.store.settings["character"] = meta["id"]
        self.store.settings["look"] = look["id"]
        self.store.save()
        self._apply_stage_look(meta, look)
        self._last_greeting_key = ""
        self._update_clock()
        self.stage.add_hearts(QPointF(self.stage.width() * 0.55, self.stage.height() * 0.48))
        self.sounds.interact()
        self._set_stage_quote(
            {
                "speaker": "Black",
                "text": f"……{meta['name']}会坐在书桌边陪你。放心，计时和手札还是我来管。",
            }
        )

    # ------------------------------------------------------------------ initial / global refresh
    def _startup(self) -> None:
        self._write_note()
        self._refresh_global()
        self.study_page.refresh_live()
        if int(self.store.data.get("launches", 0)) <= 2:
            self._set_stage_quote(
                {
                    "speaker": "Black",
                    "text": "初次见面。我是 Black，一只负责看时间、记手札的黑猫。考试卡片的日期可以点开修改——尤其是算法考试那一栏。",
                }
            )
        if self.store.settings.get("auto_play_bgm"):
            QTimer.singleShot(500, self.music_page.start_default)

    def _refresh_global(self) -> None:
        now = datetime.now()
        self._update_clock()
        actives = self.store.active_subjects()
        overall = self.store.overall(now)
        subjects = self.store.subjects(now)
        streak = max([s["streak"] for s in subjects], default=0)
        self.stage.set_stats(format_duration(overall["today_seconds"]), streak)
        self.stage.set_greeting(
            content.greeting(now, str(self.store.settings.get("user_name", "旅行者"))),
            content.greeting_sub(now, bool(actives)),
        )
        self.stage.set_date(
            f"{now.month}月{now.day}日 · 周{WEEKDAYS[now.weekday()]}",
            f"尘歌壶 · {self._character_meta.get('name', '沃雅妮莎')}",
        )
        self._update_exam_label(now)
        self._update_active_ui(actives, now)
        self._update_music_initial()
        self.study_page.refresh_live()

    @staticmethod
    def _elapsed_clock(seconds: int) -> str:
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    def _active_status(self, now: datetime) -> tuple[str, bool]:
        running = self.store.active_subjects()
        if not running:
            return "待机中", False
        if len(running) == 1:
            elapsed = self.store.active_elapsed(now, subject_id=running[0]["id"])
            return f"专注中 · {running[0]['name']} {self._elapsed_clock(elapsed)}", True
        return f"专注中 · {len(running)} 项并行", True

    def _update_clock(self) -> None:
        now = datetime.now()
        self.stage.set_time(now.strftime("%H:%M"))
        text, active = self._active_status(now)
        self.titlebar.set_status(text, active)
        if active:
            elapsed = max(
                (self.store.active_elapsed(now, subject_id=sub["id"]) for sub in self.store.active_subjects()),
                default=0,
            )
            if elapsed % 30 == 0:
                self.stage.set_stats(self.store.overall(now)["today_text"], max([s["streak"] for s in self.store.subjects(now)], default=0))
        # refresh greeting when hour or active state changes
        key = f"{now.hour}-{bool(active)}-{self.store.settings.get('user_name')}"
        if key != self._last_greeting_key:
            self._last_greeting_key = key
            self.stage.set_greeting(
                content.greeting(now, str(self.store.settings.get("user_name", "旅行者"))),
                content.greeting_sub(now, bool(active)),
            )
            self.stage.set_date(
                f"{now.month}月{now.day}日 · 周{WEEKDAYS[now.weekday()]}",
                f"尘歌壶 · {self._character_meta.get('name', '沃雅妮莎')}",
            )

    def _update_exam_label(self, now: datetime | None = None) -> None:
        now = now or datetime.now()
        exams = [e for e in self.store.exams(now) if not e.get("passed")]
        if exams:
            nearest = exams[0]
            self.stage.set_exam(f"{nearest['name']} · {nearest['label']}")
        else:
            all_exams = self.store.exams(now)
            if all_exams:
                self.stage.set_exam("所有考试已结束")
            else:
                self.stage.set_exam("考试日期待设定")

    def _update_active_ui(self, actives: list[dict], now: datetime) -> None:
        self._update_tray_status()
        if actives:
            names = "」「".join(sub["name"] for sub in actives)
            self.stage.set_stats(
                format_duration(self.store.total_today(now)),
                max([s["streak"] for s in self.store.subjects(now)], default=0),
            )
            self.stage.set_greeting(
                content.greeting(now, str(self.store.settings.get("user_name", "旅行者"))),
                f"「{names}」的计时正在继续。我会替你守好这一小段安静。",
            )
        self.study_page.refresh_live()

    def _update_music_initial(self) -> None:
        if self.music_engine.current_playable():
            item = self.music_engine.current_playable()
            self.stage.set_track(item.title, item.subtitle, self.music_engine.is_playing())
            return
        folder = Path(str(self.store.settings.get("music_folder", "") or ""))
        files = sorted(folder.glob("*.wav")) + sorted(folder.glob("*.mp3")) if folder.exists() else []
        if files:
            self.stage.set_track(files[0].stem, "Black 原声 · 点击播放", False)
        else:
            self.stage.set_track("尚未选择乐曲", "去「乐音」选一首", False)

    # ------------------------------------------------------------------ timer signals
    def _on_timer_tick(self) -> None:
        now = datetime.now()
        text, active = self._active_status(now)
        self.titlebar.set_status(text, active)
        subjects = self.store.subjects(now)
        self.stage.set_stats(
            format_duration(self.store.total_today(now)),
            max([s["streak"] for s in subjects], default=0),
        )

    def _on_data_changed(self) -> None:
        now = datetime.now()
        self._update_exam_label(now)
        self._refresh_global()
        if self.stack.currentIndex() == 1:
            self.journal_page.refresh(select_today=False, write_today=True)
        self._sync_stack_min_height()

    def _on_active_changed(self, subject_id) -> None:
        actives = self.store.active_subjects()
        self._update_active_ui(actives, datetime.now())
        self._update_tray_status()
        self.study_page.refresh_live()

    def _on_session_finished(self, summary: dict) -> None:
        self.sounds.chime()
        self._write_note_for_summary(summary)
        seconds = int(summary.get("seconds", 0))
        if seconds >= 60:
            message = (
                f"「{summary.get('name', '修习')}」的 {format_duration(seconds)} 已经写进今天的手札。"
                "去倒杯水吧，我在这里。"
            )
            self._set_stage_quote({"speaker": "Black", "text": message})
        self.study_page.refresh_live()
        if self.stack.currentIndex() == 1:
            self.journal_page.refresh(select_today=False, write_today=False)

    def _on_level_ups(self, ups: list) -> None:
        self.sounds.levelup()
        self.overlay.setGeometry(self.rect())
        self.overlay.show_levels(ups)
        if self.store.settings.get("tts_enabled") and ups:
            first = ups[0]
            self.speak(f"{first['name']}，等级提升到 {first['level']}，{first['title']}。")

    def _on_day_changed(self, new_day: str) -> None:
        try:
            d = datetime.strptime(new_day, "%Y-%m-%d").date()
            prev = (d - timedelta(days=1)).isoformat()
            self._write_note(prev)
        except Exception:
            pass
        self._update_clock()
        self.stage.set_date(
            f"{datetime.now().month}月{datetime.now().day}日 · 周{WEEKDAYS[datetime.now().weekday()]}",
            f"尘歌壶 · {self._character_meta.get('name', '沃雅妮莎')} · 新的一天",
        )
        self._update_exam_label()
        self.study_page.rebuild()
        self.journal_page.refresh(select_today=False, write_today=True)

    # ------------------------------------------------------------------ quotes
    def _speaker_meta(self, speaker: str) -> dict:
        return content.SPEAKERS.get(speaker, content.SPEAKERS["Black"])

    def _set_stage_quote(self, quote: dict) -> None:
        meta = self._speaker_meta(str(quote.get("speaker", "Black")))
        self.stage.set_quote(quote, meta.get("avatar", "black.png"))

    def _set_initial_quote(self) -> None:
        quote = content.daily_quote(datetime.now().date().isoformat())
        self._set_stage_quote(quote)
        self._recent_quotes.append(str(quote.get("text", "")))

    def _choose_quote(
        self,
        tags: list[str] | None = None,
        context: dict | None = None,
        speaker: str | None = None,
    ) -> dict:
        context = context or self.store.context()
        exclude = set(self._recent_quotes[-10:])
        for _ in range(4):
            quote = content.pick_quote(
                context=context,
                tags=tags,
                exclude=exclude,
                rng=self._rng,
                speaker=speaker,
            )
            if str(quote.get("text", "")) not in exclude:
                break
        self._recent_quotes.append(str(quote.get("text", "")))
        self._recent_quotes = self._recent_quotes[-12:]
        return quote

    def _whisper_persona(self) -> dict:
        return get_whisper_avatar(str(self.store.settings.get("whisper_avatar", "派蒙")))

    def _schedule_whisper(self, first: bool = False) -> None:
        try:
            minutes = max(1, min(180, int(self.store.settings.get("quote_interval_min", 20) or 20)))
        except Exception:
            minutes = 20
        delay = min(minutes * 60_000, 4 * 60_000) if first else minutes * 60_000
        if not hasattr(self, "_whisper_timer"):
            self._whisper_timer = QTimer(self)
            self._whisper_timer.setSingleShot(True)
            self._whisper_timer.timeout.connect(self._whisper_timeout)
        self._whisper_timer.start(max(60_000, delay))

    def _whisper_timeout(self) -> None:
        self._schedule_whisper(False)
        if not self.store.settings.get("desktop_whisper", True):
            return
        if QApplication.activeModalWidget() is not None:
            return
        self._show_whisper(manual=False)

    def _show_whisper(self, manual: bool = False) -> None:
        if not manual and not self.store.settings.get("desktop_whisper", True):
            return
        persona = self._whisper_persona()
        quote = self._choose_quote(context=self.store.context(), speaker=persona["speaker"])
        self._set_stage_quote(quote)
        self._whisper_popup.pop(
            quote,
            str(persona["path"]),
            str(persona.get("role", "提瓦特的朋友")),
            str(persona.get("color", theme.GOLD)),
            duration_ms=18000,
        )
        if self.store.settings.get("tts_enabled", False):
            self.speak(str(quote.get("text", "")))
        if manual:
            self.sounds.interact()

    def _whisper_another(self) -> None:
        persona = self._whisper_persona()
        quote = self._choose_quote(context=self.store.context(), speaker=persona["speaker"])
        self._set_stage_quote(quote)
        self._whisper_popup.pop(
            quote,
            str(persona["path"]),
            str(persona.get("role", "提瓦特的朋友")),
            str(persona.get("color", theme.GOLD)),
            duration_ms=18000,
        )
        if self.store.settings.get("tts_enabled", False):
            self.speak(str(quote.get("text", "")))

    def _on_stage_petted(self) -> None:
        self.sounds.interact()
        quote = self._choose_quote(tags=["cute", "courage", "default"])
        self._set_stage_quote(quote)
        if self.store.settings.get("tts_enabled", False):
            self.speak(str(quote.get("text", "")))

    def speak(self, text: str) -> None:
        if not text:
            return
        try:
            rate = int(self.store.settings.get("tts_rate", 0) or 0)
        except Exception:
            rate = 0
        self.tts.speak(text, rate)

    # ------------------------------------------------------------------ navigation / settings
    def _goto_page(self, index: int) -> None:
        if index < 0 or index >= self.stack.count():
            return
        changed = self.stack.currentIndex() != index
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_tabs):
            self.nav_tabs[index].setChecked(True)
        if index == 1:
            self.journal_page.refresh(select_today=False, write_today=True)
        elif index == 3:
            self.chat_page.refresh_status()
        self._sync_stack_min_height()
        if changed:
            self.sounds.click()

    def _open_journal(self) -> None:
        self._goto_page(1)
        self.journal_page.show_today()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, self.store)
        self.sounds.open()
        accepted = dialog.exec_() == dialog.Accepted
        if getattr(dialog, "quit_requested", False):
            self._shutdown()
            return
        if accepted and dialog.result_data:
            self.sounds.confirm()
            self._apply_settings(dialog.result_data)
        else:
            self.sounds.cancel()

    def _apply_settings(self, data: dict) -> None:
        self.store.settings.update(data)
        self.store.save()
        top = bool(data.get("always_on_top", False))
        if top != bool(self.windowFlags() & Qt.WindowStaysOnTopHint):
            visible = self.isVisible()
            self.setWindowFlag(Qt.WindowStaysOnTopHint, top)
            if visible:
                self.show()
        wanted_appearance = data.get("appearance")
        if wanted_appearance and theme.normalize_mode(wanted_appearance) != theme.MODE:
            # Rebuild after all settings are saved.  The new widgets read the
            # updated store and the new palette.
            self._set_appearance(str(wanted_appearance), persist=False)
            return
        self.titlebar.set_pinned(top)
        self.chat_page.refresh_status()
        self.music_page.load_local(initial=False)
        self.music_engine.set_volume(int(self.store.settings.get("music_volume", 42) or 42))
        self._schedule_whisper(False)
        self._last_greeting_key = ""
        self._update_clock()
        self._refresh_global()
        if data.get("auto_play_bgm") and not self.music_engine.is_playing():
            self.music_page.start_default()

    def _toggle_appearance(self) -> None:
        self._set_appearance("light" if not theme.is_light() else "dark")

    def _set_appearance(self, mode: str, *, persist: bool = True) -> None:
        mode = theme.normalize_mode(mode)
        if mode == theme.MODE:
            return
        if persist:
            self.store.settings["appearance"] = mode
            self.store.save()
        theme.set_mode(mode)
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app)
        self._rebuild_for_theme()
        if self.isVisible():
            anim = QPropertyAnimation(self, b"windowOpacity", self)
            anim.setDuration(220)
            anim.setStartValue(0.58)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            self._theme_fade = anim

    def _rebuild_for_theme(self) -> None:
        """Rebuild the visible UI in place while keeping engines and state.

        The timer, music player, tray and current sessions stay alive; only the
        widget tree is recreated so every inline style and custom painter picks
        up the new palette.
        """
        page = self.stack.currentIndex() if hasattr(self, "stack") else 0
        clock = getattr(self, "_clock", None)
        if clock is not None:
            clock.stop()
        old_central = self.takeCentralWidget()
        if old_central is not None:
            old_central.hide()
            old_central.setParent(None)
            old_central.deleteLater()
        self._recreate_whisper_popup()
        self._build_ui()
        self._position_resize_handles()
        self._wire_signals()
        self.titlebar.set_pinned(bool(self.store.settings.get("always_on_top", False)))
        if self._maximized:
            self.outer.setContentsMargins(0, 0, 0, 0)
            self.root.setProperty("maximized", "true")
            self.size_grip.hide()
        else:
            self.outer.setContentsMargins(18, 18, 18, 18)
            self.root.setProperty("maximized", "false")
        theme.set_prop(self.root, "maximized", "true" if self._maximized else "false")
        self.setProperty("customMaximized", self._maximized)
        self.titlebar.set_maximized_icon(self._maximized)
        self._restore_character()
        self._refresh_global()
        self._set_initial_quote()
        self._goto_page(page)
        self._update_tray_status()
        self._update_clock()
        self._update_music_initial()
        if self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())
            self.overlay.raise_()
        self._schedule_whisper(False)
        if clock is not None:
            clock.start()

    def _recreate_whisper_popup(self) -> None:
        old = getattr(self, "_whisper_popup", None)
        if old is not None:
            try:
                old.close()
                old.deleteLater()
            except Exception:
                pass
        self._whisper_popup = PaimonWhisperPopup()
        self._whisper_popup.another_requested.connect(self._whisper_another)
        self._whisper_popup.accepted.connect(lambda: self.sounds.interact())

    def _on_pin_toggled(self, checked: bool) -> None:
        self.store.settings["always_on_top"] = bool(checked)
        self.store.save()
        visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        if visible:
            self.show()

    def _toggle_maximize(self) -> None:
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        if not self._maximized:
            self._normal_geometry = self.geometry()
            if screen:
                self.setGeometry(screen.availableGeometry())
            self.outer.setContentsMargins(0, 0, 0, 0)
            self._maximized = True
            self.root.setProperty("maximized", "true")
            self.size_grip.hide()
        else:
            if self._normal_geometry:
                self.setGeometry(self._normal_geometry)
            self.outer.setContentsMargins(18, 18, 18, 18)
            self._maximized = False
            self.root.setProperty("maximized", "false")
            self.size_grip.show()
        theme.set_prop(self.root, "maximized", "true" if self._maximized else "false")
        self.setProperty("customMaximized", self._maximized)
        self.titlebar.set_maximized_icon(self._maximized)
        self._position_resize_handles()
        if self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())

    # ------------------------------------------------------------------ music callbacks
    def _on_track_changed(self, title: str, subtitle: str, kind: str, playing: bool) -> None:
        self.stage.set_track(title, subtitle, playing)
        self._update_tray_status()

    def _on_music_state(self, playing: bool) -> None:
        item = self.music_engine.current_playable()
        if item:
            self.stage.set_track(item.title, item.subtitle, playing)
        self._update_tray_status()

    def _on_music_loading(self, loading: bool, text: str) -> None:
        if loading:
            self.stage.set_track("正在获取乐曲…", text, False)

    def _on_music_error(self, message: str) -> None:
        self.sounds.error()
        self.stage.set_track("乐音暂时停下", "点开「乐音」看看发生了什么", False)

    # ------------------------------------------------------------------ journal
    def _write_note(self, date_key: str | None = None, quote: dict | None = None) -> Path | None:
        key = date_key or datetime.now().date().isoformat()
        try:
            quote = quote or content.daily_quote(key)
            return self.store.write_daily_note(key, quote=quote)
        except Exception:
            return None

    def _write_note_for_summary(self, summary: dict) -> None:
        for date_key in summary.get("dates", []) or [datetime.now().date().isoformat()]:
            self._write_note(date_key)

    # ------------------------------------------------------------------ tray / lifecycle
    def _setup_tray(self) -> None:
        self.tray: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(QIcon(str(IMAGES / "app_icon.png")), self)
        self.tray.setToolTip("Black · 提瓦特驻留终端")
        menu = QMenu()
        show_action = QAction("显示 Black", menu)
        show_action.triggered.connect(self._show_from_tray)
        menu.addAction(show_action)
        journal_action = QAction("预览今日手札", menu)
        journal_action.triggered.connect(self._tray_journal)
        menu.addAction(journal_action)
        self.tray_pause_action = QAction("暂停当前计时", menu)
        self.tray_pause_action.triggered.connect(self._tray_pause)
        menu.addAction(self.tray_pause_action)
        menu.addSeparator()
        # Music transport + play modes live in a small player widget instead of
        # a pile of menu rows, so the tray menu stays short.
        self.tray_player = TrayPlayer()
        self.tray_player.play_toggled.connect(self._tray_toggle_music)
        self.tray_player.previous_clicked.connect(self._tray_prev_music)
        self.tray_player.next_clicked.connect(self._tray_next_music)
        self.tray_player.mode_selected.connect(self._tray_set_music_mode)
        player_action = QWidgetAction(menu)
        player_action.setDefaultWidget(self.tray_player)
        menu.addAction(player_action)
        self.tray_music_open = QAction("打开乐音页", menu)
        self.tray_music_open.triggered.connect(self._tray_open_music)
        menu.addAction(self.tray_music_open)
        menu.addSeparator()
        quit_action = QAction("退出 Black", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray_menu = menu
        menu.aboutToShow.connect(self._update_tray_status)
        self.tray.show()
        self._update_tray_status()

    def _tray_prev_music(self) -> None:
        self.music_page.previous_track()
        self._update_tray_status()

    def _tray_next_music(self) -> None:
        self.music_page.next_track()
        self._update_tray_status()

    def _tray_set_music_mode(self, mode: str) -> None:
        self.music_page.set_play_mode(mode)
        self._update_tray_status()

    def _tray_toggle_music(self) -> None:
        self.music_page.toggle_playback()
        self._update_tray_status()

    def _tray_open_music(self) -> None:
        self._show_from_tray()
        self._goto_page(2)

    def _update_tray_status(self) -> None:
        if not self.tray:
            return
        running = self.store.active_subjects()
        playing = self.music_engine.is_playing()
        current = self.music_engine.current_playable()
        title = current.title if current else ""
        tips = []
        if len(running) == 1:
            tips.append(f"正在修习「{running[0]['name']}」")
        elif running:
            tips.append("正在修习" + "」「".join(sub["name"] for sub in running[:2]) + (
                f"」等 {len(running)} 项" if len(running) > 2 else "」"
            ))
        if playing and title:
            tips.append(f"正在播放「{title}」")
        self.tray.setToolTip("Black · " + (" · ".join(tips) if tips else "在书桌边等你"))
        self.tray_pause_action.setEnabled(bool(running))
        if not running:
            self.tray_pause_action.setText("当前没有计时")
        elif len(running) == 1:
            self.tray_pause_action.setText("暂停当前计时")
        else:
            self.tray_pause_action.setText(f"暂停全部计时（{len(running)} 项）")
        if hasattr(self, "tray_player"):
            self.tray_player.refresh(title, playing, self.music_engine.play_mode)

    def _tray_pause(self) -> None:
        if self.store.actives():
            count = len(self.store.actives())
            self.timer.pause_all()
            if self.tray:
                text = "计时已暂停，今天的进度已经记下。" if count == 1 else f"{count} 项计时都已暂停，进度已经记下。"
                self.tray.showMessage("Black", text, QSystemTrayIcon.Information, 2600)

    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        self._position_resize_handles()

    def _tray_journal(self) -> None:
        self._show_from_tray()
        self._open_journal()

    def _quit(self) -> None:
        self._shutdown()

    def _about_to_quit(self) -> None:
        if self._shutting_down:
            return
        try:
            if self.store.actives():
                self.timer.shutdown()
            self._write_note()
            self.store.save()
        except Exception:
            pass

    def _shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        try:
            if self._clock:
                self._clock.stop()
            if hasattr(self, "_whisper_timer"):
                self._whisper_timer.stop()
            self.timer.shutdown()
            self._write_note()
            self.store.save()
        except Exception:
            pass
        try:
            self._whisper_popup.close()
        except Exception:
            pass
        try:
            self.music_page.shutdown()
        except Exception:
            pass
        try:
            self.music_engine.shutdown()
        except Exception:
            pass
        try:
            self.chat_page.shutdown()
        except Exception:
            pass
        if self.tray:
            self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._shutting_down:
            event.accept()
            return
        close_to_tray = bool(self.store.settings.get("close_to_tray", True))
        if close_to_tray and self.tray and self.tray.isVisible():
            self.hide()
            event.ignore()
            if self.store.actives():
                running = len(self.store.actives())
                text = (
                    "我还在替你计时。双击托盘里的小黑猫，就能把我叫回来。"
                    if running == 1
                    else f"我还在替你计时（{running} 项同时进行）。双击托盘里的小黑猫，就能把我叫回来。"
                )
                self.tray.showMessage(
                    "Black",
                    text,
                    QSystemTrayIcon.Information,
                    3200,
                )
            else:
                self.tray.showMessage(
                    "Black",
                    "我先躲在托盘里。双击小黑猫，随时回来。",
                    QSystemTrayIcon.Information,
                    2600,
                )
            return
        self._shutdown()
        event.accept()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Do nothing expensive per mouse-move: moving eight fallback grips and
        # re-raising them on every resize event repaints the window edges over
        # and over, which is what made a shrink look like it was flashing.
        if self._left_button_down():
            self._begin_interactive_resize()
        self._schedule_resize_work()

    @staticmethod
    def _left_button_down() -> bool:
        """True while the user physically holds the left mouse button.

        The WM_ENTERSIZEMOVE/WM_EXITSIZEMOVE pair is the documented signal for a
        native sizing loop, but it is not always delivered to a frameless Qt
        window.  The real button state is always available, so a drag can never
        be interrupted by a deferred layout swap (the first half of a shrink
        crosses the stage/column thresholds, which is where the flashes were).
        """
        try:
            return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        except Exception:
            return False

    def _schedule_resize_work(self) -> None:
        if not hasattr(self, "_resize_timer"):
            self._resize_timer = QTimer(self)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.timeout.connect(self._after_resize)
        self._resize_timer.start(80)

    def _after_resize(self) -> None:
        if self._left_button_down():
            # Still dragging an edge: never swap the layout mid-gesture.
            self._schedule_resize_work()
            return
        self._finish_interactive_resize_state()
        if hasattr(self, "size_grip") and not self._maximized:
            grip_pos = QPoint(self.width() - 22, self.height() - 22)
            if self.size_grip.pos() != grip_pos:
                self.size_grip.move(grip_pos)
            self.size_grip.raise_()
        self._position_resize_handles()
        if hasattr(self, "overlay") and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())
        self._apply_compact_mode()

    def _finish_interactive_resize_state(self) -> None:
        if not self._in_size_move:
            return
        self._in_size_move = False
        if hasattr(self, "_size_move_watchdog"):
            self._size_move_watchdog.stop()
        render_mode.set_fast(False)
        if hasattr(self, "study_page"):
            self.study_page.set_fast_paint(False)
        if hasattr(self, "stage"):
            self.stage.resume_animation()
        album = getattr(getattr(self, "music_page", None), "album", None)
        if album is not None:
            album.resume_animation()
        self.update()

    def _begin_interactive_resize(self) -> None:
        """Freeze everything that repaints on its own while the user drags."""
        if self._in_size_move:
            return
        self._in_size_move = True
        render_mode.set_fast(True)
        if hasattr(self, "_resize_timer"):
            self._resize_timer.stop()
        if hasattr(self, "stage"):
            self.stage.pause_animation()
        if hasattr(self, "study_page"):
            self.study_page.set_fast_paint(True)
        album = getattr(getattr(self, "music_page", None), "album", None)
        if album is not None:
            album.pause_animation()
        # Safety net: a lost release must not leave the UI frozen.
        if not hasattr(self, "_size_move_watchdog"):
            self._size_move_watchdog = QTimer(self)
            self._size_move_watchdog.setSingleShot(True)
            self._size_move_watchdog.timeout.connect(self._end_interactive_resize)
        self._size_move_watchdog.start(15000)

    def _end_interactive_resize(self) -> None:
        if not self._in_size_move:
            return
        self._finish_interactive_resize_state()
        self._schedule_resize_work()

    def _schedule_compact(self) -> None:
        # Kept as the public name for "recheck the responsive layout".
        self._schedule_resize_work()

    def nativeEvent(self, event_type, message):  # noqa: N802
        """Let Windows perform hit-testing on the frameless edges.

        Child ``_ResizeHandle`` widgets are a useful fallback, but on Windows
        they can sit outside the visible rounded card and never receive hover
        events.  Returning HTLEFT/HTTOP... from WM_NCHITTEST gives the native
        resize cursor and drag behaviour at the real window border.

        The hit point is taken from ``QCursor.pos()`` on purpose: Qt widget
        geometry is in logical pixels while WM_NCHITTEST carries physical
        pixels, so decoding lParam directly made every point look shifted
        towards the right/bottom edge on scaled displays (the whole window
        turned into a resize border).  QCursor already speaks Qt coordinates.
        """
        if event_type == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0231:  # WM_ENTERSIZEMOVE
                    self._begin_interactive_resize()
                elif msg.message == 0x0232:  # WM_EXITSIZEMOVE
                    self._end_interactive_resize()
                elif msg.message == 0x0084 and not self._maximized:  # WM_NCHITTEST
                    local = self.mapFromGlobal(QCursor.pos())
                    w, h = self.width(), self.height()
                    if not (-2 <= local.x() <= w + 2 and -2 <= local.y() <= h + 2):
                        return super().nativeEvent(event_type, message)
                    # The visible card edge is inset 18px; a 30px native hit
                    # zone reaches it while still sparing the page content.
                    border = 30
                    left = local.x() <= border
                    right = local.x() >= w - border
                    top = local.y() <= border
                    bottom = local.y() >= h - border
                    if left and top:
                        return True, 13  # HTTOPLEFT
                    if right and top:
                        return True, 14  # HTTOPRIGHT
                    if left and bottom:
                        return True, 16  # HTBOTTOMLEFT
                    if right and bottom:
                        return True, 17  # HTBOTTOMRIGHT
                    if left:
                        return True, 10  # HTLEFT
                    if right:
                        return True, 11  # HTRIGHT
                    if top:
                        return True, 12  # HTTOP
                    if bottom:
                        return True, 15  # HTBOTTOM
            except Exception:
                pass
        return super().nativeEvent(event_type, message)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if hasattr(self, "stage"):
            self.stage.resume_animation()
        if hasattr(self, "overlay") and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())
        QTimer.singleShot(0, self._position_resize_handles)
        QTimer.singleShot(0, self._apply_compact_mode)

    def hideEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, "stage"):
            self.stage.pause_animation()
        super().hideEvent(event)
