from __future__ import annotations

from ctypes import wintypes
from datetime import date, timedelta

from PyQt5.QtCore import QDate, QEvent, QPoint, QSize, Qt, QTime
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .content import SPEAKERS
from .theme import ELEMENTS
from .widgets import Divider, IconButton, ProgressBar

# How far the frameless dialog's invisible shadow margin reaches.  The visible
# card starts this many pixels inside the top-level window.
SHADOW_MARGIN = 24


class GenshinDialog(QDialog):
    def __init__(self, parent: QWidget | None, title: str, subtitle: str = "", width: int = 500) -> None:
        super().__init__(parent, Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setWindowTitle(title)
        self.setSizeGripEnabled(True)
        self._drag_offset: QPoint | None = None
        self._width = width
        self.setMinimumSize(360, 240)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN, SHADOW_MARGIN)
        self.card = QFrame()
        self.card.setObjectName("DialogCard")
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(44)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.card.setGraphicsEffect(shadow)
        self.card.setMinimumWidth(0)
        outer.addWidget(self.card)

        root = QVBoxLayout(self.card)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(0)
        self._header = QWidget()
        head = QHBoxLayout(self._header)
        head.setContentsMargins(0, 0, 0, 0)
        head.setSpacing(8)
        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 22px; font-weight: 600; color: {theme.TEXT};"
        )
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        self.subtitle_label.setVisible(bool(subtitle))
        title_col.addWidget(self.title_label)
        title_col.addWidget(self.subtitle_label)
        head.addLayout(title_col)
        head.addStretch(1)
        close = IconButton("close", "关闭", size=14, button_size=30, color=theme.MUTED)
        close.clicked.connect(self.reject)
        head.addWidget(close, 0, Qt.AlignTop)
        root.addWidget(self._header)
        root.addSpacing(10)
        root.addWidget(Divider(faint=True))
        root.addSpacing(10)

        body_host = QWidget()
        body_host.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.body = QVBoxLayout(body_host)
        self.body.setContentsMargins(0, 0, 0, 0)
        self.body.setSpacing(11)
        self.body_scroll = QScrollArea()
        self.body_scroll.setFrameShape(QFrame.NoFrame)
        self.body_scroll.setWidgetResizable(True)
        self.body_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.body_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        self.body_scroll.setWidget(body_host)
        self.body_scroll.setMinimumHeight(80)
        root.addWidget(self.body_scroll, 1)
        root.addSpacing(12)
        root.addWidget(Divider(faint=True))
        root.addSpacing(10)
        self.footer = QHBoxLayout()
        self.footer.setContentsMargins(0, 0, 0, 0)
        self.footer.setSpacing(8)
        root.addLayout(self.footer)
        self._header.installEventFilter(self)

        self._size_grip = QSizeGrip(self)
        self._size_grip.setFixedSize(18, 18)
        self._size_grip.setStyleSheet("background: transparent;")
        self._size_grip.setToolTip("拖动这里或窗口边缘调整大小")

    # ------------------------------------------------------------------ resizing
    def _position_size_grip(self) -> None:
        if not hasattr(self, "_size_grip"):
            return
        pos = QPoint(
            self.width() - SHADOW_MARGIN - 16,
            self.height() - SHADOW_MARGIN - 16,
        )
        if self._size_grip.pos() != pos:
            self._size_grip.move(pos)
        self._size_grip.raise_()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_size_grip()

    def nativeEvent(self, event_type, message):  # noqa: N802
        """Windows edge hit-testing so every dialog can be resized by mouse."""
        if event_type == b"windows_generic_MSG":
            try:
                msg = wintypes.MSG.from_address(int(message))
                if msg.message == 0x0084:  # WM_NCHITTEST
                    if not self.isMaximized():
                        local = self.mapFromGlobal(self.cursor().pos())
                        w, h = self.width(), self.height()
                        border = SHADOW_MARGIN + 8
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

    def add_field(self, label: str, widget: QWidget, hint: str = "") -> None:
        box = QVBoxLayout()
        box.setSpacing(4)
        lab = QLabel(label)
        lab.setStyleSheet(f"font-size: 11px; color: {theme.MUTED}; letter-spacing: 1px;")
        box.addWidget(lab)
        box.addWidget(widget)
        if hint:
            h = QLabel(hint)
            h.setWordWrap(True)
            h.setStyleSheet(f"font-size: 10px; color: {theme.FAINT};")
            box.addWidget(h)
        self.body.addLayout(box)

    def add_note(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setWordWrap(True)
        lab.setStyleSheet(
            f"font-size: 11px; color: {theme.TEXT_SOFT}; background: rgba(217,188,125,12); "
            "border: 1px solid rgba(217,188,125,28); border-radius: 8px; padding: 8px 10px;"
        )
        self.body.addWidget(lab)
        return lab

    def add_button(self, text: str, *, primary: bool = False, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setObjectName("Primary" if primary else ("Danger" if danger else "Ghost"))
        btn.setMinimumHeight(34)
        btn.setMinimumWidth(88)
        self.footer.addWidget(btn)
        return btn

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.adjustSize()
        wanted_w = self._width + 2 * SHADOW_MARGIN
        if self.width() < wanted_w:
            self.resize(wanted_w, max(self.height(), 320))
        self._position_size_grip()
        parent = self.parentWidget()
        if parent:
            geo = parent.window().frameGeometry()
            x = geo.center().x() - self.width() // 2
            y = geo.center().y() - self.height() // 2
            screen = parent.window().screen().availableGeometry() if parent.window().screen() else None
            if screen:
                x = max(screen.left() + 10, min(x, screen.right() - self.width() - 10))
                y = max(screen.top() + 10, min(y, screen.bottom() - self.height() - 10))
            self.move(x, y)
        else:
            screen = self.screen().availableGeometry() if self.screen() else None
            if screen:
                self.move(screen.center().x() - self.width() // 2, screen.center().y() - self.height() // 2)

    # dragging on the header
    def eventFilter(self, obj, event):  # noqa: N802
        if obj is self._header:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.MouseMove and self._drag_offset is not None and event.buttons() & Qt.LeftButton:
                self.move(event.globalPos() - self._drag_offset)
                return True
            if event.type() == QEvent.MouseButtonRelease:
                self._drag_offset = None
        return super().eventFilter(obj, event)


class SubjectDialog(GenshinDialog):
    def __init__(self, parent: QWidget | None, subject: dict | None = None) -> None:
        editing = subject is not None
        super().__init__(
            parent,
            "编辑修习方向" if editing else "新的修习方向",
            "每一个方向，都会在提瓦特的书桌上拥有自己的位置。",
            width=430,
        )
        self.subject = subject or {}
        self.result_data: dict | None = None

        self.name_edit = QLineEdit(str(self.subject.get("name", "")))
        self.name_edit.setPlaceholderText("例如：算法、英语、科研")
        self.name_edit.setMaxLength(16)
        self.add_field("名称", self.name_edit, "最多 16 个字符，会显示在修习卡片上。")

        self.element_combo = QComboBox()
        for key, info in ELEMENTS.items():
            if key == "default":
                continue
            self.element_combo.addItem(theme.icon("sparkle", info["color"], 14), f"{info['label']}元素 · {key}", key)
        current_el = str(self.subject.get("element", "dendro"))
        idx = self.element_combo.findData(current_el)
        self.element_combo.setCurrentIndex(max(0, idx))
        self.add_field("元素", self.element_combo, "它会决定卡片的配色与元素徽记。")

        self.goal_spin = QSpinBox()
        self.goal_spin.setRange(5, 720)
        self.goal_spin.setSingleStep(5)
        self.goal_spin.setSuffix(" 分钟")
        self.goal_spin.setValue(int(self.subject.get("goal_min", 60) or 60))
        self.add_field("每日目标", self.goal_spin, "完成目标会给今天的手札留下一枚小标记；不用太苛刻。")

        self.note_edit = QLineEdit(str(self.subject.get("note", "")))
        self.note_edit.setPlaceholderText("一句话备忘，例如：真题 · 错题 · 论文")
        self.note_edit.setMaxLength(80)
        self.add_field("备注", self.note_edit, "选填。")

        self.add_note("提示：计时支持暂停与跨天累计。连续修习会带来永久的小额等级加成。")
        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        save = self.add_button("保存方向" if editing else "创建方向", primary=True)
        save.clicked.connect(self._save)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            self.name_edit.setStyleSheet("border: 1px solid #d87373;")
            return
        element = self.element_combo.currentData()
        info = ELEMENTS.get(element, ELEMENTS["default"])
        self.result_data = {
            "name": name,
            "element": element,
            "color": info["color"],
            "goal_min": int(self.goal_spin.value()),
            "note": self.note_edit.text().strip(),
        }
        self.accept()


class ExamDialog(GenshinDialog):
    def __init__(self, parent: QWidget | None, exam: dict | None = None) -> None:
        editing = exam is not None
        super().__init__(
            parent,
            "编辑考试" if editing else "添加考试",
            "把日期写下来，时间就会变成可以抵达的地方。",
            width=440,
        )
        self.exam = exam or {}
        self.result_data: dict | None = None
        self.delete_requested = False

        self.name_edit = QLineEdit(str(self.exam.get("name", "")))
        self.name_edit.setPlaceholderText("例如：算法考试、六级考试")
        self.name_edit.setMaxLength(24)
        self.add_field("考试名称", self.name_edit)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy 年 M 月 d 日")
        parsed = QDate.fromString(str(self.exam.get("date", "")), "yyyy-MM-dd")
        if not parsed.isValid():
            parsed = QDate.currentDate().addDays(30)
        self.date_edit.setDate(parsed)
        self.date_edit.setMinimumDate(QDate(2000, 1, 1))
        self.add_field("考试日期", self.date_edit)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        parsed_t = QTime.fromString(str(self.exam.get("time", "09:00")), "HH:mm")
        if not parsed_t.isValid():
            parsed_t = QTime(9, 0)
        self.time_edit.setTime(parsed_t)
        self.add_field("开始时间", self.time_edit)

        self.element_combo = QComboBox()
        for key, info in ELEMENTS.items():
            if key == "default":
                continue
            self.element_combo.addItem(theme.icon("sparkle", info["color"], 14), f"{info['label']}元素 · {key}", key)
        idx = self.element_combo.findData(str(self.exam.get("element", "hydro")))
        self.element_combo.setCurrentIndex(max(0, idx))
        self.add_field("元素标记", self.element_combo, "只用于视觉区分，不影响倒计时。")

        self.note_edit = QLineEdit(str(self.exam.get("note", "")))
        self.note_edit.setPlaceholderText("例如：准考证、考场、要带的东西")
        self.note_edit.setMaxLength(100)
        self.add_field("备注", self.note_edit, "选填。")

        if editing:
            delete = self.add_button("删除考试", danger=True)
            delete.clicked.connect(self._delete)
        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        save = self.add_button("保存考试" if editing else "添加考试", primary=True)
        save.clicked.connect(self._save)

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setFocus()
            self.name_edit.setStyleSheet("border: 1px solid #d87373;")
            return
        info = ELEMENTS.get(self.element_combo.currentData(), ELEMENTS["default"])
        data = {
            "name": name,
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "time": self.time_edit.time().toString("HH:mm"),
            "end_time": self.exam.get("end_time", ""),
            "note": self.note_edit.text().strip(),
            "element": self.element_combo.currentData(),
            "color": info["color"],
        }
        if self.exam.get("id"):
            data["id"] = self.exam["id"]
            data["short"] = self.exam.get("short", "")
        self.result_data = data
        self.accept()

    def _delete(self) -> None:
        self.delete_requested = True
        self.accept()


class ExamDetailDialog(GenshinDialog):
    EDIT_CODE = 2

    def __init__(self, parent: QWidget | None, exam: dict) -> None:
        super().__init__(parent, "考试倒计时", "把注意力放回今天，数字自然会向前走。", width=420)
        self.exam = exam

        name = QLabel(exam.get("name", "考试"))
        name.setStyleSheet(f"font-family: '{theme.SERIF}'; font-size: 17px; color: {theme.TEXT_SOFT};")
        name.setAlignment(Qt.AlignCenter)
        self.body.addWidget(name)

        self.big = QLabel(str(exam.get("label", "待设定")))
        self.big.setAlignment(Qt.AlignCenter)
        color = theme.GOLD_BRIGHT if not exam.get("passed") else theme.MUTED
        self.big.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 60px; font-weight: 700; color: {color}; "
            "background: transparent; letter-spacing: 2px;"
        )
        self.body.addWidget(self.big)

        if exam.get("passed"):
            sub = "这场考试已经结束。辛苦了，先把这一页合上吧。"
        elif exam.get("same_day"):
            sub = f"就是今天。还有 {exam.get('hours_left', 0)} 小时 {exam.get('minutes_left', 0)} 分。深呼吸。"
        else:
            sub = f"距离目标还有 {exam.get('days', 0)} 天 {exam.get('hours_left', 0)} 小时 {exam.get('minutes_left', 0)} 分"
        sub_label = QLabel(sub)
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setStyleSheet(f"font-size: 11px; color: {theme.MUTED};")
        self.body.addWidget(sub_label)
        self.body.addSpacing(6)

        glass = QFrame()
        glass.setObjectName("InnerCard")
        gl = QVBoxLayout(glass)
        gl.setContentsMargins(14, 11, 14, 11)
        gl.setSpacing(5)
        date_label = QLabel(exam.get("date_label", "尚未设定日期"))
        date_label.setStyleSheet(f"font-family: '{theme.SERIF}'; font-size: 15px; color: {theme.GOLD};")
        gl.addWidget(date_label)
        note = QLabel(exam.get("note", "") or "没有留下备注。")
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_SOFT};")
        gl.addWidget(note)
        self.body.addWidget(glass)
        exam_name = str(exam.get("name", ""))
        if "六级" in exam_name or "CET" in exam_name.upper():
            self.add_note("日期与时间可在「编辑日期」中修改。六级官方笔试时间为 2026 年 12 月 12 日 15:00–17:25。")
        else:
            self.add_note("日期与时间可在「编辑日期」中修改。具体考试时间请以学校或官方通知为准。")

        self.footer.addStretch(1)
        close = self.add_button("关闭")
        close.clicked.connect(self.reject)
        edit = self.add_button("编辑日期", primary=True)
        edit.clicked.connect(lambda: self.done(self.EDIT_CODE))


class ConfirmDialog(GenshinDialog):
    def __init__(self, parent: QWidget | None, title: str, message: str, confirm_text: str = "确定", danger: bool = False) -> None:
        super().__init__(parent, title, "这一步会直接写入本地数据。", width=400)
        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_SOFT}; line-height: 150%;")
        self.body.addWidget(label)
        self.footer.addStretch(1)
        cancel = self.add_button("再想想")
        cancel.clicked.connect(self.reject)
        ok = self.add_button(confirm_text, primary=not danger, danger=danger)
        ok.clicked.connect(self.accept)

    @classmethod
    def ask(cls, parent: QWidget | None, title: str, message: str, confirm_text: str = "确定", danger: bool = False) -> bool:
        dlg = cls(parent, title, message, confirm_text, danger)
        return dlg.exec_() == QDialog.Accepted


