from __future__ import annotations

import math
import random
from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme as _theme
from .characters import get_look
from .paths import IMAGES, avatar_path
from .widgets import Avatar, Dot, IconButton


class _StagePalette:
    """The stage palette follows the desk theme.

    Night keeps the original deep-navy island; daylight uses warm parchment,
    dark ink and antique gold so the illustration no longer sits on a black
    slab.
    """

    @property
    def GOLD(self):
        return "#987536" if _theme.is_light() else "#d9bc7d"

    @property
    def GOLD_BRIGHT(self):
        return "#7b5a24" if _theme.is_light() else "#f3ddaa"

    @property
    def GOLD_SOFT(self):
        return "#8a6b3e" if _theme.is_light() else "#a98e5c"

    @property
    def TEXT(self):
        return "#2f271c" if _theme.is_light() else "#eee7da"

    @property
    def TEXT_SOFT(self):
        return "#4c4031" if _theme.is_light() else "#d7cdbb"

    @property
    def MUTED(self):
        return "#6b5b46" if _theme.is_light() else "#a89d8b"

    @property
    def FAINT(self):
        return "#8b7962" if _theme.is_light() else "#858a82"

    @property
    def TEAL(self):
        return "#2f817d" if _theme.is_light() else "#72d3ce"

    @property
    def ROSE(self):
        return "#b05d59" if _theme.is_light() else "#e39a91"

    @property
    def WHITE(self):
        return "#2b241a" if _theme.is_light() else "#fbf7ee"

    def __getattr__(self, name):
        return getattr(_theme, name)


theme = _StagePalette()


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = text
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setTextFormat(Qt.PlainText)
        super().setText(text)
        self.setToolTip(text)

    def setText(self, text: str) -> None:  # noqa: N802
        self._full_text = text
        self.setToolTip(text)
        self._apply_elide()

    def fullText(self) -> str:  # noqa: N802
        return self._full_text

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._apply_elide()

    def _apply_elide(self) -> None:
        fm = QFontMetrics(self.font())
        width = max(20, self.width() - 2)
        elided = fm.elidedText(self._full_text, Qt.ElideRight, width)
        QLabel.setText(self, elided)


class Equalizer(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._playing = False
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._tick)

    def set_playing(self, playing: bool) -> None:
        self._playing = playing
        if playing and not self._timer.isActive():
            self._timer.start()
        elif not playing:
            self._timer.stop()
        self.update()

    def _tick(self) -> None:
        self._phase += 0.45
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setPen(Qt.NoPen)
        for i in range(3):
            if self._playing:
                h = 4 + (math.sin(self._phase + i * 1.4) * 0.5 + 0.5) * 9
            else:
                h = 4 + i
            color = QColor(theme.GOLD if i == 1 else theme.TEAL)
            color.setAlpha(170 if self._playing else 75)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(i * 5.2, 16 - h, 2.6, h), 1.2, 1.2)


