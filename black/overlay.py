from __future__ import annotations

import math
import random

from PyQt5.QtCore import QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import QWidget

from . import theme


class LevelUpOverlay(QWidget):
    dismissed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ups: list[dict] = []
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._animate)
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.timeout.connect(self.hide_overlay)
        self._rng = random.Random(77)
        self._sparks = [
            {
                "a": self._rng.uniform(0, math.tau),
                "r": self._rng.uniform(80, 340),
                "speed": self._rng.uniform(-0.35, 0.35),
                "size": self._rng.uniform(1.0, 3.1),
                "phase": self._rng.uniform(0, math.tau),
            }
            for _ in range(52)
        ]
        self.setCursor(Qt.PointingHandCursor)
        self.hide()
        self.setAttribute(Qt.WA_StyledBackground, False)

    def show_levels(self, ups: list[dict]) -> None:
        if not ups:
            return
        self._ups = ups
        self._phase = 0.0
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()
        self._timer.start()
        self._close_timer.start(6200)

    def hide_overlay(self) -> None:
        self._timer.stop()
        self._close_timer.stop()
        if self.isVisible():
            self.hide()
            self.dismissed.emit()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.hide_overlay()
            event.accept()
            return
        super().mousePressEvent(event)

    def _animate(self) -> None:
        self._phase += 0.03
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._ups:
            return
        first = self._ups[0]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), QColor(3, 6, 10, 215))

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2 - 10
        # central warm bloom
        bloom = QRadialGradient(QPointF(cx, cy), 320)
        bloom.setColorAt(0.0, QColor(217, 188, 125, 66))
        bloom.setColorAt(0.35, QColor(217, 188, 125, 24))
        bloom.setColorAt(1.0, QColor(217, 188, 125, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(bloom)
        p.drawEllipse(QPointF(cx, cy), 340, 340)

        # rotating thin rays
        p.save()
        p.translate(cx, cy)
        p.rotate(self._phase * 18)
        for i in range(24):
            p.rotate(15)
            alpha = 22 + int(22 * (0.5 + 0.5 * math.sin(self._phase * 2 + i)))
            p.setPen(QPen(QColor(240, 219, 170, alpha), 0.8))
            p.drawLine(QPointF(80, 0), QPointF(78 + 120 + (i % 3) * 35, 0))
        p.restore()

        # rings
        p.setBrush(Qt.NoBrush)
        for r, alpha, width in ((156, 95, 1.4), (166, 42, 0.8), (236, 55, 0.9), (246, 25, 0.7)):
            p.setPen(QPen(QColor(217, 188, 125, alpha), width))
            p.drawEllipse(QPointF(cx, cy), r, r)
        # four diamonds on the outer ring
        for angle in (0, 90, 180, 270):
            a = math.radians(angle - 90)
            point = QPointF(cx + math.cos(a) * 246, cy + math.sin(a) * 246)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(theme.GOLD_BRIGHT))
            p.save()
            p.translate(point)
            p.rotate(angle)
            path = QPainterPath()
            path.moveTo(0, -5)
            path.lineTo(4, 0)
            path.lineTo(0, 5)
            path.lineTo(-4, 0)
            path.closeSubpath()
            p.drawPath(path)
            p.restore()

        # sparks
        for s in self._sparks:
            a = s["a"] + self._phase * s["speed"]
            r = s["r"] + math.sin(self._phase * 1.4 + s["phase"]) * 5
            x = cx + math.cos(a) * r
            y = cy + math.sin(a) * r
            alpha = int(35 + 120 * (0.5 + 0.5 * math.sin(self._phase * 2.2 + s["phase"])))
            color = QColor(theme.GOLD_BRIGHT if s["size"] > 1.8 else theme.TEAL)
            color.setAlpha(alpha)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawEllipse(QPointF(x, y), s["size"], s["size"])

        # text
        p.setPen(QColor(theme.GOLD_SOFT))
        p.setFont(theme.font(9, theme.DISPLAY, 400, 3))
        p.drawText(QRectF(0, cy - 170, w, 24), Qt.AlignHCenter, "LEVEL  UP  ·  羁 绊 提 升")
        p.setPen(QColor(theme.TEXT_SOFT))
        p.setFont(theme.font(16, theme.SERIF, 500))
        p.drawText(QRectF(0, cy - 142, w, 30), Qt.AlignHCenter, str(first.get("name", "")))

        # level number
        level_text = str(first.get("level", 1))
        p.setPen(QColor(theme.GOLD_BRIGHT))
        f = theme.font(72, theme.SERIF, 700)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        p.setFont(f)
        p.drawText(QRectF(0, cy - 108, w, 100), Qt.AlignHCenter, f"Lv.{level_text}")
        p.setPen(QColor(theme.GOLD))
        p.setFont(theme.font(19, theme.SERIF, 500))
        p.drawText(QRectF(0, cy + 2, w, 30), Qt.AlignHCenter, str(first.get("title", "")))
        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.font(10, theme.SERIF))
        p.drawText(QRectF(0, cy + 44, w, 24), Qt.AlignHCenter, "累计的光，正在成为你的力量。")

        if len(self._ups) > 1:
            rest = "  ·  ".join(f"{u['name']} Lv.{u['level']}" for u in self._ups[1:])
            p.setPen(QColor(theme.FAINT))
            p.setFont(theme.font(9, theme.SANS))
            p.drawText(QRectF(0, cy + 76, w, 24), Qt.AlignHCenter, "同时提升：" + rest)

        p.setPen(QColor(theme.FAINT))
        p.setFont(theme.font(9, theme.SANS))
        p.drawText(QRectF(0, h - 38, w, 20), Qt.AlignHCenter, "点击任意处继续")
