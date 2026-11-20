from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QPoint, QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient
from PyQt5.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..dialogs import ConfirmDialog, ExamDetailDialog, ExamDialog, SubjectDialog
from ..levels import format_duration, format_short_duration
from ..stage import ElidedLabel
from ..theme import ELEMENTS
from ..widgets import Avatar, Divider, Dot, ElementOrb, IconButton, LevelBadge, ProgressBar


def clock_text(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class ExamCard(QFrame):
    clicked = pyqtSignal()
    edit_clicked = pyqtSignal()

    def __init__(self, exam: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.exam = exam
        self._hover = False
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMinimumHeight(104)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if theme.is_light():
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(22)
            shadow.setOffset(0, 5)
            shadow.setColor(QColor(91, 69, 38, 38))
            self.setGraphicsEffect(shadow)
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(15, 11, 12, 11)
        lay.setSpacing(10)
        self.orb = ElementOrb(str(self.exam.get("element", "hydro")), 38)
        lay.addWidget(self.orb, 0, Qt.AlignVCenter)

        left = QVBoxLayout()
        left.setSpacing(1)
        name = ElidedLabel(str(self.exam.get("name", "考试")))
        name.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 16px; font-weight: 600; color: {theme.TEXT};"
        )
        left.addWidget(name)
        date_label = QLabel(str(self.exam.get("date_label", "待设定")))
        date_label.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        left.addWidget(date_label)
        note = ElidedLabel(str(self.exam.get("note", "") or "点击查看倒计时"))
        note_color = theme.GOLD_SOFT if "示例" in str(self.exam.get("note", "")) else theme.FAINT
        note.setStyleSheet(f"font-size: 9px; color: {note_color};")
        left.addWidget(note)
        lay.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(0)
        right.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        big = QLabel(str(self.exam.get("label", "待设定")))
        big.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        color = theme.GOLD_BRIGHT if not self.exam.get("passed") else theme.MUTED
        if self.exam.get("same_day"):
            color = theme.ROSE
        big.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 28px; font-weight: 700; color: {color}; letter-spacing: 1px;"
        )
        right.addWidget(big)
        sub = QLabel("距离考试" if not self.exam.get("same_day") else "就在今天")
        if self.exam.get("passed"):
            sub = "已结束"
        sub.setAlignment(Qt.AlignRight)
        sub.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        right.addWidget(sub)
        lay.addLayout(right)

        self.edit_btn = QToolButton()
        self.edit_btn.setIcon(theme.icon("edit", theme.MUTED, 13))
        self.edit_btn.setIconSize(QSize(13, 13))
        self.edit_btn.setFixedSize(24, 24)
        self.edit_btn.setCursor(Qt.PointingHandCursor)
        self.edit_btn.setToolTip("编辑考试")
        self.edit_btn.setStyleSheet(
            "QToolButton { background: rgba(217,188,125,12); border-radius: 6px; } "
            "QToolButton:hover { background: rgba(217,188,125,38); }"
        )
        self.edit_btn.clicked.connect(self.edit_clicked)
        lay.addWidget(self.edit_btn, 0, Qt.AlignTop)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6)
        path = QPainterPath()
        path.addRoundedRect(rect, 13, 13)
        color = QColor(self.exam.get("color", theme.GOLD))
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if theme.is_light():
            c1 = QColor(255, 251, 243, 248) if not self._hover else QColor(255, 247, 235, 252)
            c2 = QColor(248, 239, 225, 246)
            grad.setColorAt(0, c1)
            grad.setColorAt(0.65, c2)
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 28))
            p.setBrush(grad)
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 115 if self._hover else 62), 1.0))
            p.drawPath(path)
        else:
            c1 = QColor(24, 37, 53, 230) if not self._hover else QColor(30, 46, 65, 240)
            grad.setColorAt(0, c1)
            grad.setColorAt(0.65, QColor(14, 23, 34, 230))
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 22))
            p.setBrush(grad)
            p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 100 if self._hover else 44), 1.0))
            p.drawPath(path)

        # faint elemental watermark
        p.save()
        p.setClipPath(path)
        water = QRectF(rect.right() - 118, rect.top() - 24, 144, 144)
        theme.draw_orb(p, water, str(self.exam.get("element", "hydro")), glow=False, alpha=24 if theme.is_light() else 18)
        # corner ticks
        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 90), 1.0))
        p.drawLine(QPoint(15, 9), QPoint(34, 9))
        p.drawLine(QPoint(15, 9), QPoint(15, 20))
        p.restore()


class AddSubjectCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(176)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._hover = False

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            return
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(2, 2, self.width() - 4, self.height() - 4)
        p.setBrush(QColor(217, 188, 125, 6 if not self._hover else 14))
        pen = QPen(QColor(217, 188, 125, 50 if not self._hover else 100), 1.2, Qt.DashLine)
        pen.setDashPattern([4, 5])
        p.setPen(pen)
        p.drawRoundedRect(rect, 14, 14)
        cx, cy = self.width() / 2, self.height() / 2 - 5
        p.setPen(QPen(QColor(theme.GOLD if self._hover else theme.GOLD_SOFT), 1.4))
        p.drawLine(QPoint(int(cx - 10), int(cy)), QPoint(int(cx + 10), int(cy)))
        p.drawLine(QPoint(int(cx), int(cy - 10)), QPoint(int(cx), int(cy + 10)))
        p.setFont(theme.font(12, theme.SERIF))
        p.setPen(QColor(theme.GOLD if self._hover else theme.MUTED))
        p.drawText(QRectF(0, cy + 16, self.width(), 26), Qt.AlignHCenter, "开启一个新的修习方向")
        p.setFont(theme.font(9, theme.SANS))
        p.setPen(QColor(theme.FAINT))
        p.drawText(QRectF(0, cy + 37, self.width(), 20), Qt.AlignHCenter, "NEW PATH · 可随时编辑或删除")


