from __future__ import annotations

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PyQt5.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
)
from PyQt5.QtGui import QColor, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QPushButton,
    QSizeGrip,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QAction,
)

from . import content, theme
from .character_picker import CharacterPickerDialog
from .characters import (
    DEFAULT_CHARACTER_ID,
    get_character,
    get_look,
    legacy_look_id,
)
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
from .widgets import Divider, IconButton, NavTab, TitleBar

WEEKDAYS = "一二三四五六日"
class MainWindow(QMainWindow):
    def __init__(self, store: Store) -> None:
        super().__init__(None)
        self.store = store
        self._shutting_down = False
        self._maximized = False
        self._normal_geometry: QRect | None = None
        self._recent_quotes: list[str] = []
        self._last_greeting_key = ""
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
        self.setMinimumSize(1180, 748)

        self.timer = TimerEngine(self.store, self)
        self.sounds = Sounds(self)
        self.tts = TTSService(self)
        self.music_engine = MusicEngine(
            self, volume=int(self.store.settings.get("music_volume", 42) or 42)
        )

        self._build_ui()
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
        QTimer.singleShot(400, self._startup)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        self.outer = QVBoxLayout(central)
        self.outer.setContentsMargins(18, 18, 18, 18)
        self.outer.setSpacing(0)
        self.root = QWidget()
        self.root.setObjectName("RootCard")
        self.root.setAttribute(Qt.WA_StyledBackground, True)
        self.outer.addWidget(self.root)
        root_lay = QVBoxLayout(self.root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        self.titlebar = TitleBar()
        root_lay.addWidget(self.titlebar)
        self.body = QWidget()
        body_lay = QHBoxLayout(self.body)
        body_lay.setContentsMargins(16, 0, 16, 15)
        body_lay.setSpacing(18)
        root_lay.addWidget(self.body, 1)

        art = str(self.store.settings.get("art", "art_snow.jpg") or "art_snow.jpg")
        self.stage = CharacterStage(art)
        body_lay.addWidget(self.stage)

        content_host = QWidget()
        content_lay = QVBoxLayout(content_host)
        content_lay.setContentsMargins(0, 0, 0, 0)
        content_lay.setSpacing(0)
        body_lay.addWidget(content_host, 1)

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
        content_lay.addWidget(self.stack, 1)
        self.nav_tabs[0].setChecked(True)
        self.nav_group.idClicked.connect(self._goto_page)

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

        self.stage.petted.connect(self._on_stage_petted)
        self.stage.chat_requested.connect(lambda: self._goto_page(3))
        self.stage.character_requested.connect(self._open_character_picker)
        self.stage.music_toggle_requested.connect(self.music_page.toggle_playback)
        self.stage.music_next_requested.connect(self.music_page.next_track)

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
            w = min(1380, max(1180, avail.width() - 60))
            h = min(864, max(748, avail.height() - 60))
            self.resize(w, h)
            self.move(
                avail.left() + max(0, (avail.width() - w) // 2),
                avail.top() + max(0, (avail.height() - h) // 2),
            )
        else:
            self.resize(1380, 860)

    def _restore_character(self) -> None:
        meta = get_character(self.store.settings.get("character", DEFAULT_CHARACTER_ID))
        look_id = str(self.store.settings.get("look", "") or "")
        if not look_id:
            look_id = legacy_look_id(meta["id"], self.store.settings.get("art")) or ""
        look = get_look(meta, look_id)
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
        if dialog.exec_() != dialog.Accepted or not dialog.result_data:
            return
        cid = str(dialog.result_data.get("character", DEFAULT_CHARACTER_ID))
        meta = get_character(cid)
        look = get_look(meta, str(dialog.result_data.get("look", "")))
        self._character_meta = meta
        self.store.settings["character"] = meta["id"]
        self.store.settings["look"] = look["id"]
        self.store.save()
        self.stage.set_character(meta, look["id"])
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
        active = self.store.active_subject()
        overall = self.store.overall(now)
        subjects = self.store.subjects(now)
        streak = max([s["streak"] for s in subjects], default=0)
        self.stage.set_stats(format_duration(overall["today_seconds"]), streak)
        self.stage.set_greeting(
            content.greeting(now, str(self.store.settings.get("user_name", "旅行者"))),
            content.greeting_sub(now, bool(active)),
        )
        self.stage.set_date(
            f"{now.month}月{now.day}日 · 周{WEEKDAYS[now.weekday()]}",
            f"尘歌壶 · {self._character_meta.get('name', '沃雅妮莎')}",
        )
        self._update_exam_label(now)
        self._update_active_ui(active, now)
        self._update_music_initial()
        self.study_page.refresh_live()

    @staticmethod
    def _elapsed_clock(seconds: int) -> str:
        seconds = max(0, int(seconds))
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"

    def _update_clock(self) -> None:
        now = datetime.now()
        self.stage.set_time(now.strftime("%H:%M"))
        active = self.store.active_subject()
        if active:
            elapsed = self.store.active_elapsed(now)
            self.titlebar.set_status(f"专注中 · {active['name']} {self._elapsed_clock(elapsed)}", True)
            if elapsed % 30 == 0:
                self.stage.set_stats(self.store.overall(now)["today_text"], max([s["streak"] for s in self.store.subjects(now)], default=0))
        else:
            self.titlebar.set_status("待机中", False)
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

    def _update_active_ui(self, active: dict | None, now: datetime) -> None:
        self._update_tray_status()
        if active:
            self.stage.set_stats(
                format_duration(self.store.total_today(now)),
                max([s["streak"] for s in self.store.subjects(now)], default=0),
            )
            self.stage.set_greeting(
                content.greeting(now, str(self.store.settings.get("user_name", "旅行者"))),
                f"「{active['name']}」的计时正在继续。我会替你守好这一小段安静。",
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
        active = self.store.active_subject()
        if active:
            self.titlebar.set_status(
                f"专注中 · {active['name']} {self._elapsed_clock(self.store.active_elapsed(now))}",
                True,
            )
        else:
            self.titlebar.set_status("待机中", False)
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

    def _on_active_changed(self, subject_id) -> None:
        active = self.store.active_subject()
        self._update_active_ui(active, datetime.now())
        self._update_tray_status()
        if not active:
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

    def _choose_quote(self, tags: list[str] | None = None, context: dict | None = None) -> dict:
        context = context or self.store.context()
        exclude = set(self._recent_quotes[-10:])
        for _ in range(4):
            quote = content.pick_quote(context=context, tags=tags, exclude=exclude, rng=self._rng)
            if str(quote.get("text", "")) not in exclude:
                break
        self._recent_quotes.append(str(quote.get("text", "")))
        self._recent_quotes = self._recent_quotes[-12:]
        return quote

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
        quote = self._choose_quote(context=self.store.context())
        self._set_stage_quote(quote)
        speaker = str(quote.get("speaker", "Black"))
        meta = self._speaker_meta(speaker)
        self._whisper_popup.pop(
            quote,
            str(avatar_path(meta.get("avatar", "black.png"))),
            str(meta.get("title", "提瓦特的朋友")),
            str(meta.get("color", theme.GOLD)),
            duration_ms=18000,
        )
        if self.store.settings.get("tts_enabled", False):
            self.speak(str(quote.get("text", "")))
        if manual:
            self.sounds.interact()

    def _whisper_another(self) -> None:
        quote = self._choose_quote(context=self.store.context())
        self._set_stage_quote(quote)
        speaker = str(quote.get("speaker", "Black"))
        meta = self._speaker_meta(speaker)
        self._whisper_popup.pop(
            quote,
            str(avatar_path(meta.get("avatar", "black.png"))),
            str(meta.get("title", "提瓦特的朋友")),
            str(meta.get("color", theme.GOLD)),
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
        self.stack.setCurrentIndex(index)
        if 0 <= index < len(self.nav_tabs):
            self.nav_tabs[index].setChecked(True)
        if index == 1:
            self.journal_page.refresh(select_today=False, write_today=True)
        elif index == 3:
            self.chat_page.refresh_status()

    def _open_journal(self) -> None:
        self._goto_page(1)
        self.journal_page.show_today()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self, self.store)
        accepted = dialog.exec_() == dialog.Accepted
        if getattr(dialog, "quit_requested", False):
            self._shutdown()
            return
        if accepted and dialog.result_data:
            self._apply_settings(dialog.result_data)

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
        if self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())

    # ------------------------------------------------------------------ music callbacks
    def _on_track_changed(self, title: str, subtitle: str, kind: str, playing: bool) -> None:
        self.stage.set_track(title, subtitle, playing)

    def _on_music_state(self, playing: bool) -> None:
        item = self.music_engine.current_playable()
        if item:
            self.stage.set_track(item.title, item.subtitle, playing)

    def _on_music_loading(self, loading: bool, text: str) -> None:
        if loading:
            self.stage.set_track("正在获取乐曲…", text, False)

    def _on_music_error(self, message: str) -> None:
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
        quit_action = QAction("退出 Black", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray_menu = menu
        self.tray.show()
        self._update_tray_status()

    def _update_tray_status(self) -> None:
        if not self.tray:
            return
        active = self.store.active_subject()
        if active:
            self.tray.setToolTip(f"Black · 正在修习「{active['name']}」")
            self.tray_pause_action.setEnabled(True)
            self.tray_pause_action.setText("暂停当前计时")
        else:
            self.tray.setToolTip("Black · 在书桌边等你")
            self.tray_pause_action.setEnabled(False)
            self.tray_pause_action.setText("当前没有计时")

    def _tray_pause(self) -> None:
        if self.store.active():
            self.timer.pause()
            if self.tray:
                self.tray.showMessage("Black", "计时已暂停，今天的进度已经记下。", QSystemTrayIcon.Information, 2600)

    def _tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self._show_from_tray()

    def _show_from_tray(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def _tray_journal(self) -> None:
        self._show_from_tray()
        self._open_journal()

    def _quit(self) -> None:
        self._shutdown()

    def _about_to_quit(self) -> None:
        if self._shutting_down:
            return
        try:
            if self.store.active():
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
            if self.store.active():
                self.tray.showMessage(
                    "Black",
                    "我还在替你计时。双击托盘里的小黑猫，就能把我叫回来。",
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
        if hasattr(self, "size_grip"):
            self.size_grip.move(self.width() - 22, self.height() - 22)
            self.size_grip.raise_()
        if hasattr(self, "overlay") and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if hasattr(self, "stage"):
            self.stage.resume_animation()
        if hasattr(self, "overlay") and self.overlay.isVisible():
            self.overlay.setGeometry(self.rect())

    def hideEvent(self, event) -> None:  # noqa: N802
        if hasattr(self, "stage"):
            self.stage.pause_animation()
        super().hideEvent(event)