class NoticeDialog(GenshinDialog):
    """Resizable replacement for QMessageBox.information / warning."""

    def __init__(self, parent: QWidget | None, title: str, message: str, ok_text: str = "知道了", width: int = 430) -> None:
        super().__init__(parent, title, "", width=width)
        label = QLabel(message)
        label.setWordWrap(True)
        label.setStyleSheet(f"font-size: 12px; color: {theme.TEXT_SOFT}; line-height: 150%;")
        self.body.addWidget(label)
        self.body.addStretch(1)
        self.footer.addStretch(1)
        ok = self.add_button(ok_text, primary=True)
        ok.clicked.connect(self.accept)

    @classmethod
    def show_message(cls, parent: QWidget | None, title: str, message: str, ok_text: str = "知道了") -> None:
        cls(parent, title, message, ok_text).exec_()


class InputDialog(GenshinDialog):
    """Resizable replacement for QInputDialog.getText."""

    def __init__(self, parent: QWidget | None, title: str, label: str, text: str = "", width: int = 430) -> None:
        super().__init__(parent, title, "", width=width)
        self._edit = QLineEdit(text)
        self._edit.setPlaceholderText(label)
        self._edit.setMinimumHeight(34)
        self._edit.returnPressed.connect(self.accept)
        self.add_field(label, self._edit)
        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        ok = self.add_button("确定", primary=True)
        ok.clicked.connect(self.accept)
        self._edit.setFocus()
        self._edit.selectAll()

    def value(self) -> str:
        return self._edit.text().strip()

    @classmethod
    def get_text(cls, parent: QWidget | None, title: str, label: str, text: str = "") -> tuple[str, bool]:
        dialog = cls(parent, title, label, text)
        accepted = dialog.exec_() == QDialog.Accepted
        return dialog.value(), accepted


class CountdownOrnament(QWidget):
    """A small painted ornament used at the top of exam dialogs."""

    def __init__(self, color: str = theme.GOLD, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedHeight(16)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        cy = self.height() / 2
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(self._color).darker(150))
        grad.setColorAt(0.5, QColor(self._color))
        grad.setColorAt(1, QColor(self._color).darker(150))
        p.setPen(QPen(grad, 1.0))
        p.drawLine(QRectF(20, cy, self.width() - 40, 0).topLeft(), QRectF(20, cy, self.width() - 40, 0).topRight())
        theme.draw_diamond(p, QRectF(self.width() / 2 - 4, cy - 4, 8, 8), QColor(self._color), True)