class SubjectCard(QFrame):
    toggle_requested = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, info: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.info = info
        self._hover = False
        self._active = False
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setMinimumHeight(170)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if theme.is_light():
            shadow = QGraphicsDropShadowEffect(self)
            shadow.setBlurRadius(24)
            shadow.setOffset(0, 6)
            shadow.setColor(QColor(91, 69, 38, 42))
            self.setGraphicsEffect(shadow)
        self._build()
        self.update_info(info)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(15, 12, 15, 11)
        lay.setSpacing(4)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.orb = ElementOrb(str(self.info.get("element", "dendro")), 37)
        top.addWidget(self.orb)
        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        self.name_label = QLabel(str(self.info.get("name", "修习")))
        self.name_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 17px; font-weight: 600; color: {theme.TEXT};"
        )
        name_col.addWidget(self.name_label)
        self.note_label = ElidedLabel(str(self.info.get("note", "") or "在自己的节奏里前进"))
        self.note_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        name_col.addWidget(self.note_label)
        top.addLayout(name_col, 1)
        top.addSpacing(3)
        self.level_badge = LevelBadge()
        top.addWidget(self.level_badge)
        self.live_dot = Dot(theme.GREEN, 10)
        self.live_dot.setToolTip("正在计时")
        self.live_dot.setVisible(False)
        top.addWidget(self.live_dot)
        top.addSpacing(2)
        self.menu_btn = QToolButton()
        self.menu_btn.setIcon(theme.icon("more", theme.MUTED, 15))
        self.menu_btn.setIconSize(QSize(15, 15))
        self.menu_btn.setFixedSize(26, 26)
        self.menu_btn.setCursor(Qt.PointingHandCursor)
        self.menu_btn.setStyleSheet(
            "QToolButton { border-radius: 6px; } QToolButton:hover { background: rgba(217,188,125,28); }"
        )
        self.menu_btn.clicked.connect(self._open_menu)
        top.addWidget(self.menu_btn)
        lay.addLayout(top)

        timer_row = QHBoxLayout()
        timer_row.setSpacing(8)
        self.timer_label = QLabel("00:00:00")
        self.timer_label.setStyleSheet(
            f"font-family: '{theme.MONO}'; font-size: 28px; font-weight: 500; color: {theme.TEXT}; letter-spacing: 1px;"
        )
        timer_row.addWidget(self.timer_label)
        timer_row.addStretch(1)
        self.play_btn = QToolButton()
        self.play_btn.setObjectName("Play")
        self.play_btn.setFixedSize(44, 44)
        self.play_btn.setIcon(theme.icon("play", "#1c1810", 18))
        self.play_btn.setIconSize(QSize(18, 18))
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setToolTip("开始计时")
        self.play_btn.clicked.connect(lambda: self.toggle_requested.emit(self.info["id"]))
        timer_row.addWidget(self.play_btn)
        lay.addLayout(timer_row)

        self.progress = ProgressBar(0, color=str(self.info.get("color", theme.GOLD)))
        lay.addWidget(self.progress)

        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.today_label = QLabel("今日 0m · 目标 90m")
        self.today_label.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        bottom.addWidget(self.today_label)
        bottom.addStretch(1)
        self.total_label = QLabel("累计 0h · 连习 0 天")
        self.total_label.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        bottom.addWidget(self.total_label)
        lay.addLayout(bottom)

    def _open_menu(self) -> None:
        menu = QMenu(self)
        edit = menu.addAction(theme.icon("edit", theme.GOLD_SOFT, 14), "编辑这个方向")
        menu.addSeparator()
        delete = menu.addAction(theme.icon("trash", "#d99a92", 14), "删除这个方向")
        action = menu.exec_(self.menu_btn.mapToGlobal(self.menu_btn.rect().bottomLeft()))
        if action == edit:
            self.edit_requested.emit(self.info["id"])
        elif action == delete:
            self.delete_requested.emit(self.info["id"])

    def update_info(self, info: dict) -> None:
        self.info = info
        active = bool(info.get("active"))
        if active != self._active:
            self._active = active
            self.play_btn.setIcon(theme.icon("pause" if active else "play", "#1c1810", 18))
            self.play_btn.setToolTip("暂停并记录" if active else "开始计时")
            self.live_dot.setVisible(active)
            self.timer_label.setStyleSheet(
                f"font-family: '{theme.MONO}'; font-size: 28px; font-weight: 500; "
                f"color: {theme.GOLD_BRIGHT if active else theme.TEXT}; letter-spacing: 1px;"
            )
            self.update()
        self.name_label.setText(str(info.get("name", "修习")))
        note = str(info.get("note", "") or "在自己的节奏里前进")
        if self.note_label.fullText() != note:
            self.note_label.setText(note)
        self.orb.set_element(str(info.get("element", "dendro")))
        level = info.get("level")
        if level:
            if level.is_max:
                next_text = "已达到最高等级。"
            else:
                next_text = f"距 Lv.{level.level + 1} 还需 {format_short_duration(level.to_next_seconds)}。"
            self.level_badge.set_info(level.level, level.title, level.progress, next_text)
        self.timer_label.setText(clock_text(info.get("today_seconds", 0)))
        today = info.get("today_seconds", 0)
        goal = info.get("goal_min", 60)
        self.today_label.setText(f"今日 {format_short_duration(today)} · 目标 {goal}m")
        self.progress.setValue(float(info.get("goal_progress", 0)), animate=False)
        self.progress.set_color(str(info.get("color", theme.GOLD)))
        total = info.get("total_seconds", 0)
        streak = info.get("streak", 0)
        best = info.get("best_streak", 0)
        self.total_label.setText(f"累计 {format_short_duration(total)} · 连习 {streak} 天")
        self.total_label.setToolTip(f"最长连续 {best} 天")
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(0.8, 0.8, self.width() - 1.6, self.height() - 1.6)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        color = QColor(str(self.info.get("color", theme.GOLD)))
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if theme.is_light():
            if self._active:
                base1 = theme.mix("#fffaf1", color, 0.14)
                base2 = theme.mix("#f8f0e1", color, 0.06)
            else:
                base1 = QColor(255, 251, 243, 248) if not self._hover else QColor(255, 246, 234, 252)
                base2 = QColor(248, 239, 225, 246)
            grad.setColorAt(0, base1)
            grad.setColorAt(0.7, base2)
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 30))
            p.setBrush(grad)
            if self._active:
                border = QColor(color.red(), color.green(), color.blue(), 180)
            else:
                border = QColor(217, 188, 125, 120 if self._hover else 62)
            p.setPen(QPen(border, 1.2 if self._active else 1.0))
            p.drawPath(path)
        else:
            base1 = QColor(26, 40, 56, 235) if self._hover else QColor(21, 33, 47, 235)
            base2 = QColor(13, 21, 31, 235)
            if self._active:
                base1 = QColor(color.red() // 4 + 18, color.green() // 4 + 27, color.blue() // 4 + 35, 245)
            grad.setColorAt(0, base1)
            grad.setColorAt(0.7, base2)
            grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 22 if self._active else 12))
            p.setBrush(grad)
            if self._active:
                border = QColor(color.red(), color.green(), color.blue(), 170)
            else:
                border = QColor(217, 188, 125, 80 if self._hover else 35)
            p.setPen(QPen(border, 1.2 if self._active else 1.0))
            p.drawPath(path)

        p.save()
        p.setClipPath(path)
        # faint arc / sigil in the upper right
        theme.draw_orb(p, QRectF(rect.right() - 92, -35, 124, 124), str(self.info.get("element", "dendro")), glow=False, alpha=13)
        # thin active glow line
        if self._active:
            line_grad = QLinearGradient(rect.left(), 0, rect.right(), 0)
            line_grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 20))
            line_grad.setColorAt(0.5, QColor(color.red(), color.green(), color.blue(), 200))
            line_grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 20))
            p.setPen(QPen(line_grad, 1.4))
            p.drawLine(QPointF(rect.left() + 16, rect.top() + 0.8), QPointF(rect.right() - 16, rect.top() + 0.8))
        p.restore()


