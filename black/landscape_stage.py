from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
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

from .stage import CharacterStage, ElidedLabel, Equalizer, theme
from .widgets import Avatar


class LandscapeStage(CharacterStage):
    """A true full-width cinematic banner for landscape illustrations.

    Unlike the portrait stage, this widget sits above the pages rather than in
    a left column.  The wide art fills the banner, the date/exam live at the
    top edge, and the quote/actions/player form a bottom rail.  MainWindow
    changes the whole body from a horizontal split to a vertical stack when
    this stage is active.
    """

    ORIENTATION = "landscape"

    def _build_ui(self) -> None:
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setFixedHeight(298)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_StyledBackground, False)
        root = QVBoxLayout(self)
        root.setContentsMargins(22, 15, 22, 13)
        root.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(12)
        date_col = QVBoxLayout()
        date_col.setSpacing(1)
        self.date_label = QLabel("11月18日 · 周二")
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

        self.exam_label = QLabel("考试日期 · 待设定")
        self.exam_label.setObjectName("StageExam")
        self.exam_label.setFixedHeight(21)
        self.exam_label.setStyleSheet(
            f"font-size: 10px; color: {theme.GOLD}; background: rgba(8,13,20,130); "
            "border: 1px solid rgba(217,188,125,38); border-radius: 8px; padding: 2px 7px;"
        )
        self.exam_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        top.addWidget(self.exam_label, 0, Qt.AlignBottom)
        top.addStretch(1)

        self.mark_label = QLabel("TEYVAT DESK · LANDSCAPE")
        self.mark_label.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: rgba(243,221,170,125); "
            "letter-spacing: 2px;"
        )
        top.addWidget(self.mark_label, 0, Qt.AlignBottom)
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("StageTime")
        self.time_label.setStyleSheet(
            f"font-family: '{theme.MONO}'; font-size: 22px; color: {theme.TEXT}; letter-spacing: 1px;"
        )
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top.addWidget(self.time_label)
        root.addLayout(top)
        root.addStretch(1)

        bottom = QHBoxLayout()
        bottom.setSpacing(16)
        left = QVBoxLayout()
        left.setSpacing(2)
        self.stats_label = QLabel("今日专注 0m · 连习 0 天")
        self.stats_label.setObjectName("StageStats")
        self.stats_label.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        left.addWidget(self.stats_label)
        self.greeting_label = QLabel("晚上好，旅行者。")
        self.greeting_label.setObjectName("StageGreeting")
        self.greeting_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 22px; font-weight: 600; color: {theme.WHITE};"
        )
        left.addWidget(self.greeting_label)
        self.sub_label = QLabel("今晚的风很适合读书。")
        self.sub_label.setObjectName("StageSub")
        self.sub_label.setWordWrap(True)
        self.sub_label.setMaximumHeight(30)
        self.sub_label.setStyleSheet("font-size: 10px; color: rgba(238,231,218,190);")
        left.addWidget(self.sub_label)

        self.quote_card = QFrame()
        self.quote_card.setObjectName("StageQuote")
        self.quote_card.setMaximumWidth(480)
        self.quote_card.setStyleSheet(
            "QFrame#StageQuote { background: rgba(7,12,18,215); "
            "border: 1px solid rgba(217,188,125,60); border-radius: 11px; }"
        )
        qlay = QVBoxLayout(self.quote_card)
        qlay.setContentsMargins(10, 6, 10, 6)
        qlay.setSpacing(2)
        qtop = QHBoxLayout()
        qtop.setSpacing(6)
        self.quote_avatar = Avatar("black.png", 20, ring=theme.GOLD_BRIGHT)
        qtop.addWidget(self.quote_avatar)
        self.quote_name = QLabel("Black")
        self.quote_name.setObjectName("StageName")
        self.quote_name.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 10px; color: {theme.GOLD};"
        )
        qtop.addWidget(self.quote_name)
        self.quote_tag = QLabel("轻声")
        self.quote_tag.setStyleSheet(f"font-size: 8px; color: {theme.FAINT}; letter-spacing: 1px;")
        qtop.addWidget(self.quote_tag)
        qtop.addStretch(1)
        qlay.addLayout(qtop)
        self.quote_text = QLabel("……")
        self.quote_text.setWordWrap(True)
        self.quote_text.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 11px; color: rgba(241,235,224,230);"
        )
        qlay.addWidget(self.quote_text)
        left.addWidget(self.quote_card)
        bottom.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(6)
        right.addStretch(1)
        actions = QHBoxLayout()
        actions.setSpacing(5)
        self.chat_btn = QPushButton(" 说说话")
        self.chat_btn.setObjectName("StageAction")
        self.chat_btn.setIcon(theme.icon("chat", theme.GOLD_SOFT, 13))
        self.chat_btn.setCursor(Qt.PointingHandCursor)
        self.chat_btn.setFixedHeight(26)
        self.chat_btn.setFixedWidth(82)
        self.chat_btn.clicked.connect(self.chat_requested)
        self.pet_btn = QPushButton(" 摸摸头")
        self.pet_btn.setObjectName("StageAction")
        self.pet_btn.setIcon(theme.icon("cat", theme.GOLD_SOFT, 13))
        self.pet_btn.setCursor(Qt.PointingHandCursor)
        self.pet_btn.setFixedHeight(26)
        self.pet_btn.setFixedWidth(82)
        self.pet_btn.clicked.connect(self._on_pet)
        self.orientation_btn = QPushButton(" 竖屏")
        self.orientation_btn.setObjectName("StageAction")
        self.orientation_btn.setIcon(theme.icon("portrait", theme.GOLD_SOFT, 13))
        self.orientation_btn.setCursor(Qt.PointingHandCursor)
        self.orientation_btn.setFixedHeight(26)
        self.orientation_btn.setFixedWidth(76)
        self.orientation_btn.clicked.connect(self.orientation_requested)
        self.char_btn = QPushButton(" 角色")
        self.char_btn.setObjectName("StageAction")
        self.char_btn.setIcon(theme.icon("palette", theme.GOLD_SOFT, 13))
        self.char_btn.setCursor(Qt.PointingHandCursor)
        self.char_btn.setFixedHeight(26)
        self.char_btn.setFixedWidth(76)
        self.char_btn.setToolTip("切换看板角色")
        self.char_btn.clicked.connect(self.character_requested)
        for btn in (self.chat_btn, self.pet_btn, self.orientation_btn, self.char_btn):
            actions.addWidget(btn)
        actions.addStretch(1)
        right.addLayout(actions)

        self.player = QFrame()
        self.player.setObjectName("StagePlayer")
        self.player.setStyleSheet(
            "QFrame#StagePlayer { background: rgba(7,12,18,205); "
            "border: 1px solid rgba(217,188,125,45); border-radius: 10px; }"
        )
        play_lay = QHBoxLayout(self.player)
        play_lay.setContentsMargins(7, 5, 7, 5)
        play_lay.setSpacing(6)
        self.play_btn = QToolButton()
        self.play_btn.setObjectName("StagePlay")
        self.play_btn.setFixedSize(28, 28)
        self.play_btn.setIcon(theme.icon("play", theme.GOLD_BRIGHT, 12))
        self.play_btn.setIconSize(QSize(12, 12))
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
        self.track_title.setStyleSheet(f"font-size: 10px; color: {theme.TEXT};")
        self.track_sub = ElidedLabel("Black 原声 · 点击播放")
        self.track_sub.setObjectName("TrackSub")
        self.track_sub.setStyleSheet(f"font-size: 8px; color: {theme.MUTED};")
        text_col.addWidget(self.track_title)
        text_col.addWidget(self.track_sub)
        play_lay.addLayout(text_col, 1)
        self.next_btn = QToolButton()
        self.next_btn.setObjectName("StageIcon")
        self.next_btn.setFixedSize(22, 22)
        self.next_btn.setIcon(theme.icon("next", theme.MUTED, 12))
        self.next_btn.setIconSize(QSize(12, 12))
        self.next_btn.setCursor(Qt.PointingHandCursor)
        self.next_btn.setToolTip("下一首")
        self.next_btn.clicked.connect(self.music_next_requested)
        play_lay.addWidget(self.next_btn)
        right.addWidget(self.player)
        bottom.addLayout(right, 0)
        root.addLayout(bottom)

    def set_character(self, character: dict, look_id: str | None = None) -> None:
        super().set_character(character, look_id)
        self._element_name = str(character.get("element", "hydro"))
        self.set_orientation("landscape")
        self.update()

    def _build_cover(self) -> None:
        if self._art.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        target = QSize(self.width() + 14, self.height() + 14)
        scaled = self._art.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if scaled.width() > target.width() or scaled.height() > target.height():
            x = max(0, (scaled.width() - target.width()) // 2)
            y = max(0, int((scaled.height() - target.height()) * 0.25))
            scaled = scaled.copy(x, y, target.width(), target.height())
        self._cover = scaled

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.setClipPath(path)
        p.fillRect(self.rect(), QColor("#111b26"))
        if self._cover is None:
            self._build_cover()
        if self._cover:
            p.drawPixmap(
                QRectF(rect.left() - 7, rect.top() - 7, rect.width() + 14, rect.height() + 14).toRect(),
                self._cover,
            )

        top_grad = QLinearGradient(rect.topLeft(), QPointF(rect.left(), rect.top() + 120))
        top_grad.setColorAt(0, QColor(4, 8, 13, 225))
        top_grad.setColorAt(1, QColor(4, 8, 13, 0))
        p.fillRect(QRectF(rect.left(), rect.top(), rect.width(), 125), top_grad)
        bottom_grad = QLinearGradient(
            QPointF(rect.left(), rect.bottom() - 175),
            rect.bottomLeft(),
        )
        bottom_grad.setColorAt(0, QColor(5, 9, 14, 0))
        bottom_grad.setColorAt(0.55, QColor(5, 9, 14, 180))
        bottom_grad.setColorAt(1, QColor(5, 9, 14, 252))
        p.fillRect(QRectF(rect.left(), rect.bottom() - 180, rect.width(), 180), bottom_grad)
        left_grad = QLinearGradient(rect.topLeft(), QPointF(rect.left() + 430, rect.top()))
        left_grad.setColorAt(0, QColor(5, 9, 14, 110))
        left_grad.setColorAt(1, QColor(5, 9, 14, 0))
        p.fillRect(QRectF(rect.left(), rect.top(), 450, rect.height()), left_grad)

        glyph = theme.element_pixmap(getattr(self, "_element_name", "hydro"), 256, "white")
        if glyph is not None:
            p.setOpacity(0.06)
            p.drawPixmap(QRectF(rect.right() - 260, rect.bottom() - 230, 220, 220), glyph, QRectF(glyph.rect()))
            p.setOpacity(1.0)

        self._paint_particles(p, rect)
        self._paint_motes(p, rect)
        self._paint_hearts(p)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(217, 188, 125, 125), 1.2))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(QColor(255, 239, 205, 28), 1.0))
        p.drawRoundedRect(rect.adjusted(3.5, 3.5, -3.5, -3.5), 13, 13)
        self._paint_corners(p, rect)

    def _on_pet(self) -> None:
        self.add_hearts(QPointF(self.width() * 0.55, self.height() * 0.52))
        self.petted.emit()
