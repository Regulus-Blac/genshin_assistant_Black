"""Paimon-themed desktop whisper popup.

The dark main UI is deliberately contrasted with a warm, cream Paimon bubble:
Paimon floats gently, stars twinkle behind her, and the whole note slides in
from the lower-right without stealing keyboard focus.
"""
from __future__ import annotations

import math

from PyQt5.QtCore import (
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from . import theme as _theme
from .paths import AVATARS
from .widgets import IconButton


class _PaimonPalette:
    """Paimon's note stays a dark little night-sky even in daylight mode."""

    GOLD = "#d9bc7d"
    GOLD_BRIGHT = "#f3ddaa"
    GOLD_SOFT = "#a98e5c"
    TEXT = "#eee7da"
    TEXT_SOFT = "#d7cdbb"
    MUTED = "#a89d8b"
    FAINT = "#8a9188"
    TEAL = "#72d3ce"

    def __getattr__(self, name):
        return getattr(_theme, name)


theme = _PaimonPalette()

PAIMON_ICON = AVATARS / "paimon_official.png"
CREAM = "#f7edda"
CREAM_DARK = "#ecddc1"
INK = "#3b3022"
NAVY = "#1c2c45"


class PaimonPortrait(QWidget):
    """A floating circular Paimon medallion with a slow bob and sparkle halo."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(88, 98)
        self._phase = 0.0
        self._pix = QPixmap(str(PAIMON_ICON))
        if not self._pix.isNull():
            side = min(self._pix.width(), self._pix.height())
            x = (self._pix.width() - side) // 2
            y = (self._pix.height() - side) // 2
            self._pix = self._pix.copy(x, y, side, side).scaled(
                180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        self._timer = QTimer(self)
        self._timer.setInterval(45)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        self._phase += 0.10
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cy = 4 + math.sin(self._phase) * 2.2
        center = QPointF(self.width() / 2, 46 + cy)
        radius = 39
        # halo
        halo = QRadialGradient(center, radius * 1.6)
        halo.setColorAt(0.0, QColor(111, 211, 205, 110))
        halo.setColorAt(0.55, QColor(217, 188, 125, 35))
        halo.setColorAt(1.0, QColor(217, 188, 125, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(center, radius * 1.55, radius * 1.55)

        # medallion disc
        disc = QRadialGradient(center - QPointF(10, 12), radius * 1.3)
        disc.setColorAt(0.0, QColor("#486f7b"))
        disc.setColorAt(0.60, QColor("#203a4d"))
        disc.setColorAt(1.0, QColor("#101e2d"))
        p.setBrush(disc)
        p.setPen(QPen(QColor(theme.GOLD_BRIGHT), 2.0))
        p.drawEllipse(center, radius, radius)
        p.setPen(QPen(QColor(255, 247, 224, 80), 1.0))
        p.drawEllipse(center, radius - 4, radius - 4)

        if not self._pix.isNull():
            p.save()
            clip = QPainterPath()
            clip.addEllipse(center, radius - 3.5, radius - 3.5)
            p.setClipPath(clip)
            dpr = self._pix.devicePixelRatio()
            w = self._pix.width() / (dpr or 1)
            h = self._pix.height() / (dpr or 1)
            target = QRectF(center.x() - (radius - 3), center.y() - (radius - 3), (radius - 3) * 2, (radius - 3) * 2)
            # Paimon icon is square and centered on her head.
            p.drawPixmap(target, self._pix, QRectF(0, 0, w, h))
            p.restore()

        # sparkles
        for angle, distance, size in ((-2.2, 44, 3.5), (-0.8, 47, 2.4), (-2.9, 32, 2.0), (0.3, 48, 2.8)):
            a = self._phase * 0.5 + angle
            alpha = int(110 + 100 * (0.5 + 0.5 * math.sin(self._phase * 1.8 + angle)))
            x = center.x() + math.cos(a) * distance
            y = center.y() + math.sin(a) * distance * 0.65
            c = QColor(255, 242, 199, alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(x, y), size, size)
            p.setPen(QPen(QColor(255, 242, 199, max(30, alpha // 3)), 0.7))
            p.drawLine(QPointF(x - size * 2.3, y), QPointF(x + size * 2.3, y))
            p.drawLine(QPointF(x, y - size * 2.3), QPointF(x, y + size * 2.3))


class BubbleTail(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(14, 28)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        path = QPainterPath()
        path.moveTo(13, 4)
        path.lineTo(1, 14)
        path.lineTo(13, 24)
        path.closeSubpath()
        p.setPen(QPen(QColor(217, 188, 125, 120), 1.2))
        p.setBrush(QColor(CREAM))
        p.drawPath(path)


class PaimonCard(QFrame):
    """Starry navy card behind the cream speech bubble."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(85)
        self._timer.timeout.connect(self._tick)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def _tick(self) -> None:
        self._phase += 0.06
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(1, 1, self.width() - 2, self.height() - 2)
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.setClipPath(path)
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0.0, QColor("#20344f"))
        grad.setColorAt(0.48, QColor("#14253c"))
        grad.setColorAt(1.0, QColor("#0b1628"))
        p.fillRect(rect, grad)
        # teal/cream aurora
        glow = QRadialGradient(QPointF(rect.width() * 0.15, rect.height() * 0.05), 260)
        glow.setColorAt(0.0, QColor(99, 208, 204, 60))
        glow.setColorAt(0.5, QColor(99, 208, 204, 16))
        glow.setColorAt(1.0, QColor(99, 208, 204, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(rect.width() * 0.15, rect.height() * 0.05), 280, 220)
        warm = QRadialGradient(QPointF(rect.width() * 0.92, rect.height() * 0.15), 230)
        warm.setColorAt(0.0, QColor(240, 214, 155, 55))
        warm.setColorAt(1.0, QColor(240, 214, 155, 0))
        p.setBrush(warm)
        p.drawEllipse(QPointF(rect.width() * 0.92, rect.height() * 0.15), 230, 230)

        # slow twinkling stars
        for i in range(20):
            x = ((i * 173 + 37) % 997) / 997 * rect.width()
            y = ((i * 89 + 61) % 431) / 431 * rect.height()
            if y > rect.height() * 0.74:
                continue
            twinkle = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self._phase * 1.5 + i * 1.8))
            r = 1.0 + (i % 3) * 0.7
            color = QColor(246, 232, 195, int(25 + 105 * twinkle))
            p.setBrush(color)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(x, y), r, r)
            if i % 5 == 0:
                p.setPen(QPen(QColor(246, 232, 195, int(15 + 45 * twinkle)), 0.7))
                p.drawLine(QPointF(x - r * 2.8, y), QPointF(x + r * 2.8, y))
                p.drawLine(QPointF(x, y - r * 2.8), QPointF(x, y + r * 2.8))

        # border and tiny star-corner accents
        p.setClipping(False)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(217, 188, 125, 150), 1.3))
        p.drawRoundedRect(rect, 16, 16)
        p.setPen(QPen(QColor(220, 216, 197, 45), 0.8))
        p.drawRoundedRect(rect.adjusted(3.5, 3.5, -3.5, -3.5), 13, 13)
        for x, y in ((15, 14), (self.width() - 15, 14), (15, self.height() - 14), (self.width() - 15, self.height() - 14)):
            theme.draw_star(p, QPointF(x, y), 3.1, QColor(theme.GOLD_BRIGHT if (x < 50) else theme.TEAL))


