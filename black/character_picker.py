from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import (
    QColor,
    QFontMetrics,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import theme
from .characters import all_characters, art_path, default_look, get_character, get_look
from .dialogs import GenshinDialog
from .paths import IMAGES


def _cover_pixmap(source: Path, width: int, height: int, focus_y: float = 0.5) -> QPixmap:
    pix = QPixmap(str(source))
    if pix.isNull():
        return pix
    target = QSize(width * 2, height * 2)
    scaled = pix.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    if scaled.width() > target.width() or scaled.height() > target.height():
        x = max(0, (scaled.width() - target.width()) // 2)
        y = max(0, int((scaled.height() - target.height()) * max(0.0, min(1.0, focus_y))))
        scaled = scaled.copy(x, y, target.width(), target.height())
    scaled.setDevicePixelRatio(2.0)
    return scaled


class CharacterTile(QAbstractButton):
    order_requested = pyqtSignal(str, str)  # character id, action

    def __init__(self, meta: dict, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.meta = meta
        self._hover = False
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(150, 194)
        self.setToolTip(f"{meta.get('name')} · {meta.get('title', '')}\n右键可以调整排序")
        self._thumb = ""
        self._pix = QPixmap()
        self.set_look(meta.get("default_look"))
        self._count = len(meta.get("looks", []))

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        # Parentless on purpose: a menu parented to a widget inside the
        # translucent dialog window was drawn with a transparent background,
        # which made the labels unreadable in the dark theme.
        menu = QMenu()
        menu.setStyleSheet(
            f"QMenu {{ background: {theme.PANEL if not theme.is_light() else '#fbf6ed'}; "
            f"border: 1px solid {theme.mix(theme.GOLD, theme.PANEL, 0.55).name()}; "
            "border-radius: 9px; padding: 5px; "
            f"color: {theme.TEXT}; }} "
            "QMenu::item { padding: 7px 24px 7px 12px; border-radius: 5px; } "
            f"QMenu::item:selected {{ background: {theme.mix(theme.GOLD, theme.PANEL, 0.72).name()}; "
            f"color: {theme.GOLD_BRIGHT}; }} "
            f"QMenu::item:disabled {{ color: {theme.MUTED}; }}"
        )
        meta = self.meta
        title = menu.addAction(f"{meta.get('name')} · 排序")
        title.setEnabled(False)
        menu.addSeparator()
        for label, action in (
            ("移到最前", "front"),
            ("上移一位", "up"),
            ("下移一位", "down"),
            ("恢复默认顺序", "reset"),
        ):
            act = menu.addAction(label)
            act.triggered.connect(lambda _checked=False, a=action: self.order_requested.emit(str(self.meta.get("id")), a))
        menu.exec_(event.globalPos())
        menu.deleteLater()

    def set_look(self, look_id: str | None) -> None:
        look = get_look(self.meta, look_id)
        rel = str(look.get("thumb") or "art_snow.jpg")
        if rel == self._thumb:
            return
        self._thumb = rel
        self._pix = _cover_pixmap(art_path(rel), 150, 194, 0.12)
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
        rect = QRectF(0.6, 0.6, self.width() - 1.2, self.height() - 1.2)
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        p.setClipPath(path)
        p.fillRect(rect, QColor("#111a24") if not theme.is_light() else QColor("#fcf7ed"))
        accent = QColor(str(self.meta.get("color", theme.GOLD)))
        if not self._pix.isNull():
            p.drawPixmap(rect.toRect(), self._pix)
        if theme.is_light():
            grad = QLinearGradient(QPointF(0, self.height() * 0.68), QPointF(0, self.height()))
            grad.setColorAt(0, QColor(252, 247, 237, 0))
            grad.setColorAt(0.14, QColor(252, 247, 237, 225))
            grad.setColorAt(0.30, QColor(252, 247, 237, 245))
            grad.setColorAt(1, QColor(252, 247, 237, 250))
            p.fillRect(rect, grad)
            bottom = QLinearGradient(QPointF(0, self.height() * 0.8), QPointF(0, self.height()))
            bottom.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 0))
            bottom.setColorAt(1, QColor(accent.red(), accent.green(), accent.blue(), 22))
            p.fillRect(rect, bottom)
        else:
            grad = QLinearGradient(QPointF(0, self.height() * 0.42), QPointF(0, self.height()))
            grad.setColorAt(0, QColor(5, 9, 14, 0))
            grad.setColorAt(0.58, QColor(5, 9, 14, 185))
            grad.setColorAt(1, QColor(5, 9, 14, 248))
            p.fillRect(rect, grad)
            bottom = QLinearGradient(QPointF(0, self.height() * 0.8), QPointF(0, self.height()))
            c = QColor(accent)
            c.setAlpha(24)
            bottom.setColorAt(0, QColor(accent.red(), accent.green(), accent.blue(), 0))
            bottom.setColorAt(1, c)
            p.fillRect(rect, bottom)
        p.setClipping(False)

        theme.draw_orb(p, QRectF(9, 9, 28, 28), str(self.meta.get("element", "default")), glow=True, alpha=235)

        if self.isChecked():
            p.setPen(QPen(QColor(theme.GOLD_BRIGHT if not theme.is_light() else theme.GOLD), 2.0))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 11, 11)
            theme.draw_diamond(p, QRectF(self.width() - 20, 10, 8, 8), QColor(theme.GOLD_BRIGHT if not theme.is_light() else theme.GOLD), True)
        else:
            p.setPen(QPen(QColor(theme.GOLD if self._hover else accented(accent, 80)), 1.1))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(rect, 12, 12)

        p.setPen(QColor(theme.GOLD_SOFT if theme.is_light() else theme.GOLD_BRIGHT))
        p.setFont(theme.font(14, theme.SERIF, 600))
        p.drawText(QRectF(11, self.height() - 51, self.width() - 22, 22), Qt.AlignLeft | Qt.AlignVCenter, str(self.meta.get("name", "")))
        p.setPen(QColor(theme.MUTED))
        p.setFont(theme.font(9, theme.SANS))
        fm = QFontMetrics(p.font())
        title = fm.elidedText(str(self.meta.get("title", "")), Qt.ElideRight, self.width() - 22)
        p.drawText(QRectF(11, self.height() - 28, self.width() - 22, 17), Qt.AlignLeft | Qt.AlignVCenter, title)
        if self._count > 1:
            label = f"{self._count} 幅"
            p.setFont(theme.font(8, theme.SANS))
            fm2 = QFontMetrics(p.font())
            w = fm2.horizontalAdvance(label) + 10
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 250, 240, 210) if theme.is_light() else QColor(7, 12, 18, 180))
            p.drawRoundedRect(QRectF(self.width() - w - 9, self.height() - 25, w, 15), 7, 7)
            p.setPen(QColor(theme.GOLD_SOFT))
            p.drawText(QRectF(self.width() - w - 9, self.height() - 25, w, 15), Qt.AlignCenter, label)


