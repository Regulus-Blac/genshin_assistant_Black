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
    """A wide, cinematic character card for landscape illustrations.

    The left column becomes a 600px postcard: the wide artwork sits on top,
    with the Black quote, stats and compact player in a dark glass panel below.
    It shares CharacterStage's public API so MainWindow can swap it without
    touching any page or timer logic.
    """

    ORIENTATION = "landscape"

    def _build_ui(self) -> None:
        self.setFixedWidth(600)
        self.setMinimumHeight(560)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._top_h = 338
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # transparent overlay over the painted wide illustration
        top = QWidget()
        top.setFixedHeight(self._top_h)
        top.setAttribute(Qt.WA_StyledBackground, False)
        tl = QVBoxLayout(top)
        tl.setContentsMargins(20, 16, 20, 0)
        tl.setSpacing(0)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
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
        top_row.addLayout(date_col)
        top_row.addStretch(1)
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("StageTime")
        self.time_label.setStyleSheet(
            f"font-family: '{theme.MONO}'; font-size: 21px; color: {theme.TEXT}; letter-spacing: 1px;"
        )
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_row.addWidget(self.time_label)
        tl.addLayout(top_row)

        self.exam_label = QLabel("考试日期 · 待设定")
        self.exam_label.setObjectName("StageExam")
        self.exam_label.setFixedHeight(21)
        self.exam_label.setStyleSheet(
            f"font-size: 10px; color: {theme.GOLD}; background: rgba(8,13,20,130); "
            "border: 1px solid rgba(217,188,125,38); border-radius: 8px; padding: 2px 7px;"
        )
        self.exam_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        exam_row = QHBoxLayout()
        exam_row.setContentsMargins(0, 9, 0, 0)
        exam_row.addWidget(self.exam_label)
        exam_row.addStretch(1)
        tl.addLayout(exam_row)
        tl.addStretch(1)

        mark = QLabel("TEYVAT DESK  ·  LANDSCAPE")
        mark.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: rgba(243,221,170,120); "
            "letter-spacing: 2px;"
        )
        tl.addWidget(mark, 0, Qt.AlignRight)
        root.addWidget(top)

        info = QWidget()
        info.setAttribute(Qt.WA_StyledBackground, False)
        il = QVBoxLayout(info)
        il.setContentsMargins(18, 10, 18, 12)
        il.setSpacing(5)

        self.stats_label = QLabel("今日专注 0m · 连习 0 天")
        self.stats_label.setObjectName("StageStats")
        self.stats_label.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        il.addWidget(self.stats_label)

        self.greeting_label = QLabel("晚上好，旅行者。")
        self.greeting_label.setObjectName("StageGreeting")
        self.greeting_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 23px; font-weight: 600; color: {theme.WHITE};"
        )
        il.addWidget(self.greeting_label)
        self.sub_label = QLabel("今晚的风很适合读书。")
        self.sub_label.setObjectName("StageSub")
        self.sub_label.setWordWrap(True)
        self.sub_label.setMaximumHeight(34)
        self.sub_label.setStyleSheet("font-size: 11px; color: rgba(238,231,218,185);")
        il.addWidget(self.sub_label)

        self.quote_card = QFrame()
        self.quote_card.setObjectName("StageQuote")
        self.quote_card.setStyleSheet(
            "QFrame#StageQuote { background: rgba(7,12,18,210); "
            "border: 1px solid rgba(217,188,125,55); border-radius: 12px; }"
        )
        qlay = QVBoxLayout(self.quote_card)
        qlay.setContentsMargins(11, 8, 11, 8)
        qlay.setSpacing(3)
        qtop = QHBoxLayout()
        qtop.setSpacing(7)
        self.quote_avatar = Avatar("black.png", 23, ring=theme.GOLD_BRIGHT)
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
        self.quote_text.setWordWrap(True)
        self.quote_text.setMaximumHeight(54)
        self.quote_text.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 12px; color: rgba(241,235,224,225);"
        )
        qlay.addWidget(self.quote_text)
        il.addWidget(self.quote_card)

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
        self.char_btn = QPushButton(" 角色")
        self.char_btn.setObjectName("StageAction")
        self.char_btn.setIcon(theme.icon("palette", theme.GOLD_SOFT, 14))
        self.char_btn.setCursor(Qt.PointingHandCursor)
        self.char_btn.setFixedHeight(27)
        self.char_btn.setToolTip("切换看板角色")
        self.char_btn.clicked.connect(self.character_requested)
        actions.addWidget(self.chat_btn)
        actions.addWidget(self.pet_btn)
        actions.addStretch(1)
        actions.addWidget(self.char_btn)
        il.addLayout(actions)

        self.player = QFrame()
        self.player.setObjectName("StagePlayer")
        self.player.setStyleSheet(
            "QFrame#StagePlayer { background: rgba(7,12,18,198); "
            "border: 1px solid rgba(217,188,125,45); border-radius: 11px; }"
        )
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
        il.addWidget(self.player)
        il.addStretch(1)
        self.footer_hint = QLabel("Black · 替你看时间")
        self.footer_hint.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 9px; color: rgba(168,157,139,150); "
            "letter-spacing: 1px;"
        )
        il.addWidget(self.footer_hint)
        root.addWidget(info, 1)

    def set_character(self, character: dict, look_id: str | None = None) -> None:
        super().set_character(character, look_id)
        self._element_name = str(character.get("element", "hydro"))
        if hasattr(self, "footer_hint"):
            self.footer_hint.setText(f"{self._character_name} · 此刻也在这里")
        self.update()

    def _build_cover(self) -> None:
        if self._art.isNull() or self.width() <= 0:
            return
        target = QSize(self.width() + 12, self._top_h + 12)
        scaled = self._art.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        if scaled.width() > target.width() or scaled.height() > target.height():
            x = max(0, (scaled.width() - target.width()) // 2)
            y = max(0, (scaled.height() - target.height()) // 2)
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
        art_rect = QRectF(rect.left(), rect.top(), rect.width(), self._top_h)
        if self._cover:
            p.drawPixmap(art_rect.toRect(), self._cover)

        top_grad = QLinearGradient(art_rect.topLeft(), QPointF(art_rect.left(), art_rect.top() + 120))
        top_grad.setColorAt(0, QColor(4, 8, 13, 220))
        top_grad.setColorAt(1, QColor(4, 8, 13, 0))
        p.fillRect(QRectF(art_rect.left(), art_rect.top(), art_rect.width(), 130), top_grad)
        bottom_grad = QLinearGradient(
            QPointF(art_rect.left(), art_rect.bottom() - 150),
            art_rect.bottomLeft(),
        )
        bottom_grad.setColorAt(0, QColor(5, 9, 14, 0))
        bottom_grad.setColorAt(1, QColor(5, 9, 14, 245))
        p.fillRect(QRectF(art_rect.left(), art_rect.bottom() - 155, art_rect.width(), 155), bottom_grad)

        info_rect = QRectF(rect.left(), art_rect.bottom(), rect.width(), rect.bottom() - art_rect.bottom())
        info_grad = QLinearGradient(info_rect.topLeft(), info_rect.bottomLeft())
        info_grad.setColorAt(0, QColor("#111c28"))
        info_grad.setColorAt(1, QColor("#0a1119"))
        p.fillRect(info_rect, info_grad)
        glyph = theme.element_pixmap(getattr(self, "_element_name", "hydro"), 256, "white")
        if glyph is not None:
            p.setOpacity(0.055)
            p.drawPixmap(
                QRectF(rect.right() - 246, info_rect.bottom() - 222, 230, 230),
                glyph,
                QRectF(glyph.rect()),
            )
            p.setOpacity(1.0)
        p.setPen(QPen(QColor(217, 188, 125, 80), 1.0))
        p.drawLine(
            QPointF(rect.left() + 14, art_rect.bottom()),
            QPointF(rect.right() - 14, art_rect.bottom()),
        )
        self._paint_particles(p, art_rect)
        self._paint_motes(p, art_rect)
        self._paint_hearts(p)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(217, 188, 125, 120), 1.2))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(QColor(255, 239, 205, 28), 1.0))
        p.drawRoundedRect(rect.adjusted(3.5, 3.5, -3.5, -3.5), 13, 13)
        self._paint_corners(p, rect)

    def _on_pet(self) -> None:
        self.add_hearts(QPointF(self.width() * 0.42, self._top_h * 0.62))
        self.petted.emit()
