from __future__ import annotations

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QTimer
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

from . import render_mode
from .stage import CharacterStage, ElidedLabel, Equalizer, theme
from .widgets import Avatar, WrappedText


class LandscapeStage(CharacterStage):
    """A full-width landscape banner with the artwork on the left.

    The overall shell stays top/bottom: this banner is above the pages.  The
    banner itself is split into a large artwork panel and a compact functional
    side panel (player, three action medallions, quote).  The artwork uses a
    contain fit so the wide illustration is not blown up into a narrow strip.
    """

    ORIENTATION = "landscape"

    def _build_ui(self) -> None:
        light = theme.is_light()
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self.setFixedHeight(360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAttribute(Qt.WA_StyledBackground, False)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.art_panel = QWidget()
        self.art_panel.setAttribute(Qt.WA_StyledBackground, False)
        left = QVBoxLayout(self.art_panel)
        left.setContentsMargins(22, 15, 30, 13)
        left.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(10)
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
        top.addStretch(1)
        self.time_label = QLabel("00:00")
        self.time_label.setObjectName("StageTime")
        self.time_label.setStyleSheet(
            f"font-family: '{theme.MONO}'; font-size: 23px; color: {theme.WHITE}; letter-spacing: 1px;"
        )
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.time_label.setMinimumWidth(96)
        top.addWidget(self.time_label)
        left.addLayout(top)
        left.addSpacing(9)

        self.exam_label = QLabel("考试日期 · 待设定")
        self.exam_label.setObjectName("StageExam")
        self.exam_label.setFixedHeight(21)
        self.exam_label.setStyleSheet(
            f"font-size: 10px; color: {theme.GOLD}; background: "
            f"{'rgba(255,250,240,225)' if light else 'rgba(8,13,20,145)'}; "
            f"border: 1px solid {'rgba(152,117,54,65)' if light else 'rgba(217,188,125,45)'}; "
            "border-radius: 8px; padding: 2px 7px;"
        )
        self.exam_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        exam_row = QHBoxLayout()
        exam_row.addWidget(self.exam_label)
        exam_row.addStretch(1)
        left.addLayout(exam_row)
        left.addStretch(1)

        self.art_name_label = QLabel("")
        self.art_name_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 24px; font-weight: 600; "
            f"color: {theme.WHITE}; letter-spacing: 2px;"
        )
        left.addWidget(self.art_name_label)
        art_caption = QLabel("TEYVAT DESK · LANDSCAPE")
        art_caption.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: {theme.GOLD_SOFT}; "
            "letter-spacing: 2px;"
        )
        left.addWidget(art_caption)
        root.addWidget(self.art_panel, 58)

        self.side_panel = QWidget()
        self.side_panel.setAttribute(Qt.WA_StyledBackground, False)
        side = QVBoxLayout(self.side_panel)
        side.setContentsMargins(17, 14, 17, 13)
        side.setSpacing(5)
        header = QHBoxLayout()
        header.setSpacing(7)
        mark = QLabel("LANDSCAPE DESK")
        mark.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: {theme.GOLD_SOFT}; "
            "letter-spacing: 1.5px;"
        )
        header.addWidget(mark)
        header.addStretch(1)
        self.orientation_btn = QPushButton(" 竖屏")
        self.orientation_btn.setObjectName("StageSideButton")
        self.orientation_btn.setIcon(theme.icon("portrait", theme.GOLD_SOFT, 12))
        self.orientation_btn.setCursor(Qt.PointingHandCursor)
        self.orientation_btn.setFixedHeight(23)
        self.orientation_btn.clicked.connect(self.orientation_requested)
        self.orientation_btn.setStyleSheet(
            f"QPushButton {{ background: {'rgba(255,250,240,220)' if light else 'rgba(8,14,21,150)'}; "
            f"border: 1px solid {'rgba(152,117,54,60)' if light else 'rgba(217,188,125,45)'}; "
            f"border-radius: 7px; color: {theme.TEXT_SOFT}; font-size: 9px; padding: 2px 8px; }} "
            f"QPushButton:hover {{ border-color: {theme.GOLD}; color: {theme.GOLD_BRIGHT}; }}"
        )
        header.addWidget(self.orientation_btn)
        side.addLayout(header)

        self.stats_label = QLabel("今日专注 0m · 连习 0 天")
        self.stats_label.setObjectName("StageStats")
        self.stats_label.setStyleSheet(f"font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;")
        side.addWidget(self.stats_label)
        self.greeting_label = QLabel("晚上好，旅行者。")
        self.greeting_label.setObjectName("StageGreeting")
        self.greeting_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 21px; font-weight: 600; color: {theme.WHITE};"
        )
        side.addWidget(self.greeting_label)
        self.sub_label = QLabel("今晚的风很适合读书。")
        self.sub_label.setObjectName("StageSub")
        self.sub_label.setWordWrap(True)
        self.sub_label.setMaximumHeight(30)
        side.addWidget(self.sub_label)

        self.player = QFrame()
        self.player.setObjectName("StagePlayer")
        self.player.setStyleSheet(
            "QFrame#StagePlayer { background: "
            f"{'rgba(255,250,240,235)' if light else 'rgba(7,12,18,215)'}; "
            f"border: 1px solid {'rgba(152,117,54,65)' if light else 'rgba(217,188,125,55)'}; "
            "border-radius: 10px; }"
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
        side.addWidget(self.player)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(7)
        self.chat_btn = self._logo_button("chat", "说说话", "和 Black 说说话")
        self.chat_btn.clicked.connect(self.chat_requested)
        self.pet_btn = self._logo_button("cat", "摸摸头", "摸摸头")
        self.pet_btn.clicked.connect(self._on_pet)
        self.char_btn = self._logo_button("palette", "角色", "切换看板角色")
        self.char_btn.clicked.connect(self.character_requested)
        for btn in (self.chat_btn, self.pet_btn, self.char_btn):
            logo_row.addWidget(btn, 1)
        side.addLayout(logo_row)

        self.quote_card = QFrame()
        self.quote_card.setObjectName("StageQuote")
        self.quote_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.quote_card.setStyleSheet(
            "QFrame#StageQuote { background: "
            f"{'rgba(255,250,240,238)' if light else 'rgba(7,12,18,215)'}; "
            f"border: 1px solid {'rgba(152,117,54,75)' if light else 'rgba(217,188,125,55)'}; "
            "border-radius: 10px; }"
        )
        qlay = QVBoxLayout(self.quote_card)
        qlay.setContentsMargins(10, 7, 10, 7)
        qlay.setSpacing(3)
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
        self.quote_text = WrappedText("……", color=theme.TEXT)
        self.quote_text.setStyleSheet(f"font-family: '{theme.SERIF}'; font-size: 12px;")
        self.quote_text.ensurePolished()
        qlay.addWidget(self.quote_text)
        side.addWidget(self.quote_card)
        side.addStretch(1)
        root.addWidget(self.side_panel, 42)

    def _quote_available_width(self) -> int:
        """Landscape bubble spans the side panel, not the 316px portrait card."""
        width = self.quote_card.width() if hasattr(self, "quote_card") else 0
        if width < 200 and hasattr(self, "side_panel"):
            width = self.side_panel.width()
        if width < 140:
            width = max(220, int(self.width() * 0.34)) if self.width() else 400
        return max(120, width - 20)

    def set_quote(self, quote: dict, avatar_file: str) -> None:
        super().set_quote(quote, avatar_file)
        # The banner is laid out after the first quote arrives; measure again
        # once its real width is known so the bubble uses the full panel.
        QTimer.singleShot(0, self._fit_quote_text)

    def _logo_button(self, icon_name: str, text: str, tip: str) -> QToolButton:
        light = theme.is_light()
        btn = QToolButton()
        btn.setObjectName("StageLogo")
        btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        btn.setIcon(theme.icon(icon_name, theme.GOLD_SOFT, 18))
        btn.setIconSize(QSize(18, 18))
        btn.setText(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(56)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet(
            f"QToolButton {{ background: {'rgba(255,250,240,225)' if light else 'rgba(8,14,21,155)'}; "
            f"border: 1px solid {'rgba(152,117,54,65)' if light else 'rgba(217,188,125,42)'}; "
            f"border-radius: 9px; color: {theme.TEXT_SOFT}; font-size: 9px; padding: 4px 2px; }} "
            f"QToolButton:hover {{ background: {'rgba(152,117,54,18)' if light else 'rgba(217,188,125,28)'}; "
            f"border-color: {theme.GOLD}; color: {theme.GOLD_BRIGHT}; }}"
        )
        return btn

    def set_character(self, character: dict, look_id: str | None = None) -> None:
        super().set_character(character, look_id)
        self._element_name = str(character.get("element", "hydro"))
        if hasattr(self, "art_name_label"):
            self.art_name_label.setText(str(character.get("name", "")))
        self.set_orientation("landscape")
        self.update()

    def _build_cover(self) -> None:
        if self._art.isNull():
            return
        left = getattr(self, "art_panel", None)
        w = left.width() if left is not None and left.width() > 0 else int(self.width() * 0.58)
        h = self.height() if self.height() > 0 else 360
        # Contain, not cover: the whole wide illustration should be visible.
        self._cover = self._art.scaled(QSize(max(1, w), max(1, h)), Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def paintEvent(self, event) -> None:  # noqa: N802
        if render_mode.is_fast():
            p = QPainter(self)
            p.fillRect(self.rect(), QColor("#f1e7d8" if theme.is_light() else "#101a25"))
            if self._cover is None:
                self._build_cover()
            if self._cover is not None and not self._cover.isNull():
                art = self.art_panel.geometry()
                p.drawPixmap(art.topLeft(), self._cover)
            p.end()
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(1.5, 1.5, self.width() - 3.0, self.height() - 3.0)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.setClipPath(path)
        light = theme.is_light()
        p.fillRect(self.rect(), QColor("#f1e7d8" if light else "#101a25"))

        art_rect = QRectF(self.art_panel.geometry())
        if art_rect.width() <= 0:
            art_rect = QRectF(rect.left(), rect.top(), rect.width() * 0.58, rect.height())
        p.fillRect(art_rect, QColor("#e9dece" if light else "#0b1520"))
        if self._cover is None:
            self._build_cover()
        if self._cover and not self._cover.isNull():
            cw, ch = self._cover.width(), self._cover.height()
            x = art_rect.left() + (art_rect.width() - cw) / 2
            y = art_rect.top() + (art_rect.height() - ch) / 2
            p.drawPixmap(QRectF(x, y, cw, ch).toRect(), self._cover)

        # side panel glass
        side_rect = QRectF(art_rect.right(), rect.top(), rect.right() - art_rect.right(), rect.height())
        side_grad = QLinearGradient(side_rect.topLeft(), side_rect.bottomRight())
        if light:
            side_grad.setColorAt(0, QColor("#fbf6ec"))
            side_grad.setColorAt(1, QColor("#eee2cf"))
        else:
            side_grad.setColorAt(0, QColor("#111f2c"))
            side_grad.setColorAt(1, QColor("#08111a"))
        p.fillRect(side_rect, side_grad)
        glyph = theme.element_pixmap(
            getattr(self, "_element_name", "hydro"), 220, "black" if light else "white"
        )
        if glyph is not None:
            p.setOpacity(0.07 if light else 0.055)
            p.drawPixmap(
                QRectF(side_rect.right() - 190, side_rect.bottom() - 190, 180, 180),
                glyph,
                QRectF(glyph.rect()),
            )
            p.setOpacity(1.0)

        top_grad = QLinearGradient(art_rect.topLeft(), QPointF(art_rect.left(), art_rect.top() + 125))
        if light:
            top_grad.setColorAt(0, QColor(252, 247, 237, 220))
            top_grad.setColorAt(1, QColor(252, 247, 237, 0))
        else:
            top_grad.setColorAt(0, QColor(4, 8, 13, 225))
            top_grad.setColorAt(1, QColor(4, 8, 13, 0))
        p.fillRect(QRectF(art_rect.left(), art_rect.top(), art_rect.width(), 130), top_grad)
        bottom_grad = QLinearGradient(
            QPointF(art_rect.left(), art_rect.bottom() - 160),
            art_rect.bottomLeft(),
        )
        if light:
            bottom_grad.setColorAt(0, QColor(247, 240, 228, 0))
            bottom_grad.setColorAt(1, QColor(247, 240, 228, 245))
        else:
            bottom_grad.setColorAt(0, QColor(5, 9, 14, 0))
            bottom_grad.setColorAt(1, QColor(5, 9, 14, 240))
        p.fillRect(QRectF(art_rect.left(), art_rect.bottom() - 160, art_rect.width(), 160), bottom_grad)

        self._paint_particles(p, art_rect)
        self._paint_hearts(p)
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(theme.GOLD), 1.2, Qt.SolidLine))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(QColor(255, 239, 205, 28), 1.0))
        p.drawRoundedRect(rect.adjusted(3.5, 3.5, -3.5, -3.5), 13, 13)
        self._paint_corners(p, rect)

    def _on_pet(self) -> None:
        art = self.art_panel.geometry()
        self.add_hearts(QPointF(art.center().x(), art.center().y()))
        self.petted.emit()