class StudyPage(QWidget):
    note_preview_requested = pyqtSignal()
    data_changed = pyqtSignal()

    def __init__(self, store, timer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.timer = timer
        self.cards: dict[str, SubjectCard] = {}
        self.exam_cards: list[ExamCard] = []
        self.add_card = None
        self._last_day = ""
        self._compact = False
        self._expanded = False
        self._build()
        self.rebuild()
        self.timer.tick.connect(self.refresh_live)
        self.timer.active_changed.connect(self._on_active_changed)

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 2, 0)
        root.setSpacing(0)

        header = QHBoxLayout()
        header.setSpacing(8)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("修习")
        title.setObjectName("PageTitle")
        title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 26px; font-weight: 600; color: {theme.TEXT}; letter-spacing: 2px;"
        )
        subtitle = QLabel("今日的每一分钟，都会成为旅途的一部分。")
        subtitle.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch(1)
        self.total_chip = QLabel("今日 0 分钟")
        self.total_chip.setStyleSheet(
            "font-family: 'Noto Serif SC'; font-size: 12px; color: #f0d9a5; "
            "background: rgba(217,188,125,16); border: 1px solid rgba(217,188,125,45); "
            "border-radius: 10px; padding: 4px 10px;"
        )
        header.addWidget(self.total_chip, 0, Qt.AlignBottom)
        root.addLayout(header)
        root.addSpacing(12)

        exam_head = QHBoxLayout()
        exam_title = QLabel("旅行的路标")
        exam_title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 13px; font-weight: 600; color: {theme.TEXT_SOFT}; letter-spacing: 1px;"
        )
        exam_sub = QLabel("EXAM COUNTDOWN")
        exam_sub.setStyleSheet(f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: {theme.FAINT}; letter-spacing: 1px;")
        exam_head.addWidget(exam_title)
        exam_head.addWidget(exam_sub)
        exam_head.addStretch(1)
        self.exam_add_btn = QPushButton("+ 新增考试")
        self.exam_add_btn.setObjectName("TextButton")
        self.exam_add_btn.setCursor(Qt.PointingHandCursor)
        self.exam_add_btn.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        self.exam_add_btn.clicked.connect(self._add_exam)
        exam_head.addWidget(self.exam_add_btn)
        root.addLayout(exam_head)
        root.addSpacing(6)

        self.exam_container = QWidget()
        self.exam_grid = QGridLayout(self.exam_container)
        self.exam_grid.setContentsMargins(0, 0, 0, 0)
        self.exam_grid.setHorizontalSpacing(10)
        self.exam_grid.setVerticalSpacing(8)
        root.addWidget(self.exam_container)
        root.addSpacing(14)

        study_head = QHBoxLayout()
        study_head.setSpacing(8)
        title2 = QLabel("今日修习")
        title2.setObjectName("SectionTitle")
        title2.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 16px; font-weight: 600; color: {theme.TEXT}; letter-spacing: 1px;"
        )
        self.active_chip = QLabel("待机中")
        self.active_chip.setVisible(False)
        self.active_chip.setStyleSheet(
            f"font-size: 9px; color: {theme.MUTED}; background: rgba(255,255,255,7); "
            "border: 1px solid rgba(217,188,125,28); border-radius: 8px; padding: 2px 7px;"
        )
        study_head.addWidget(title2)
        study_head.addWidget(self.active_chip)
        study_head.addStretch(1)
        self.add_btn = QPushButton("+ 新建方向")
        self.add_btn.setObjectName("Ghost")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setFixedHeight(30)
        self.add_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,5); border: 1px solid rgba(217,188,125,45); "
            "border-radius: 8px; padding: 4px 12px; font-size: 11px; color: #d7cdbb; } "
            "QPushButton:hover { background: rgba(217,188,125,22); border-color: rgba(217,188,125,90); color: #f3ddaa; }"
        )
        self.add_btn.clicked.connect(self._add_subject)
        study_head.addWidget(self.add_btn)
        root.addLayout(study_head)
        root.addSpacing(7)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 6, 4)
        self.grid.setHorizontalSpacing(11)
        self.grid.setVerticalSpacing(10)
        self.scroll.setWidget(self.grid_host)
        root.addWidget(self.scroll, 1)
        self.empty_label = QLabel("还没有修习方向。点击右上角，创建第一条。")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {theme.FAINT}; font-family: '{theme.SERIF}'; font-size: 13px;")
        self.empty_label.setVisible(False)
        self.grid.addWidget(self.empty_label, 0, 0, 1, 2)

        root.addSpacing(8)
        self.journal_strip = QFrame()
        self.journal_strip.setObjectName("JournalStrip")
        self.journal_strip.setStyleSheet(
            "QFrame#JournalStrip { background: rgba(20,31,45,190); border: 1px solid rgba(217,188,125,32); border-radius: 11px; }"
        )
        jl = QHBoxLayout(self.journal_strip)
        jl.setContentsMargins(12, 7, 10, 7)
        jl.setSpacing(9)
        book = QLabel()
        book.setPixmap(theme.icon("book", theme.GOLD_SOFT, 18).pixmap(18, 18))
        jl.addWidget(book)
        jbox = QVBoxLayout()
        jbox.setSpacing(0)
        self.journal_title = QLabel("今日手札 · 自动记录")
        self.journal_title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 11px; color: {theme.TEXT_SOFT};"
        )
        self.journal_sub = QLabel("每天的计时会汇总为本地 Markdown")
        self.journal_sub.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        jbox.addWidget(self.journal_title)
        jbox.addWidget(self.journal_sub)
        jl.addLayout(jbox)
        jl.addStretch(1)
        preview = QPushButton("预览手札")
        preview.setObjectName("Ghost")
        preview.setCursor(Qt.PointingHandCursor)
        preview.setFixedHeight(27)
        preview.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,4); border: 1px solid rgba(217,188,125,42); "
            "border-radius: 7px; padding: 3px 11px; font-size: 10px; color: #d7cdbb; } "
            "QPushButton:hover { background: rgba(217,188,125,25); color: #f3ddaa; }"
        )
        preview.clicked.connect(self.note_preview_requested)
        jl.addWidget(preview)
        root.addWidget(self.journal_strip)

    # ------------------------------------------------------------------ data
    def _clear_layout(self, layout: QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def rebuild(self) -> None:
        self._clear_layout(self.exam_grid)
        self.exam_cards = []
        cols = 1 if self._compact else 2
        exams = self.store.exams()
        if not exams:
            empty = QLabel("还没有考试日期。点击「+ 新增考试」，为自己立一个路标。")
            empty.setStyleSheet(f"font-size: 10px; color: {theme.FAINT}; padding: 9px;")
            self.exam_grid.addWidget(empty, 0, 0, 1, cols)
        for i, exam in enumerate(exams[:6]):
            card = ExamCard(exam)
            card.clicked.connect(lambda e=exam: self._open_exam(e))
            card.edit_clicked.connect(lambda e=exam: self._edit_exam(e))
            self.exam_cards.append(card)
            self.exam_grid.addWidget(card, i // cols, i % cols)
        self.exam_grid.setColumnStretch(0, 1)
        self.exam_grid.setColumnStretch(1, 0 if self._compact else 1)

        self._clear_layout(self.grid)
        self.cards = {}
        subjects = self.store.subjects()
        if not subjects:
            self.empty_label = QLabel("还没有修习方向。点击右上角，创建第一条。")
            self.empty_label.setAlignment(Qt.AlignCenter)
            self.empty_label.setStyleSheet(f"color: {theme.FAINT}; font-family: '{theme.SERIF}'; font-size: 13px;")
            self.empty_label.setMinimumHeight(160)
            self.grid.addWidget(self.empty_label, 0, 0, 1, cols)
        for i, info in enumerate(subjects):
            card = SubjectCard(info)
            card.toggle_requested.connect(self._toggle_subject)
            card.edit_requested.connect(self._edit_subject)
            card.delete_requested.connect(self._delete_subject)
            self.cards[info["id"]] = card
            self.grid.addWidget(card, i // cols, i % cols)
        if subjects:
            add = AddSubjectCard()
            add.clicked.connect(self._add_subject)
            self.grid.addWidget(add, len(subjects) // cols, len(subjects) % cols)
            self.add_card = add
        else:
            self.add_card = None
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 0 if self._compact else 1)
        self.refresh_live()
        self._update_expanded_height()

    def _can_relayout(self) -> bool:
        """True when the existing cards can simply be re-gridded.

        Destroying and recreating every card while the user drags the window
        is what used to produce the blank flash; a re-grid keeps the very same
        widgets and only changes their positions.
        """
        subjects = self.store.subjects()
        if not subjects or self.add_card is None:
            return False
        if len(self.cards) != len(subjects):
            return False
        if any(info["id"] not in self.cards for info in subjects):
            return False
        exams = self.store.exams()
        return len(self.exam_cards) == min(len(exams), 6)

    def _relayout_cards(self) -> None:
        cols = 1 if self._compact else 2
        self.grid_host.setUpdatesEnabled(False)
        try:
            for card in self.exam_cards:
                self.exam_grid.removeWidget(card)
            for i, card in enumerate(self.exam_cards):
                self.exam_grid.addWidget(card, i // cols, i % cols)
            self.exam_grid.setColumnStretch(0, 1)
            self.exam_grid.setColumnStretch(1, 0 if self._compact else 1)

            widgets = [self.cards[info["id"]] for info in self.store.subjects()]
            if self.add_card is not None:
                widgets.append(self.add_card)
            for widget in widgets:
                self.grid.removeWidget(widget)
            for i, widget in enumerate(widgets):
                self.grid.addWidget(widget, i // cols, i % cols)
            self.grid.setColumnStretch(0, 1)
            self.grid.setColumnStretch(1, 0 if self._compact else 1)
        finally:
            self.grid_host.setUpdatesEnabled(True)
            self.grid_host.update()

    def set_compact(self, compact: bool) -> None:
        compact = bool(compact)
        if compact == self._compact:
            return
        self._compact = compact
        if self._can_relayout():
            self._relayout_cards()
            self.refresh_live()
            self._update_expanded_height()
        else:
            self.rebuild()

    def set_expanded(self, expanded: bool) -> None:
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        if not expanded:
            self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.scroll.setMinimumHeight(0)
            self.scroll.setMaximumHeight(16777215)
            self.scroll.updateGeometry()
        self._update_expanded_height()

    def _update_expanded_height(self) -> None:
        if not hasattr(self, "scroll"):
            return
        if not self._expanded:
            return
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(max(320, self.grid_host.sizeHint().height() + 16))
        self.scroll.setMaximumHeight(16777215)
        self.scroll.updateGeometry()


    def refresh_live(self) -> None:
        now = datetime.now()
        subjects = self.store.subjects(now)
        for info in subjects:
            card = self.cards.get(info["id"])
            if card:
                card.update_info(info)
        overall = self.store.overall(now)
        self.total_chip.setText(f"今日 {format_duration(overall['today_seconds'])}")
        active = self.store.active_subject()
        self.active_chip.setVisible(bool(active))
        if active:
            elapsed = self.store.active_elapsed(now)
            self.active_chip.setText(f"● 正在修习「{active['name']}」 · {format_short_duration(elapsed)}")
            self.active_chip.setStyleSheet(
                f"font-size: 9px; color: {theme.GREEN}; background: rgba(154,202,132,14); "
                "border: 1px solid rgba(154,202,132,38); border-radius: 8px; padding: 2px 7px;"
            )
        else:
            self.active_chip.setText("")
        today_count = len([s for s in subjects if s["today_seconds"] > 0])
        streak_max = max([s["streak"] for s in subjects], default=0)
        self.journal_sub.setText(
            f"今日 {format_duration(overall['today_seconds'])} · {today_count}/{max(1,len(subjects))} 个方向有记录 · 最长连习 {streak_max} 天"
        )

    # ------------------------------------------------------------------ actions
    def _toggle_subject(self, subject_id: str) -> None:
        active = self.store.active()
        if active and active.get("subject_id") == subject_id:
            self.timer.pause()
        else:
            self.timer.start(subject_id)
        self.refresh_live()

    def _on_active_changed(self, subject_id) -> None:
        self.refresh_live()

    def _add_subject(self) -> None:
        dlg = SubjectDialog(self.window())
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.store.add_subject(**dlg.result_data)
            self.rebuild()
            self.data_changed.emit()

    def _edit_subject(self, subject_id: str) -> None:
        sub = self.store.subject(subject_id)
        if not sub:
            return
        dlg = SubjectDialog(self.window(), sub)
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.store.update_subject(subject_id, **dlg.result_data)
            self.rebuild()
            self.data_changed.emit()

    def _delete_subject(self, subject_id: str) -> None:
        sub = self.store.subject(subject_id)
        if not sub:
            return
        if not ConfirmDialog.ask(
            self.window(),
            "删除修习方向",
            f"确定要删除「{sub['name']}」吗？它的累计时长和连续记录也会一起消失，这一步无法撤销。",
            "删除",
            danger=True,
        ):
            return
        if self.timer.is_active_subject(subject_id):
            self.timer.pause()
        self.store.delete_subject(subject_id)
        self.rebuild()
        self.data_changed.emit()

    def _open_exam(self, exam_info: dict) -> None:
        dlg = ExamDetailDialog(self.window(), exam_info)
        result = dlg.exec_()
        if result == ExamDetailDialog.EDIT_CODE:
            self._edit_exam(exam_info)

    def _edit_exam(self, exam_info: dict) -> None:
        exam = self.store.exam(exam_info.get("id", ""))
        if not exam:
            return
        dlg = ExamDialog(self.window(), exam)
        dlg.exec_()
        if dlg.delete_requested:
            if ConfirmDialog.ask(
                self.window(),
                "删除考试",
                f"确定删除「{exam.get('name', '这场考试')}」吗？倒计时会从路标上移除。",
                "删除",
                danger=True,
            ):
                self.store.delete_exam(exam["id"])
                self.rebuild()
                self.data_changed.emit()
            return
        if dlg.result_data:
            self.store.save_exam(dlg.result_data)
            self.rebuild()
            self.data_changed.emit()

    def _add_exam(self) -> None:
        dlg = ExamDialog(self.window())
        if dlg.exec_() == QDialog.Accepted and dlg.result_data:
            self.store.save_exam(dlg.result_data)
            self.rebuild()
            self.data_changed.emit()
