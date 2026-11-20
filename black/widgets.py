from __future__ import annotations

import math
from pathlib import Path

from PyQt5.QtCore import (
    QEasingCurve,
    QEvent,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    pyqtProperty,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QCursor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
    QTextLayout,
)
from PyQt5.QtWidgets import (
    QAbstractButton,
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .paths import IMAGES, avatar_path


# ---------------------------------------------------------------------------
# tiny controls
# ---------------------------------------------------------------------------
class IconButton(QToolButton):
    def __init__(
        self,
        icon_name: str,
        tooltip: str = "",
        *,
        size: int = 18,
        button_size: int = 34,
        color: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        color = color or theme.GOLD
        self.setIcon(theme.icon(icon_name, color, size))
        self.setIconSize(QSize(size, size))
        self.setFixedSize(button_size, button_size)
        self.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.setToolTip(tooltip)
        self.setAutoRaise(True)


class Avatar(QWidget):
    """A circular, gold-ringed portrait."""

    def __init__(
        self,
        source: str | Path | QPixmap,
        size: int = 48,
        *,
        ring: str | None = None,
        show_status: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._size = size
        self._ring = ring or theme.GOLD
        self._show_status = show_status
        self._active = False
        self._pix: QPixmap | None = None
        self.setFixedSize(size, size)
        self.set_source(source)

    def set_source(self, source: str | Path | QPixmap | None) -> None:
        if isinstance(source, QPixmap):
            pix = source
        elif source is None:
            pix = QPixmap()
        else:
            p = Path(source)
            if not p.is_absolute():
                p = avatar_path(str(source))
            pix = QPixmap(str(p))
        if pix.isNull():
            pix = QPixmap(str(avatar_path("black.png")))
        # center-crop to square
        side = min(pix.width(), pix.height())
        if side <= 0:
            self._pix = None
            self.update()
            return
        left = (pix.width() - side) // 2
        top = (pix.height() - side) // 2
        pix = pix.copy(left, top, side, side)
        dpr = self.devicePixelRatioF() or 1.0
        target = max(2, int(self._size * dpr))
        self._pix = pix.scaled(target, target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.update()

    def set_active(self, active: bool) -> None:
        self._active = active
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(2.0, 2.0, self.width() - 4.0, self.height() - 4.0)
        clip = QPainterPath()
        clip.addEllipse(rect)
        p.save()
        p.setClipPath(clip)
        p.fillRect(rect, QColor("#0a111a"))
        if self._pix and not self._pix.isNull():
            pix = self._pix
            # fill the circle with the image, preserving crop
            p.drawPixmap(rect.toRect(), pix)
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#1a2938"))
            p.drawEllipse(rect)
            p.setFont(theme.font(max(10, self._size // 3), theme.DISPLAY))
            p.setPen(QColor(theme.GOLD))
            p.drawText(rect, Qt.AlignCenter, "B")
        # a soft vignette at the bottom, for legibility
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0.55, QColor(0, 0, 0, 0))
        grad.setColorAt(1.0, QColor(5, 9, 14, 105))
        p.fillRect(rect, grad)
        p.restore()

        ring = QColor(self._ring)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 150), 4.5))
        p.drawEllipse(rect.adjusted(1, 1, -1, -1))
        p.setPen(QPen(ring, 1.7))
        p.drawEllipse(rect.adjusted(0.8, 0.8, -0.8, -0.8))
        inner = QColor(255, 248, 225, 65)
        p.setPen(QPen(inner, 1.0))
        p.drawEllipse(rect.adjusted(4.0, 4.0, -4.0, -4.0))

        if self._show_status:
            self._paint_status(p)

    def _paint_status(self, p: QPainter) -> None:
        r = 7.0
        c = QPointF(self.width() - r - 1.5, self.height() - r - 1.5)
        p.setPen(QPen(QColor("#0a1019"), 2.4))
        p.setBrush(QColor(theme.GREEN if self._active else "#666f73"))
        p.drawEllipse(c, r, r)
        if self._active:
            glow = QRadialGradient(c, r * 2.2)
            glow.setColorAt(0, QColor(154, 202, 132, 90))
            glow.setColorAt(1, QColor(154, 202, 132, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(c, r * 2.2, r * 2.2)


class ElementOrb(QWidget):
    def __init__(self, element: str = "dendro", size: int = 42, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._element = element
        self.setFixedSize(size, size)

    def set_element(self, element: str) -> None:
        self._element = element
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        theme.draw_orb(p, QRectF(1, 1, self.width() - 2, self.height() - 2), self._element)


class ProgressBar(QWidget):
    def __init__(
        self,
        value: float = 0.0,
        *,
        color: str | None = None,
        height: int = 5,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._value = max(0.0, min(1.0, float(value)))
        self._color = color or theme.GOLD
        self.setFixedHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._anim: QPropertyAnimation | None = None

    def get_value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, float(value)))
        self.update()

    value = pyqtProperty(float, fget=get_value, fset=set_value)

    def setValue(self, value: float, animate: bool = False) -> None:  # noqa: N802
        value = max(0.0, min(1.0, float(value)))
        if not animate or abs(value - self._value) < 0.005:
            self.set_value(value)
            return
        if self._anim:
            self._anim.stop()
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(650)
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(value)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def set_color(self, color: str) -> None:
        self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0, (self.height() - 4) / 2, self.width(), 4)
        p.setPen(Qt.NoPen)
        if theme.is_light():
            p.setBrush(QColor(53, 44, 32, 32))
        else:
            p.setBrush(QColor(255, 255, 255, 22))
        p.drawRoundedRect(rect, 2, 2)
        if self._value <= 0:
            return
        w = max(3.0, rect.width() * self._value)
        fill = QRectF(rect.left(), rect.top(), w, rect.height())
        grad = QLinearGradient(fill.topLeft(), fill.topRight())
        if theme.is_light():
            grad.setColorAt(0.0, theme.mix(self._color, theme.BG2, 0.20))
        else:
            grad.setColorAt(0.0, theme.mix(self._color, "#0b1119", 0.15))
        grad.setColorAt(0.7, QColor(self._color))
        grad.setColorAt(1.0, QColor(theme.GOLD_BRIGHT))
        p.setBrush(grad)
        p.drawRoundedRect(fill, 2, 2)
        # a tiny diamond at the leading edge
        color = QColor(self._color)
        color.setAlpha(190)
        p.setBrush(color)
        end = QPointF(fill.right(), fill.center().y())
        path = QPainterPath()
        path.moveTo(end.x() - 3, end.y() - 3)
        path.lineTo(end.x(), end.y())
        path.lineTo(end.x() - 3, end.y() + 3)
        path.lineTo(end.x() - 6, end.y())
        path.closeSubpath()
        p.drawPath(path)


class NavTab(QAbstractButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._hover = False
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(42)
        self.setMinimumWidth(76)
        self.setFont(theme.font(15, theme.SERIF, 500))
        self._hover_anim = 0.0

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(max(76, fm.horizontalAdvance(self._text) + 30), 42)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        checked = self.isChecked()
        color = QColor(theme.GOLD_BRIGHT if checked else (theme.TEXT_SOFT if self._hover else theme.MUTED))
        p.setPen(color)
        p.setFont(self.font())
        p.drawText(QRectF(0, 0, self.width(), self.height() - 8), Qt.AlignCenter, self._text)
        # checked marker: small diamond and a fading underline
        if checked:
            cx = self.width() / 2
            y = self.height() - 12
            path = QPainterPath()
            path.moveTo(cx, y - 2.5)
            path.lineTo(cx + 2.5, y)
            path.lineTo(cx, y + 2.5)
            path.lineTo(cx - 2.5, y)
            path.closeSubpath()
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.GOLD))
            p.drawPath(path)
            grad = QLinearGradient(cx - 28, 0, cx + 28, 0)
            grad.setColorAt(0, QColor(theme.GOLD).darker(120))
            grad.setColorAt(0.5, QColor(theme.GOLD_BRIGHT))
            grad.setColorAt(1, QColor(theme.GOLD).darker(120))
            p.setPen(QPen(grad, 1.2))
            p.drawLine(QPointF(cx - 26, self.height() - 2), QPointF(cx + 26, self.height() - 2))
        elif self._hover:
            p.setPen(QPen(QColor(217, 188, 125, 50), 1.1))
            p.drawLine(QPointF(self.width() / 2 - 15, self.height() - 2), QPointF(self.width() / 2 + 15, self.height() - 2))


class ToggleSwitch(QAbstractButton):
    def __init__(self, checked: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)
        self._position = 1.0 if checked else 0.0
        self._anim = QPropertyAnimation(self, b"position", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._position)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def get_position(self) -> float:
        return self._position

    def set_position(self, value: float) -> None:
        self._position = max(0.0, min(1.0, float(value)))
        self.update()

    position = pyqtProperty(float, fget=get_position, fset=set_position)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0, 2, self.width(), self.height() - 4)
        track = QColor(theme.GOLD_DARK)
        track.setAlpha(int(120 + 80 * self._position))
        if not self.isChecked():
            track = QColor("#c9bda9" if theme.is_light() else "#3b4750")
        p.setPen(QPen(QColor(53, 44, 32, 45) if theme.is_light() else QColor(255, 255, 255, 35), 1))
        p.setBrush(track)
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        knob_x = 4 + self._position * (self.width() - 22)
        knob = QRectF(knob_x, 4, 16, 16)
        grad = QRadialGradient(knob.center() - QPointF(2, 2), 12)
        grad.setColorAt(0, QColor("#fff8e6"))
        grad.setColorAt(1, QColor(theme.GOLD if self.isChecked() else ("#b9ad99" if theme.is_light() else "#a8aaa5")))
        p.setPen(QPen(QColor("#fff4d4" if self.isChecked() else ("#eee5d6" if theme.is_light() else "#c6c8c0")), 0.8))
        p.setBrush(grad)
        p.drawEllipse(knob)


class Dot(QWidget):
    def __init__(self, color: str = theme.GREEN, size: int = 12, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self._on = True
        self.setFixedSize(size, size)

    def set_state(self, active: bool, color: str | None = None) -> None:
        self._on = active
        if color:
            self._color = color
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self.width() * 0.27
        if self._on:
            glow = QRadialGradient(c, self.width() / 2)
            col = QColor(self._color)
            glow.setColorAt(0, QColor(col.red(), col.green(), col.blue(), 105))
            glow.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
            p.setPen(Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(c, self.width() / 2, self.width() / 2)
        p.setBrush(QColor(self._color if self._on else "#5c6464"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, r, r)


class LevelBadge(QWidget):
    """Genshin-style level chip whose gold fill shows XP progress."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._level = 1
        self._title = "初识"
        self._progress = 0.0
        self._next_text = ""
        self.setFixedHeight(20)
        self.setMinimumWidth(76)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def set_info(self, level: int, title: str, progress: float, next_text: str = "") -> None:
        self._level = max(1, int(level))
        self._title = title
        self._progress = max(0.0, min(1.0, float(progress)))
        self._next_text = next_text
        self.setToolTip(
            f"修习等级 Lv.{self._level} · {self._title}\n"
            f"等级经验来自累计时长与连续修习加成。\n{next_text}"
        )
        fm = QFontMetrics(theme.font(10, theme.SERIF, 500))
        self.setFixedWidth(max(76, fm.horizontalAdvance(f"Lv.{self._level} {self._title}") + 18))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(217, 188, 125, 18))
        p.drawRoundedRect(rect, 8, 8)
        if self._progress > 0:
            fill = QRectF(rect.left(), rect.top(), max(2.0, rect.width() * self._progress), rect.height())
            grad = QLinearGradient(fill.topLeft(), fill.topRight())
            grad.setColorAt(0, QColor(217, 188, 125, 38))
            grad.setColorAt(0.7, QColor(217, 188, 125, 65))
            grad.setColorAt(1, QColor(243, 221, 170, 85))
            p.setBrush(grad)
            p.drawRoundedRect(fill, 8, 8)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(217, 188, 125, 80), 1.0))
        p.drawRoundedRect(rect, 8, 8)
        p.setFont(theme.font(10, theme.SERIF, 500))
        p.setPen(QColor(theme.GOLD_SOFT if theme.is_light() else "#f0d9a5"))
        p.drawText(rect, Qt.AlignCenter, f"Lv.{self._level} {self._title}")


class StatusChip(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StatusChip")
        self.setStyleSheet(
            "QFrame#StatusChip { background: rgba(8,13,20,140); border: 1px solid rgba(217,188,125,40); border-radius: 13px; }"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 3, 12, 3)
        lay.setSpacing(6)
        self.dot = Dot(theme.GREEN, 12)
        self.label = QLabel("待机中")
        self.label.setStyleSheet(f"color: {theme.MUTED}; font-size: 11px; letter-spacing: 1px;")
        lay.addWidget(self.dot)
        lay.addWidget(self.label)
        self.setFixedHeight(26)

    def set_status(self, text: str, active: bool) -> None:
        self.label.setText(text)
        self.dot.set_state(active, theme.GREEN if active else "#77807e")
        self.label.setStyleSheet(f"color: {theme.GOLD if active else theme.MUTED}; font-size: 11px; letter-spacing: 1px;")


def measure_wrapped_text(font: QFont, text: str, width: int) -> tuple[int, int]:
    """(line_count, height) for ``text`` wrapped at ``width``.

    Uses ``QTextLayout`` — the same engine QLabel paints with — because
    ``QFontMetrics.lineSpacing()`` and ``QLabel.heightForWidth()`` under-report
    the real line height for some CJK serif fonts (Noto Serif SC needs 21px per
    line at 12px while lineSpacing() says 17px), which clipped the second line
    of every two-line whisper.
    """
    width = max(40, int(width))
    lines = 0
    total = 0.0
    for paragraph in (str(text) or "").split("\n") or [""]:
        layout = QTextLayout(paragraph, font)
        layout.beginLayout()
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(width)
            total += line.height()
            lines += 1
            if lines > 400:
                break
        layout.endLayout()
    if lines == 0:
        metrics = QFontMetrics(font)
        return 1, metrics.lineSpacing()
    return lines, int(math.ceil(total))


def wrapped_label_height(label: QLabel, width: int) -> int:
    """Height a word-wrapped QLabel needs at ``width`` (kept for compatibility)."""
    label.setMinimumHeight(0)
    label.setMaximumHeight(16777215)
    return measure_wrapped_text(label.font(), label.text(), width)[1]


class WrappedText(QWidget):
    """Text that reserves exactly the height it paints.

    QLabel's heightForWidth and its painting disagreed for the CJK serif fonts
    used by the whisper bubbles (the reserved height could be 36px while the
    painted two lines needed 42px), which cut the last line in half.  This
    widget builds the real QTextLayout itself and draws those same lines, so
    measurement and painting can never diverge.
    """

    def __init__(self, text: str = "", parent: QWidget | None = None, *, color: str | None = None) -> None:
        super().__init__(parent)
        self._text = str(text or "")
        self._color = QColor(color or theme.TEXT)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    # ------------------------------------------------------------------ content
    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        text = str(text or "")
        if text == self._text:
            return
        self._text = text
        self.updateGeometry()
        self.update()

    def setTextColor(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def color(self) -> QColor:
        return QColor(self._color)

    # ------------------------------------------------------------------ layout
    def _build(self, width: int):
        width = max(40, int(width))
        layouts = []
        y = 0.0
        for paragraph in (self._text or "").split("\n") or [""]:
            layout = QTextLayout(paragraph, self.font())
            layout.beginLayout()
            while True:
                line = layout.createLine()
                if not line.isValid():
                    break
                line.setLineWidth(width)
                line.setPosition(QPointF(0, y))
                y += line.height()
                if y > 20000:
                    break
            layout.endLayout()
            layouts.append(layout)
        return layouts, y

    def measure(self, width: int | None = None) -> tuple[int, int]:
        width = width or self.width() or 200
        layouts, height = self._build(width)
        lines = sum(max(1, layout.lineCount()) for layout in layouts)
        return lines, max(1, int(math.ceil(height)))

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self.measure(width)[1]

    def sizeHint(self) -> QSize:  # noqa: N802
        width = self.width() if self.width() > 40 else 200
        return QSize(width, self.heightForWidth(width))

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        return QSize(60, max(1, self.fontMetrics().lineSpacing()))

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._text:
            return
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(QPen(self._color))
        layouts, _height = self._build(self.width())
        for layout in layouts:
            layout.draw(painter, QPointF(0, 0))
        painter.end()


class TrayPlayer(QWidget):
    """Compact music player embedded in the tray menu.

    Keeping the transport and the three play modes here avoids a long list of
    menu items while still being usable with the window hidden.
    """

    play_toggled = pyqtSignal()
    previous_clicked = pyqtSignal()
    next_clicked = pyqtSignal()
    mode_selected = pyqtSignal(str)

    MODES = (
        ("sequence", "order", "顺序播放"),
        ("shuffle", "shuffle", "随机播放"),
        ("single", "repeat-one", "单曲循环"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._playing = False
        self._mode = "sequence"
        self._title = ""
        self.setFixedWidth(268)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(9, 4, 9, 5)
        lay.setSpacing(3)

        self.title_label = QLabel("未在播放")
        self.title_label.setStyleSheet(f"font-size: 11px; color: {theme.TEXT};")
        self.title_label.setFixedWidth(250)
        lay.addWidget(self.title_label)

        row = QHBoxLayout()
        row.setSpacing(1)
        self.prev_btn = IconButton("prev", "上一首", size=12, button_size=26, color=theme.MUTED)
        self.play_btn = IconButton("play", "播放 / 暂停", size=13, button_size=28, color=theme.GOLD)
        self.next_btn = IconButton("next", "下一首", size=12, button_size=26, color=theme.MUTED)
        for btn in (self.prev_btn, self.play_btn, self.next_btn):
            row.addWidget(btn)
        row.addSpacing(10)
        self.mode_buttons: dict[str, QToolButton] = {}
        for mode, icon_name, tip in self.MODES:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setFixedSize(26, 26)
            btn.setIconSize(QSize(12, 12))
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setAutoRaise(True)
            btn.clicked.connect(lambda _checked=False, m=mode: self.mode_selected.emit(m))
            row.addWidget(btn)
            self.mode_buttons[mode] = btn
        row.addStretch(1)
        lay.addLayout(row)

        self.prev_btn.clicked.connect(self.previous_clicked)
        self.play_btn.clicked.connect(self.play_toggled)
        self.next_btn.clicked.connect(self.next_clicked)
        self.refresh("", False, "sequence")

    def refresh(self, title: str, playing: bool, mode: str) -> None:
        self._playing = bool(playing)
        self._title = str(title or "")
        self._mode = mode if mode in self.mode_buttons else "sequence"
        metrics = self.title_label.fontMetrics()
        text = self._title or "未在播放"
        self.title_label.setText(metrics.elidedText(text, Qt.ElideRight, 246))
        self.title_label.setToolTip(self._title)
        self.play_btn.setIcon(theme.icon("pause" if playing else "play", theme.GOLD, 13))
        self.play_btn.setToolTip("暂停" if playing else "播放")
        labels = {key: tip for key, _icon, tip in self.MODES}
        for key, btn in self.mode_buttons.items():
            _mode, icon_name, _tip = next(item for item in self.MODES if item[0] == key)
            active = key == self._mode
            btn.setChecked(active)
            btn.setIcon(theme.icon(icon_name, theme.GOLD if active else theme.MUTED, 12))
            btn.setToolTip(labels[key] + (" · 当前" if active else ""))


class Divider(QWidget):
    def __init__(self, parent: QWidget | None = None, *, faint: bool = False) -> None:
        super().__init__(parent)
        self._faint = faint
        self.setFixedHeight(12)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        alpha = 25 if self._faint else 55
        cx = self.width() / 2
        cy = self.height() / 2
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(217, 188, 125, 0))
        grad.setColorAt(0.25, QColor(217, 188, 125, alpha))
        grad.setColorAt(0.5, QColor(240, 217, 165, alpha + 35))
        grad.setColorAt(0.75, QColor(217, 188, 125, alpha))
        grad.setColorAt(1, QColor(217, 188, 125, 0))
        p.setPen(QPen(grad, 1))
        p.drawLine(QPointF(22, cy), QPointF(self.width() - 22, cy))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(217, 188, 125, alpha + 50))
        path = QPainterPath()
        path.moveTo(cx, cy - 3)
        path.lineTo(cx + 3, cy)
        path.lineTo(cx, cy + 3)
        path.lineTo(cx - 3, cy)
        path.closeSubpath()
        p.drawPath(path)


class TitleBar(QWidget):
    minimize_clicked = pyqtSignal()
    close_clicked = pyqtSignal()
    pin_toggled = pyqtSignal(bool)
    maximize_toggled = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(58)
        self._drag_offset: QPoint | None = None
        self._pin = False

        lay = QHBoxLayout(self)
        lay.setContentsMargins(22, 8, 14, 6)
        lay.setSpacing(10)

        mark = Avatar(
            IMAGES / ("brand_day.png" if theme.is_light() else "brand_night.png"),
            42,
            ring=theme.GOLD,
        )
        mark.setFixedSize(42, 42)
        lay.addWidget(mark)

        brand_box = QVBoxLayout()
        brand_box.setContentsMargins(0, 0, 0, 0)
        brand_box.setSpacing(-2)
        title = QLabel("BLACK")
        title.setObjectName("Brand")
        title.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 22px; font-weight: 600; color: {theme.GOLD}; letter-spacing: 5px;"
        )
        sub = QLabel("提瓦特驻留终端 · TEYVAT DESK")
        sub.setObjectName("BrandSub")
        sub.setStyleSheet(f"font-family: '{theme.SERIF}'; font-size: 9px; color: {theme.MUTED}; letter-spacing: 1px;")
        self.brand_title = title
        self.brand_sub = sub
        brand_box.addWidget(title)
        brand_box.addWidget(sub)
        lay.addLayout(brand_box)
        lay.addSpacing(12)

        self.status = StatusChip()
        self.status.setVisible(False)
        lay.addWidget(self.status)
        lay.addStretch(1)

        self.pin_btn = IconButton("pin", "窗口置顶", size=16, button_size=32, color=theme.MUTED)
        self.pin_btn.setCheckable(True)
        self.pin_btn.clicked.connect(self._on_pin)
        self.min_btn = IconButton("minus", "最小化", size=16, button_size=32, color=theme.MUTED)
        self.min_btn.clicked.connect(self.minimize_clicked)
        self.max_btn = IconButton("maximize", "最大化 / 还原", size=14, button_size=32, color=theme.MUTED)
        self.max_btn.clicked.connect(self.maximize_toggled)
        self.close_btn = IconButton("close", "关闭", size=16, button_size=32, color=theme.MUTED)
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.clicked.connect(self.close_clicked)
        for b in (self.pin_btn, self.min_btn, self.max_btn, self.close_btn):
            lay.addWidget(b)

    def _on_pin(self, checked: bool) -> None:
        self._pin = checked
        self.pin_btn.setIcon(theme.icon("pin", theme.GOLD if checked else theme.MUTED, 16))
        self.pin_toggled.emit(checked)

    def set_pinned(self, checked: bool) -> None:
        self._pin = bool(checked)
        self.pin_btn.blockSignals(True)
        self.pin_btn.setChecked(bool(checked))
        self.pin_btn.setIcon(theme.icon("pin", theme.GOLD if checked else theme.MUTED, 16))
        self.pin_btn.blockSignals(False)

    def set_maximized_icon(self, maximized: bool) -> None:
        self.max_btn.setIcon(theme.icon("restore" if maximized else "maximize", theme.MUTED, 14))

    def set_status(self, text: str, active: bool) -> None:
        # The idle chip said no more than "waiting" and took attention away
        # from the brand.  Show it only while a subject is actually counting.
        self.status.setVisible(bool(active))
        if active:
            self.status.set_status(text, True)

    def set_compact(self, compact: bool) -> None:
        wanted = not compact
        if self.brand_sub.isVisible() != wanted:
            self.brand_sub.setVisible(wanted)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.window().frameGeometry().topLeft()
            event.accept()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            if self.window().isMaximized() or self.window().property("customMaximized"):
                return
            self.window().move(event.globalPos() - self._drag_offset)
            event.accept()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.maximize_toggled.emit()
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# whisper popup
# ---------------------------------------------------------------------------
class WhisperPopup(QWidget):
    another_requested = pyqtSignal()
    accepted = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setWindowTitle("Black 的低语")
        self.setFixedWidth(408)
        self._auto_timer = QTimer(self)
        self._auto_timer.setSingleShot(True)
        self._auto_timer.timeout.connect(self._fade_close)
        self._quote: dict = {}
        self._build()

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        card = QFrame()
        card.setObjectName("WhisperCard")
        card.setStyleSheet(
            """
            QFrame#WhisperCard {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #152130, stop:0.62 #0f1924, stop:1 #0a111a);
                border: 1px solid rgba(217,188,125,120);
                border-radius: 14px;
            }
            """
        )
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 170))
        card.setGraphicsEffect(shadow)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(18, 15, 18, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        self.avatar = Avatar("black.png", 44)
        top.addWidget(self.avatar)
        names = QVBoxLayout()
        names.setSpacing(0)
        self.speaker = QLabel("Black")
        self.speaker.setStyleSheet(f"font-family: '{theme.SERIF}'; font-size: 16px; font-weight: 600; color: {theme.GOLD};")
        self.role = QLabel("夜之眷属 · 你的书桌猫")
        self.role.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        names.addWidget(self.speaker)
        names.addWidget(self.role)
        top.addLayout(names)
        top.addStretch(1)
        tag = QLabel("BLACK 的低语")
        tag.setStyleSheet(
            f"color: {theme.GOLD_SOFT}; font-family: '{theme.DISPLAY}'; font-size: 9px; letter-spacing: 1px; "
            "background: rgba(217,188,125,18); border: 1px solid rgba(217,188,125,40); border-radius: 8px; padding: 2px 6px;"
        )
        top.addWidget(tag, 0, Qt.AlignTop)
        close = IconButton("close", "收起", size=12, button_size=22, color=theme.MUTED)
        close.clicked.connect(self._fade_close)
        top.addWidget(close, 0, Qt.AlignTop)
        lay.addLayout(top)

        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setMinimumHeight(56)
        self.text.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 14px; color: {theme.TEXT}; line-height: 160%;"
        )
        lay.addWidget(self.text)

        foot = QHBoxLayout()
        foot.setContentsMargins(0, 2, 0, 0)
        foot.setSpacing(8)
        self.meta = QLabel("每隔一会儿，来和你说句话")
        self.meta.setStyleSheet(f"font-size: 10px; color: {theme.FAINT};")
        foot.addWidget(self.meta)
        foot.addStretch(1)
        another = QPushButton("再说一句")
        another.setObjectName("Ghost")
        another.setCursor(Qt.PointingHandCursor)
        another.setFixedHeight(30)
        another.clicked.connect(self.another_requested)
        okay = QPushButton("收下")
        okay.setObjectName("Primary")
        okay.setCursor(Qt.PointingHandCursor)
        okay.setFixedHeight(30)
        okay.clicked.connect(self._accept)
        foot.addWidget(another)
        foot.addWidget(okay)
        lay.addLayout(foot)

    def update_quote(self, quote: dict, avatar: str, role: str, accent: str = theme.GOLD) -> None:
        self._quote = quote
        self.avatar.set_source(avatar)
        self.speaker.setText(str(quote.get("speaker", "Black")))
        self.speaker.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 16px; font-weight: 600; color: {accent};"
        )
        self.role.setText(role)
        self.text.setText(str(quote.get("text", "")))
        self.adjustSize()

    def pop(self, quote: dict, avatar: str, role: str, accent: str = theme.GOLD, duration_ms: int = 18000) -> None:
        self.update_quote(quote, avatar, role, accent)
        self.adjustSize()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        geo = screen.availableGeometry()
        w = max(360, min(430, self.sizeHint().width()))
        self.setFixedWidth(w)
        self.adjustSize()
        h = min(310, self.height())
        self.setFixedHeight(h)
        x = geo.right() - self.width() - 12
        y = geo.bottom() - self.height() - 12
        self.move(x, y + 14)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        from PyQt5.QtCore import QParallelAnimationGroup

        group = QParallelAnimationGroup(self)
        op = QPropertyAnimation(self, b"windowOpacity", self)
        op.setDuration(220)
        op.setStartValue(0.0)
        op.setEndValue(1.0)
        mv = QPropertyAnimation(self, b"pos", self)
        mv.setDuration(300)
        mv.setStartValue(QPoint(x, y + 14))
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
        self.closed.emit()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._auto_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self.isVisible():
            self._auto_timer.start(5000)
        super().leaveEvent(event)