class CharacterStage(QWidget):
    petted = pyqtSignal()
    chat_requested = pyqtSignal()
    character_requested = pyqtSignal()
    music_toggle_requested = pyqtSignal()
    music_next_requested = pyqtSignal()
    music_open_requested = pyqtSignal()
    orientation_requested = pyqtSignal()
    ORIENTATION = "portrait"

    def __init__(self, art_name: str = "art_snow.jpg", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("darkIsland", True)
        self.setFixedWidth(362)
        self.setMinimumHeight(540)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._art_name = art_name
        self._art = QPixmap()
        self._cover: QPixmap | None = None
        self._look_kind = "painting"
        self._accent = theme.GOLD
        self._character_name = ""
        self._phase = 0.0
        self._hearts: list[dict] = []
        self._rng = random.Random(11)
        self._particles = [
            {
                "x": self._rng.random(),
                "y": self._rng.random(),
                "r": self._rng.uniform(0.8, 2.4),
                "speed": self._rng.uniform(0.008, 0.03),
                "phase": self._rng.uniform(0, 6.28),
                "gold": self._rng.random() < 0.62,
            }
            for _ in range(24)
        ]
        _theme.begin_dark_island()
        try:
            self._build_ui()
            self.set_art(art_name)
            self._timer = QTimer(self)
            self._timer.setInterval(50)
            self._timer.timeout.connect(self._animate)
            self._timer.start()
            self._cover_timer = QTimer(self)
            self._cover_timer.setSingleShot(True)
            self._cover_timer.setInterval(35)
            self._cover_timer.timeout.connect(self._refresh_cover)
            self.setStyleSheet(self._local_qss())
            self.set_orientation(self.ORIENTATION)
        finally:
            _theme.end_dark_island()

    def set_orientation(self, orientation: str) -> None:
        self.ORIENTATION = str(orientation)
        landscape = self.ORIENTATION == "landscape"
        if hasattr(self, "orientation_btn"):
            self.orientation_btn.setText(" 竖屏" if landscape else " 横屏")
            self.orientation_btn.setIcon(
                theme.icon("portrait" if landscape else "landscape", theme.GOLD_SOFT, 14)
            )
            self.orientation_btn.setToolTip("切换回竖屏立绘" if landscape else "切换到横屏立绘")

    # ------------------------------------------------------------------ ui
    def _local_qss(self) -> str:
        light = _theme.is_light()
        quote_bg = "rgba(255,250,240,238)" if light else "rgba(7,12,18,210)"
        quote_border = "rgba(152,117,54,75)" if light else "rgba(217,188,125,55)"
        player_bg = "rgba(255,250,240,232)" if light else "rgba(7,12,18,198)"
        player_border = "rgba(152,117,54,65)" if light else "rgba(217,188,125,45)"
        exam_bg = "rgba(255,250,240,215)" if light else "rgba(8,13,20,120)"
        exam_border = "rgba(152,117,54,65)" if light else "rgba(217,188,125,38)"
        action_bg = "rgba(255,250,240,220)" if light else "rgba(8,14,21,165)"
        action_border = "rgba(152,117,54,65)" if light else "rgba(217,188,125,48)"
        action_hover = "rgba(152,117,54,22)" if light else "rgba(217,188,125,25)"
        play_bg = "rgba(152,117,54,20)" if light else "rgba(217,188,125,22)"
        play_border = "rgba(152,117,54,90)" if light else "rgba(217,188,125,70)"
        return f"""
        QFrame#StageQuote {{
            background: {quote_bg};
            border: 1px solid {quote_border};
            border-radius: 12px;
        }}
        QFrame#StagePlayer {{
            background: {player_bg};
            border: 1px solid {player_border};
            border-radius: 11px;
        }}
        QLabel#StageDate {{ font-family: "{theme.SERIF}"; font-size: 18px; font-weight: 600; color: {theme.WHITE}; }}
        QLabel#StageLocation {{ font-size: 9px; color: {theme.GOLD_SOFT}; letter-spacing: 1px; }}
        QLabel#StageTime {{ font-family: "{theme.MONO}"; font-size: 20px; color: {theme.TEXT}; letter-spacing: 1px; }}
        QLabel#StageExam {{
            font-size: 10px; color: {theme.GOLD}; background: {exam_bg};
            border: 1px solid {exam_border}; border-radius: 8px; padding: 2px 7px;
        }}
        QLabel#StageGreeting {{ font-family: "{theme.SERIF}"; font-size: 23px; font-weight: 600; color: {theme.WHITE}; }}
        QLabel#StageSub {{ font-size: 11px; color: {theme.TEXT_SOFT}; }}
        QLabel#StageStats {{ font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px; }}
        QLabel#StageName {{ font-family: "{theme.SERIF}"; font-size: 11px; color: {theme.GOLD}; }}
        QLabel#StageQuoteText {{ font-family: "{theme.SERIF}"; font-size: 12px; color: {theme.TEXT}; }}
        QLabel#TrackTitle {{ font-size: 11px; color: {theme.TEXT}; }}
        QLabel#TrackSub {{ font-size: 9px; color: {theme.MUTED}; }}
        QPushButton#StageAction {{
            background: {action_bg};
            border: 1px solid {action_border};
            border-radius: 9px;
            color: {theme.TEXT_SOFT};
            font-size: 11px;
            padding: 4px 10px;
        }}
        QPushButton#StageAction:hover {{
            background: {action_hover};
            border-color: {theme.GOLD};
            color: {theme.GOLD_BRIGHT};
        }}
        QToolButton#StagePlay {{
            background: {play_bg};
            border: 1px solid {play_border};
            border-radius: 15px;
        }}
        QToolButton#StagePlay:hover {{ background: {action_hover}; }}
        QToolButton#StageIcon {{ border-radius: 7px; }}
        QToolButton#StageIcon:hover {{ background: {action_hover}; }}
        """

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(22, 19, 22, 18)
        lay.setSpacing(0)

        # top date/time
        top = QHBoxLayout()
        top.setSpacing(8)
        date_col = QVBoxLayout()
        date_col.setSpacing(1)
        self.date_label = QLabel("11月16日 · 周日")
        self.date_label.setObjectName("StageDate")
        self.date_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 18px; font-weight: 600; color: {theme.WHITE};"
        )
        self.location = QLabel("尘歌壶 · 晴")
        self.location.setObjectName("StageLocation")
        self.location.setStyleSheet(f"font-size: 9px; color: {theme.GOLD_SOFT}; letter-spacing: 1px;")
        date_col.addWidget(self.date_label)
        date_col.addWidget(self.location)
        top.addLayout(date_col)
        top.addStretch(1)
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("StageTime")
        self.time_label.setStyleSheet(
            f"font-family: '{theme.MONO}'; font-size: 21px; color: {theme.TEXT}; letter-spacing: 1px;"
        )
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.time_label)
        lay.addLayout(top)

        self.exam_label = QLabel("考试日期 · 待设定")
        self.exam_label.setObjectName("StageExam")
        self.exam_label.setFixedHeight(21)
        self.exam_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        exam_row = QHBoxLayout()
        exam_row.setContentsMargins(0, 9, 0, 0)
        exam_row.addWidget(self.exam_label)
        exam_row.addStretch(1)
        lay.addLayout(exam_row)

        lay.addStretch(1)

        # quote bubble
        self.quote_card = QFrame()
        self.quote_card.setObjectName("StageQuote")
        qlay = QVBoxLayout(self.quote_card)
        qlay.setContentsMargins(12, 10, 12, 10)
        qlay.setSpacing(4)
        qtop = QHBoxLayout()
        qtop.setSpacing(7)
        self.quote_avatar = Avatar("black.png", 24, ring=theme.GOLD_BRIGHT)
        qtop.addWidget(self.quote_avatar)
        self.quote_name = QLabel("Black")
        self.quote_name.setObjectName("StageName")
        self.quote_name.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 11px; color: {theme.GOLD};"
        )
        qtop.addWidget(self.quote_name)
        qtop.addStretch(1)
        self.quote_tag = QLabel("轻声")
        self.quote_tag.setStyleSheet(f"font-size: 8px; color: {theme.FAINT}; letter-spacing: 1px;")
        qtop.addWidget(self.quote_tag)
        qlay.addLayout(qtop)
        self.quote_text = QLabel("……")
        self.quote_text.setObjectName("StageQuoteText")
        self.quote_text.setWordWrap(True)
        qlay.addWidget(self.quote_text)
        self.quote_card.setMaximumWidth(316)
        lay.addWidget(self.quote_card, 0, Qt.AlignLeft)

        lay.addSpacing(12)

        # stats + greeting
        self.stats_label = QLabel("今日专注 0m · 连习 0 天")
        self.stats_label.setObjectName("StageStats")
        self.stats_label.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        lay.addWidget(self.stats_label)
        lay.addSpacing(2)
        self.greeting_label = QLabel("晚上好，旅行者。")
        self.greeting_label.setObjectName("StageGreeting")
        self.greeting_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 23px; font-weight: 600; color: {theme.WHITE};"
        )
        lay.addWidget(self.greeting_label)
        self.sub_label = QLabel("今晚的风很适合读书。")
        self.sub_label.setObjectName("StageSub")
        self.sub_label.setWordWrap(True)
        self.sub_label.setMaximumHeight(34)
        lay.addWidget(self.sub_label)

        lay.addSpacing(9)
        actions = QHBoxLayout()
        actions.setSpacing(6)
        self.chat_btn = QPushButton(" 说说话")
        self.chat_btn.setObjectName("StageAction")
        self.chat_btn.setIcon(theme.icon("chat", theme.GOLD_SOFT, 14))
        self.chat_btn.setCursor(Qt.PointingHandCursor)
        self.chat_btn.setFixedHeight(27)
        self.chat_btn.clicked.connect(self.chat_requested)
        self.pet_btn = QPushButton(" 摸摸头")
        self.pet_btn.setObjectName("StageAction")
        self.pet_btn.setIcon(theme.icon("cat", theme.GOLD_SOFT, 14))
        self.pet_btn.setCursor(Qt.PointingHandCursor)
        self.pet_btn.setFixedHeight(27)
        self.pet_btn.clicked.connect(self._on_pet)
        self.orientation_btn = QPushButton(" 横屏")
        self.orientation_btn.setObjectName("StageAction")
        self.orientation_btn.setIcon(theme.icon("landscape", theme.GOLD_SOFT, 14))
        self.orientation_btn.setCursor(Qt.PointingHandCursor)
        self.orientation_btn.setFixedHeight(27)
        self.orientation_btn.setToolTip("切换到横屏立绘")
        self.orientation_btn.clicked.connect(self.orientation_requested)
        self.char_btn = QPushButton(" 角色")
        self.char_btn.setObjectName("StageAction")
        self.char_btn.setIcon(theme.icon("palette", theme.GOLD_SOFT, 14))
        self.char_btn.setCursor(Qt.PointingHandCursor)
        self.char_btn.setFixedHeight(27)
        self.char_btn.setToolTip("切换看板角色")
        self.char_btn.clicked.connect(self.character_requested)
        actions.addWidget(self.chat_btn)
        actions.addWidget(self.pet_btn)
        actions.addWidget(self.orientation_btn)
        actions.addStretch(1)
        actions.addWidget(self.char_btn)
        lay.addLayout(actions)

        lay.addSpacing(9)

        # compact music player
        self.player = QFrame()
        self.player.setObjectName("StagePlayer")
        play_lay = QHBoxLayout(self.player)
        play_lay.setContentsMargins(8, 6, 8, 6)
        play_lay.setSpacing(7)
        self.play_btn = QToolButton()
        self.play_btn.setObjectName("StagePlay")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.setIcon(theme.icon("play", theme.GOLD_BRIGHT, 13))
        self.play_btn.setIconSize(QSize(13, 13))
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setToolTip("播放 / 暂停 BGM")
        self.play_btn.clicked.connect(self.music_toggle_requested)
        play_lay.addWidget(self.play_btn)
        self.eq = Equalizer()
        play_lay.addWidget(self.eq)
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        self.track_title = ElidedLabel("星落之庭")
        self.track_title.setObjectName("TrackTitle")
        self.track_title.setStyleSheet(f"font-size: 11px; color: {theme.TEXT};")
        self.track_sub = ElidedLabel("Black 原声 · 点击播放")
        self.track_sub.setObjectName("TrackSub")
        self.track_sub.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        text_col.addWidget(self.track_title)
        text_col.addWidget(self.track_sub)
        play_lay.addLayout(text_col, 1)
        self.next_btn = QToolButton()
        self.next_btn.setObjectName("StageIcon")
        self.next_btn.setFixedSize(24, 24)
        self.next_btn.setIcon(theme.icon("next", theme.MUTED, 13))
        self.next_btn.setIconSize(QSize(13, 13))
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setToolTip("下一首")
        self.next_btn.clicked.connect(self.music_next_requested)
        play_lay.addWidget(self.next_btn)
        lay.addWidget(self.player)

    # ------------------------------------------------------------------ painting
    def set_character(self, character: dict, look_id: str | None = None) -> None:
        """Switch the stage look while keeping all Black behaviour untouched."""
        self._character_name = str(character.get("name", ""))
        self._look_kind = "painting"
        self._accent = str(character.get("color", theme.GOLD))
        look = get_look(character, look_id)
        self.set_art(str(look.get("art") or "art_snow.jpg"))

    def set_art(self, art_name: str) -> None:
        path = IMAGES / art_name
        if not path.exists():
            visual = list(IMAGES.glob("art_*.jpg"))
            if visual:
                path = visual[0]
                art_name = path.name
        pix = QPixmap(str(path))
        if pix.isNull():
            pix = QPixmap(800, 1200)
            pix.fill(QColor("#152333"))
        self._art_name = art_name
        self._art = pix
        self._cover = None
        self._build_cover()
        self.update()

    def _build_cover(self) -> None:
        if self._art.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        target = QSize(self.width() + 20, self.height() + 20)
        scaled = self._art.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if scaled.width() > target.width() or scaled.height() > target.height():
            x = max(0, (scaled.width() - target.width()) // 2)
            y = max(0, (scaled.height() - target.height()) // 2)
            scaled = scaled.copy(x, y, target.width(), target.height())
        self._cover = scaled

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        # Rebuild the large illustration only after the drag has settled; doing
        # it on every mouse-move was the main source of resize flicker.
        if hasattr(self, "_cover_timer"):
            self._cover_timer.start()
        if hasattr(self, "quote_text"):
            QTimer.singleShot(0, self._fit_quote_text)

    def _refresh_cover(self) -> None:
        self._cover = None
        self._build_cover()
        self.update()

    def _fit_quote_text(self) -> None:
        if not hasattr(self, "quote_text"):
            return
        width = self.quote_text.width()
        if width < 80:
            width = 380 if self.ORIENTATION == "landscape" else 292
        needed = self.quote_text.heightForWidth(max(120, width))
        if needed > 0:
            self.quote_text.setMinimumHeight(needed + 2)
            self.quote_text.setMaximumHeight(needed + 2)
            if hasattr(self, "quote_card"):
                self.quote_card.adjustSize()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        clip = QPainterPath()
        clip.addRoundedRect(rect, 16, 16)
        p.setClipPath(clip)
        light = _theme.is_light()
        p.fillRect(self.rect(), QColor("#f1e7d8" if light else "#111b26"))

        if self._cover is None:
            self._build_cover()
        if self._cover:
            # The illustration itself is intentionally pinned in place.  All
            # motion lives in the particles, light sweep and click reactions.
            target = QRectF(
                rect.left() - 6,
                rect.top() - 6,
                rect.width() + 12,
                rect.height() + 12,
            )
            p.drawPixmap(target.toRect(), self._cover)

        # a very soft diagonal light sweep (overlay only; the art does not move)
        sweep_center = (self._phase * 24) % (self.width() + 420) - 210
        sweep = QLinearGradient(
            QPointF(rect.left() + sweep_center - 180, rect.top()),
            QPointF(rect.left() + sweep_center + 180, rect.bottom()),
        )
        sweep.setColorAt(0.0, QColor(255, 245, 220, 0))
        sweep.setColorAt(0.5, QColor(255, 245, 220, 9 if not light else 20))
        sweep.setColorAt(1.0, QColor(255, 245, 220, 0))
        p.fillRect(rect, sweep)

        # top and bottom cinematic veils
        if light:
            top_grad = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + rect.height() * 0.28))
            top_grad.setColorAt(0, QColor(252, 247, 237, 225))
            top_grad.setColorAt(1, QColor(252, 247, 237, 0))
            p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.3), top_grad)
            bottom_grad = QLinearGradient(QPointF(rect.left(), rect.bottom() - rect.height() * 0.62), rect.bottomLeft())
            bottom_grad.setColorAt(0, QColor(247, 240, 228, 0))
            bottom_grad.setColorAt(0.5, QColor(247, 240, 228, 185))
            bottom_grad.setColorAt(1, QColor(247, 240, 228, 252))
            p.fillRect(QRectF(rect.left(), rect.bottom() - rect.height() * 0.64, rect.width(), rect.height() * 0.64), bottom_grad)
            side = QLinearGradient(rect.topLeft(), QPointF(rect.left() + 52, rect.top()))
            side.setColorAt(0, QColor(252, 247, 237, 120))
            side.setColorAt(1, QColor(252, 247, 237, 0))
            p.fillRect(QRectF(rect.left(), rect.top(), 62, rect.height()), side)
            right = QLinearGradient(QPointF(rect.right() - 52, rect.top()), QPointF(rect.right(), rect.top()))
            right.setColorAt(0, QColor(252, 247, 237, 0))
            right.setColorAt(1, QColor(252, 247, 237, 95))
            p.fillRect(QRectF(rect.right() - 62, rect.top(), 62, rect.height()), right)
        else:
            top_grad = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + rect.height() * 0.28))
            top_grad.setColorAt(0, QColor(4, 8, 13, 225))
            top_grad.setColorAt(1, QColor(4, 8, 13, 0))
            p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.3), top_grad)
            bottom_grad = QLinearGradient(QPointF(rect.left(), rect.bottom() - rect.height() * 0.62), rect.bottomLeft())
            bottom_grad.setColorAt(0, QColor(5, 9, 14, 0))
            bottom_grad.setColorAt(0.5, QColor(5, 9, 14, 178))
            bottom_grad.setColorAt(1, QColor(5, 9, 14, 250))
            p.fillRect(QRectF(rect.left(), rect.bottom() - rect.height() * 0.64, rect.width(), rect.height() * 0.64), bottom_grad)
            side = QLinearGradient(rect.topLeft(), QPointF(rect.left() + 52, rect.top()))
            side.setColorAt(0, QColor(5, 9, 14, 110))
            side.setColorAt(1, QColor(5, 9, 14, 0))
            p.fillRect(QRectF(rect.left(), rect.top(), 62, rect.height()), side)
            right = QLinearGradient(QPointF(rect.right() - 52, rect.top()), QPointF(rect.right(), rect.top()))
            right.setColorAt(0, QColor(5, 9, 14, 0))
            right.setColorAt(1, QColor(5, 9, 14, 95))
            p.fillRect(QRectF(rect.right() - 62, rect.top(), 62, rect.height()), right)

        self._paint_particles(p, rect)
        self._paint_hearts(p)

        # frame, corners and ornament
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(217, 188, 125, 120), 1.2))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(QColor(255, 239, 205, 28), 1.0))
        p.drawRoundedRect(rect.adjusted(3.5, 3.5, -3.5, -3.5), 13, 13)
        self._paint_corners(p, rect)
        self._paint_motes(p, rect)

    def _paint_corners(self, p: QPainter, rect: QRectF) -> None:
        gold = QColor(theme.GOLD)
        gold.setAlpha(155)
        p.setPen(QPen(gold, 1.2))
        inset = 12
        length = 22
        for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            x = rect.left() + inset if sx > 0 else rect.right() - inset
            y = rect.top() + inset if sy > 0 else rect.bottom() - inset
            p.drawLine(QPointF(x, y), QPointF(x + sx * length, y))
            p.drawLine(QPointF(x, y), QPointF(x, y + sy * length))
        # top centre diamond
        cx = rect.center().x()
        top = rect.top()
        theme.draw_diamond(p, QRectF(cx - 4, top - 3, 8, 8), QColor(theme.GOLD_BRIGHT), True)
        p.setPen(QPen(QColor(theme.GOLD), 1.2))
        p.drawLine(QPointF(cx - 34, top), QPointF(cx - 8, top))
        p.drawLine(QPointF(cx + 8, top), QPointF(cx + 34, top))

    def _paint_particles(self, p: QPainter, rect: QRectF) -> None:
        for pt in self._particles:
            x = rect.left() + pt["x"] * rect.width() + math.sin(self._phase * 0.7 + pt["phase"]) * 8
            y_norm = (pt["y"] - self._phase * pt["speed"]) % 1.0
            y = rect.top() + y_norm * rect.height()
            twinkle = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self._phase * 2.1 + pt["phase"]))
            color = QColor(theme.GOLD_BRIGHT if pt["gold"] else theme.TEAL)
            color.setAlpha(int(50 + 105 * twinkle))
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(x, y), pt["r"], pt["r"])
            if pt["r"] > 1.8:
                p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), color.alpha() // 3), 0.7))
                p.drawLine(QPointF(x - pt["r"] * 2.2, y), QPointF(x + pt["r"] * 2.2, y))
                p.drawLine(QPointF(x, y - pt["r"] * 2.2), QPointF(x, y + pt["r"] * 2.2))

    def _paint_motes(self, p: QPainter, rect: QRectF) -> None:
        rng = random.Random(22)
        for _ in range(14):
            x = rng.uniform(rect.left() + 20, rect.right() - 20)
            y = rng.uniform(rect.top() + 20, rect.top() + rect.height() * 0.5)
            theme.draw_star(p, QPointF(x, y), rng.uniform(1.0, 2.2), QColor(240, 220, 170, rng.randint(30, 100)))

    def _paint_hearts(self, p: QPainter) -> None:
        for heart in self._hearts:
            x = heart["x"] + math.sin(heart["t"] * 4 + heart["seed"]) * 8
            y = heart["y"] - heart["t"] * 38
            alpha = max(0, int(220 * (1 - heart["t"] / 1.4)))
            if alpha <= 0:
                continue
            color = QColor(theme.ROSE)
            color.setAlpha(alpha)
            size = heart["size"]
            path = QPainterPath()
            path.moveTo(x, y + size * 0.7)
            path.cubicTo(x - size * 1.2, y - size * 0.25, x - size * 0.45, y - size * 1.0, x, y - size * 0.35)
            path.cubicTo(x + size * 0.45, y - size * 1.0, x + size * 1.2, y - size * 0.25, x, y + size * 0.7)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawPath(path)

    # ------------------------------------------------------------------ animation
    def _animate(self) -> None:
        self._phase += 0.040
        for heart in self._hearts:
            heart["t"] += 0.045
        self._hearts = [h for h in self._hearts if h["t"] < 1.4]
        self.update()

    def pause_animation(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    def resume_animation(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def _on_pet(self) -> None:
        self.add_hearts(QPointF(self.width() * 0.5, self.height() * 0.55))
        self.petted.emit()

    def add_hearts(self, point: QPointF) -> None:
        for i in range(5):
            self._hearts.append(
                {
                    "x": point.x() + self._rng.uniform(-30, 30),
                    "y": point.y() + self._rng.uniform(-10, 15),
                    "t": 0.0,
                    "size": self._rng.uniform(4, 8),
                    "seed": self._rng.uniform(0, 6.28),
                }
            )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.add_hearts(QPointF(event.pos()))
            self.petted.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    # ------------------------------------------------------------------ updates
    def set_quote(self, quote: dict, avatar_file: str) -> None:
        self.quote_avatar.set_source(avatar_path(avatar_file))
        self.quote_name.setText(str(quote.get("speaker", "Black")))
        text = str(quote.get("text", ""))
        self.quote_text.setText(text)
        self.quote_tag.setText("轻声")
        # Let the quote card grow with the actual text instead of clipping long
        # character lines (the 彩特琳德 card was the visible failure).
        width = 440 if self.ORIENTATION == "landscape" else 292
        if self.quote_text.width() > 80:
            width = self.quote_text.width()
        needed = self.quote_text.heightForWidth(max(120, width))
        if needed <= 0:
            needed = QFontMetrics(self.quote_text.font()).lineSpacing()
        self.quote_text.setMinimumHeight(needed + 2)
        self.quote_text.setMaximumHeight(needed + 2)
        self.quote_card.adjustSize()
        # small fade so the bubble feels alive
        from PyQt5.QtWidgets import QGraphicsOpacityEffect
        from PyQt5.QtCore import QPropertyAnimation

        self._quote_seq = getattr(self, "_quote_seq", 0) + 1
        seq = self._quote_seq
        effect = QGraphicsOpacityEffect(self.quote_card)
        effect.setOpacity(0.35)
        self.quote_card.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(420)
        anim.setStartValue(0.35)
        anim.setEndValue(1.0)
        anim.finished.connect(lambda: self.quote_card.setGraphicsEffect(None) if seq == getattr(self, "_quote_seq", 0) else None)
        self._quote_anim = anim
        anim.start()

    def set_greeting(self, greeting: str, sub: str) -> None:
        self.greeting_label.setText(greeting)
        self.sub_label.setText(sub)

    def set_stats(self, today_text: str, streak: int) -> None:
        self.stats_label.setText(f"今日专注 {today_text}  ·  连习 {streak} 天")

    def set_exam(self, text: str) -> None:
        self.exam_label.setText(text)

    def set_date(self, date_text: str, location: str = "尘歌壶 · 晴") -> None:
        self.date_label.setText(date_text)
        self.location.setText(location)

    def set_time(self, time_text: str) -> None:
        self.time_label.setText(time_text)

    def set_track(self, title: str, subtitle: str, playing: bool, progress: float = 0.0) -> None:
        self.track_title.setText(title or "尚未选择乐曲")
        self.track_sub.setText(subtitle)
        self.play_btn.setIcon(theme.icon("pause" if playing else "play", theme.GOLD_BRIGHT, 13))
        self.play_btn.setToolTip("暂停 BGM" if playing else "播放 BGM")
        self.eq.set_playing(playing)