class PaimonWhisperPopup(QWidget):
    another_requested = pyqtSignal()
    accepted = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setProperty("darkIsland", True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle("派蒙的悄悄话")
        self.setFixedWidth(446)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._fade_close)
        _theme.begin_dark_island()
        try:
            self._build()
        finally:
            _theme.end_dark_island()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        self.card = PaimonCard()
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 185))
        self.card.setGraphicsEffect(shadow)
        outer.addWidget(self.card)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(17, 14, 17, 13)
        root.setSpacing(6)

        # header
        head = QHBoxLayout()
        head.setSpacing(8)
        self.title = QLabel("派蒙的悄悄话")
        self.title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 17px; font-weight: 600; color: {CREAM};"
        )
        head.addWidget(self.title)
        self.subtitle = QLabel("· 提瓦特最好的向导")
        self.subtitle.setStyleSheet(f"font-size: 9px; color: {theme.TEAL};")
        head.addWidget(self.subtitle, 0, Qt.AlignBottom)
        head.addStretch(1)
        tag = QLabel("PAIMON'S NOTE")
        tag.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: {theme.GOLD_SOFT}; letter-spacing: 1px; "
            "background: rgba(217,188,125,16); border: 1px solid rgba(217,188,125,45); border-radius: 7px; padding: 2px 6px;"
        )
        head.addWidget(tag, 0, Qt.AlignVCenter)
        close = IconButton("close", "收起", size=12, button_size=23, color=theme.MUTED)
        close.clicked.connect(self._fade_close)
        head.addWidget(close, 0, Qt.AlignTop)
        root.addLayout(head)

        # body: floating Paimon + cream speech bubble
        body = QHBoxLayout()
        body.setSpacing(0)
        self.portrait = PaimonPortrait()
        body.addWidget(self.portrait, 0, Qt.AlignTop)
        body.addSpacing(2)
        self.tail = BubbleTail()
        body.addWidget(self.tail, 0, Qt.AlignTop)
        self.bubble = QFrame()
        self.bubble.setObjectName("PaimonBubble")
        self.bubble.setStyleSheet(
            f"QFrame#PaimonBubble {{ background: {CREAM}; border: 1px solid rgba(217,188,125,130); "
            "border-radius: 13px; }"
        )
        bl = QVBoxLayout(self.bubble)
        bl.setContentsMargins(13, 9, 13, 9)
        bl.setSpacing(4)
        self.quote = QLabel("")
        self.quote.setWordWrap(True)
        self.quote.setTextFormat(Qt.PlainText)
        self.quote.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.quote.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 13px; color: {INK}; line-height: 150%;"
        )
        bl.addWidget(self.quote)
        self.attribution = QLabel("")
        self.attribution.setStyleSheet("font-size: 9px; color: #8d7b60;")
        bl.addWidget(self.attribution, 0, Qt.AlignRight)
        body.addWidget(self.bubble, 1)
        root.addLayout(body)

        # footer
        foot = QHBoxLayout()
        foot.setContentsMargins(0, 3, 0, 0)
        foot.setSpacing(8)
        self.meta = QLabel("每隔一会儿，来和你说句话")
        self.meta.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        foot.addWidget(self.meta)
        foot.addStretch(1)
        another = QPushButton("再听一句")
        another.setCursor(Qt.PointingHandCursor)
        another.setFixedHeight(30)
        another.setStyleSheet(
            f"QPushButton {{ background: rgba(8,14,21,100); border: 1px solid rgba(217,188,125,65); "
            f"border-radius: 8px; padding: 2px 12px; color: {theme.TEXT_SOFT}; font-size: 10px; }} "
            f"QPushButton:hover {{ background: rgba(217,188,125,28); color: {theme.GOLD_BRIGHT}; }}"
        )
        another.clicked.connect(self.another_requested)
        okay = QPushButton("好耶！")
        okay.setCursor(Qt.PointingHandCursor)
        okay.setFixedHeight(30)
        okay.setStyleSheet(
            "QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            "stop:0 #f4e3b8, stop:1 #d4b471); border: 1px solid #f9eccd; border-radius: 8px; "
            "padding: 2px 16px; color: #2c2315; font-size: 10px; font-weight: 600; } "
            "QPushButton:hover { background: #f9eac4; }"
        )
        okay.clicked.connect(self._accept)
        foot.addWidget(another)
        foot.addWidget(okay)
        root.addLayout(foot)

    def update_quote(self, quote: dict, avatar: str = "", role: str = "", accent: str = theme.GOLD) -> None:
        speaker = str(quote.get("speaker", "派蒙"))
        text = str(quote.get("text", ""))
        self.quote.setText(text)
        if speaker == "派蒙":
            self.attribution.setText("—— 派蒙")
        else:
            self.attribution.setText(f"—— 来自 {speaker} 的一句话")
        self.title.setText("派蒙的悄悄话")
        self.adjustSize()

    def pop(self, quote: dict, avatar: str = "", role: str = "", accent: str = theme.GOLD, duration_ms: int = 18000) -> None:
        self.update_quote(quote, avatar, role, accent)
        self.setFixedWidth(446)
        self.adjustSize()
        h = max(208, min(330, self.height()))
        self.setFixedHeight(h)
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = geo.right() - self.width() - 14
        y = geo.bottom() - self.height() - 14
        self.move(x, y + 16)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.portrait.start()
        self.card.start()
        from PyQt5.QtCore import QParallelAnimationGroup

        group = QParallelAnimationGroup(self)
        op = QPropertyAnimation(self, b"windowOpacity", self)
        op.setDuration(220)
        op.setStartValue(0.0)
        op.setEndValue(1.0)
        mv = QPropertyAnimation(self, b"pos", self)
        mv.setDuration(330)
        mv.setStartValue(QPoint(x, y + 16))
        mv.setEndValue(QPoint(x, y))
        mv.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(op)
        group.addAnimation(mv)
        group.start()
        self._show_anim = group
        self._auto_timer.start(duration_ms)

    def _accept(self) -> None:
        self.accepted.emit()
        self.close()
        self.closed.emit()
        self.portrait.stop()
        self.card.stop()

    def _fade_close(self) -> None:
        if not self.isVisible():
            return
        self._auto_timer.stop()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(180)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.finished.connect(self._finish_close)
        self._close_anim = anim
        anim.start()

    def _finish_close(self) -> None:
        self.hide()
        self.portrait.stop()
        self.card.stop()
        self.closed.emit()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._auto_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.isVisible():
            self._auto_timer.start(5000)
        super().leaveEvent(event)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._auto_timer.stop()
        self.portrait.stop()
        self.card.stop()
        super().closeEvent(event)