def accented(c: QColor, alpha: int) -> QColor:
    out = QColor(c)
    out.setAlpha(alpha)
    return out


class CharacterPickerDialog(GenshinDialog):
    def __init__(self, parent, character_id: str, look_id: str | None = None, store=None) -> None:
        super().__init__(
            parent,
            "看板角色",
            "选一位陪你坐在书桌边的提瓦特来客，也可以为她换一幅立绘。",
            width=720,
        )
        self.store = store
        self._metas = {c["id"]: c for c in all_characters()}
        self._order = self._load_order()
        self._query = ""
        self._initial = get_character(character_id)
        self._initial_look = get_look(self._initial, look_id)
        self._selected_id = self._initial["id"]
        self._selected_look = self._initial_look["id"]
        self._look_memory = {self._initial["id"]: self._selected_look}
        self.result_data: dict | None = None
        self._tiles: dict[str, CharacterTile] = {}
        self._look_buttons: dict[str, QToolButton] = {}
        self._build()

    # ------------------------------------------------------------------ order
    def _load_order(self) -> list[str]:
        ids = [c["id"] for c in all_characters()]
        saved = []
        if self.store is not None:
            raw = self.store.settings.get("character_order")
            if isinstance(raw, list):
                saved = [str(item) for item in raw]
        order = [cid for cid in saved if cid in ids]
        order += [cid for cid in ids if cid not in order]
        return order

    def _save_order(self) -> None:
        if self.store is None:
            return
        self.store.settings["character_order"] = list(self._order)
        self.store.save()

    def _matches(self, meta: dict) -> bool:
        if not self._query:
            return True
        hay = " ".join(
            str(meta.get(key, "")) for key in ("name", "title", "id", "element")
        ).lower()
        return self._query in hay

    def _rebuild_grid(self) -> None:
        grid = self._grid
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
        row = col = 0
        visible = 0
        for cid in self._order:
            meta = self._metas.get(cid)
            if meta is None or not self._matches(meta):
                continue
            tile = self._tiles.get(cid)
            if tile is None:
                continue
            grid.addWidget(tile, row, col)
            tile.show()
            visible += 1
            col += 1
            if col == 4:
                col = 0
                row += 1
        self.empty_hint.setVisible(visible == 0)
        if visible == 0:
            # The grid was cleared above, so the placeholder must be re-added
            # or it would float above the (empty) tile area.
            grid.addWidget(self.empty_hint, 0, 0, 1, 4)
        self.result_label.setText(
            f"找到 {visible} 位角色" if self._query else f"{visible} 位角色 · 右键可以置顶或上下移动"
        )

    def _reorder(self, cid: str, action: str) -> None:
        if action == "reset":
            self._order = [c["id"] for c in all_characters()]
            message = "已恢复默认排序（沃雅妮莎在最前）。"
        else:
            if cid not in self._order:
                return
            index = self._order.index(cid)
            name = self._metas.get(cid, {}).get("name", cid)
            if action == "front" and index > 0:
                self._order.insert(0, self._order.pop(index))
                message = f"已把「{name}」移到最前。"
            elif action == "up" and index > 0:
                self._order[index - 1], self._order[index] = self._order[index], self._order[index - 1]
                message = f"「{name}」上移一位。"
            elif action == "down" and index < len(self._order) - 1:
                self._order[index + 1], self._order[index] = self._order[index], self._order[index + 1]
                message = f"「{name}」下移一位。"
            else:
                return
        self._save_order()
        self._rebuild_grid()
        self._ensure_visible(cid)
        self.order_status.setText(message)

    def _ensure_visible(self, cid: str) -> None:
        tile = self._tiles.get(cid)
        if tile is not None and tile.isVisible():
            QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(tile, 20, 20))

    def _build(self) -> None:
        chars = all_characters()
        looks = sum(len(c.get("looks", [])) for c in chars)
        intro = QLabel(
            f"当前共 {len(chars)} 位角色、{looks} 幅看板立绘。角色只改变左侧视觉与称呼，"
            "Black 仍然是替你计时、写手札、偶尔说几句的那只黑猫。"
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        self.body.addWidget(intro)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索角色（名字或称号），例如：芙宁娜、蒲公英骑士…")
        self.search_edit.setFixedHeight(32)
        self.search_edit.textChanged.connect(self._filter)
        self.body.addWidget(self.search_edit)

        self.result_label = QLabel("")
        self.result_label.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.body.addWidget(self.result_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFixedHeight(334)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        host = QWidget()
        host.setStyleSheet("background: transparent;")
        grid = QGridLayout(host)
        grid.setContentsMargins(2, 2, 6, 2)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self._grid = grid
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for meta in chars:
            tile = CharacterTile(meta)
            self._tiles[meta["id"]] = tile
            self._group.addButton(tile)
            tile.clicked.connect(lambda _checked=False, cid=meta["id"]: self._select_character(cid))
            tile.order_requested.connect(self._reorder)
        for c in range(4):
            grid.setColumnStretch(c, 1)
        self.empty_hint = QLabel("没有找到匹配的角色，换个关键词试试。")
        self.empty_hint.setAlignment(Qt.AlignCenter)
        self.empty_hint.setStyleSheet(f"font-size: 10px; color: {theme.FAINT};")
        self.empty_hint.setVisible(False)
        grid.addWidget(self.empty_hint, 0, 0, 1, 4)
        scroll.setWidget(host)
        self.body.addWidget(scroll)
        self._scroll = scroll

        self.order_status = QLabel("")
        self.order_status.setStyleSheet(f"font-size: 9px; color: {theme.GOLD_SOFT};")
        self.body.addWidget(self.order_status)

        self.art_frame = QFrame()
        self.art_frame.setStyleSheet(
            "QFrame { background: rgba(8,14,21,88); border: 1px solid rgba(217,188,125,30); border-radius: 9px; }"
        )
        al = QVBoxLayout(self.art_frame)
        al.setContentsMargins(10, 7, 10, 7)
        al.setSpacing(4)
        art_head = QHBoxLayout()
        self.look_title = QLabel("立绘 / LOOK")
        self.look_title.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 10px; color: {theme.GOLD}; letter-spacing: 1px;"
        )
        art_head.addWidget(self.look_title)
        self.look_hint = QLabel("")
        self.look_hint.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        art_head.addWidget(self.look_hint)
        art_head.addStretch(1)
        self.look_prev = QToolButton()
        self.look_prev.setText("‹")
        self.look_prev.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.look_prev.setFixedSize(24, 22)
        self.look_prev.setCursor(Qt.PointingHandCursor)
        self.look_prev.setToolTip("上一组立绘")
        self.look_prev.setStyleSheet(
            f"QToolButton {{ color: {theme.GOLD}; background: rgba(217,188,125,12); "
            "border: 1px solid rgba(217,188,125,42); border-radius: 5px; font-size: 15px; } "
            f"QToolButton:hover {{ background: rgba(217,188,125,28); }}"
        )
        self.look_prev.clicked.connect(lambda: self._scroll_looks(-1))
        self.look_next = QToolButton()
        self.look_next.setText("›")
        self.look_next.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.look_next.setFixedSize(24, 22)
        self.look_next.setCursor(Qt.PointingHandCursor)
        self.look_next.setToolTip("下一组立绘")
        self.look_next.setStyleSheet(
            f"QToolButton {{ color: {theme.GOLD}; background: rgba(217,188,125,12); "
            "border: 1px solid rgba(217,188,125,42); border-radius: 5px; font-size: 15px; } "
            f"QToolButton:hover {{ background: rgba(217,188,125,28); }}"
        )
        self.look_next.clicked.connect(lambda: self._scroll_looks(1))
        art_head.addWidget(self.look_prev)
        art_head.addWidget(self.look_next)
        al.addLayout(art_head)
        self.look_row = QWidget()
        self.look_layout = QHBoxLayout(self.look_row)
        self.look_layout.setContentsMargins(0, 0, 0, 0)
        self.look_layout.setSpacing(8)
        self.look_scroll = QScrollArea()
        self.look_scroll.setWidgetResizable(False)
        self.look_scroll.setFrameShape(QFrame.NoFrame)
        self.look_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.look_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.look_scroll.setFixedHeight(112)
        self.look_scroll.setMaximumWidth(620)
        self.look_scroll.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.look_scroll.setWidget(self.look_row)
        al.addWidget(self.look_scroll)
        self.art_frame.setFixedHeight(154)
        self.body.addWidget(self.art_frame)

        note = QLabel(
            "角色与立绘来自 GitHub HoYo-Assets、Enka Network 与工作区素材，仅供个人本地看板。"
            "想加入自己收集的图：把图片放进 data/art_extra/<角色 id>/，在 manifest.json 里登记，"
            "或运行 python tools/fetch_popular_art.py --list 查看角色 id。"
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        self.body.addWidget(note)

        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        apply = self.add_button("就是她了", primary=True)
        apply.clicked.connect(self._apply)

        self._tiles[self._selected_id].setChecked(True)
        self._refresh_looks()
        self._tiles[self._selected_id].set_look(self._selected_look)
        self._rebuild_grid()
        self._ensure_visible(self._selected_id)

    def _filter(self, text: str) -> None:
        self._query = text.strip().lower()
        self._rebuild_grid()
        if self._query:
            for cid in self._order:
                tile = self._tiles.get(cid)
                if tile is not None and tile.isVisible():
                    QTimer.singleShot(0, lambda t=tile: self._scroll.ensureWidgetVisible(t, 10, 10))
                    break

    def _select_character(self, cid: str) -> None:
        meta = get_character(cid)
        self._selected_id = meta["id"]
        if cid not in self._look_memory:
            self._look_memory[cid] = default_look(meta)["id"]
        self._selected_look = self._look_memory[cid]
        self._refresh_looks()
        tile = self._tiles.get(cid)
        if tile:
            tile.set_look(self._selected_look)
            QTimer.singleShot(0, lambda: self._scroll.ensureWidgetVisible(tile, 20, 20))

    def _select_look(self, look_id: str) -> None:
        meta = get_character(self._selected_id)
        look = get_look(meta, look_id)
        self._selected_look = look["id"]
        self._look_memory[meta["id"]] = look["id"]
        tile = self._tiles.get(meta["id"])
        if tile:
            tile.set_look(look["id"])
        self._refresh_look_checks()

    def _clear_look_buttons(self) -> None:
        while self.look_layout.count():
            item = self.look_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self.look_row.setMinimumWidth(0)
        self.look_row.setMaximumWidth(16777215)
        self._look_buttons = {}
        # Dispose of the old exclusive group with its buttons.
        old = getattr(self, "_look_group", None)
        if old:
            for b in list(old.buttons()):
                old.removeButton(b)
            old.deleteLater()
        self._look_group = QButtonGroup(self)
        self._look_group.setExclusive(True)

    def _refresh_looks(self) -> None:
        meta = get_character(self._selected_id)
        self._clear_look_buttons()
        looks = meta.get("looks", [])
        self._selected_look = get_look(meta, self._selected_look)["id"]
        self.look_title.setText(f"{meta.get('name', '')} · 立绘")
        for look in looks:
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(68, 82))
            btn.setFixedSize(84, 104)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setText(str(look.get("label", "立绘")))
            btn.setToolTip(f"{meta.get('name')} · {look.get('label')}")
            pix = _cover_pixmap(art_path(str(look.get("thumb", "art_snow.jpg"))), 68, 82, 0.08)
            if not pix.isNull():
                btn.setIcon(QIcon(pix))
            btn.setStyleSheet(
                f"QToolButton {{ background: rgba(255,255,255,4); border: 1px solid rgba(217,188,125,35); "
                "border-radius: 7px; padding: 2px; color: #a89d8b; font-size: 9px; } "
                f"QToolButton:hover {{ border-color: rgba(217,188,125,100); color: {theme.GOLD_SOFT}; }} "
                f"QToolButton:checked {{ border: 1px solid {theme.GOLD}; background: rgba(217,188,125,20); color: {theme.GOLD_BRIGHT}; }}"
            )
            self._look_buttons[look["id"]] = btn
            self._look_group.addButton(btn)
            btn.clicked.connect(lambda _checked=False, lid=look["id"]: self._select_look(lid))
            self.look_layout.addWidget(btn)
        row_width = max(1, len(looks) * 84 + max(0, len(looks) - 1) * 8 + 8)
        self.look_row.setFixedSize(row_width, 106)
        self.look_layout.activate()
        self.look_row.show()
        self.look_scroll.horizontalScrollBar().setValue(0)
        self._look_group.buttonClicked.connect(lambda b: None)  # keep group alive
        self._refresh_look_checks()
        selected_btn = self._look_buttons.get(self._selected_look)
        if selected_btn is not None:
            QTimer.singleShot(0, lambda b=selected_btn: self.look_scroll.ensureWidgetVisible(b, 10, 0))
        self.look_hint.setText(f"{len(looks)} 幅可选立绘。" if len(looks) > 1 else "此角色暂有一幅立绘。")

    def _refresh_look_checks(self) -> None:
        for lid, btn in self._look_buttons.items():
            btn.setChecked(lid == self._selected_look)

    def _scroll_looks(self, delta: int) -> None:
        bar = self.look_scroll.horizontalScrollBar()
        step = max(180, self.look_scroll.viewport().width() // 2)
        bar.setValue(bar.value() + delta * step)

    def _apply(self) -> None:
        meta = get_character(self._selected_id)
        look = get_look(meta, self._selected_look)
        self.result_data = {"character": meta["id"], "look": look["id"]}
        self.accept()
