from __future__ import annotations

import os
from pathlib import Path

from PyQt5.QtCore import QSize, Qt, QThread, QUrl
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import ai, theme
from ..dialogs import GenshinDialog
from ..paths import MUSIC
from ..whispers import RANDOM_CHOICE, WHISPER_AVATARS, get_whisper_avatar
from ..widgets import IconButton, ToggleSwitch


class SettingsDialog(GenshinDialog):
    def __init__(self, parent, store) -> None:
        super().__init__(
            parent,
            "设置",
            "所有偏好、计时与对话都只保存在这台电脑上。",
            width=560,
        )
        self.store = store
        self.result_data: dict | None = None
        self.quit_requested = False
        self._test_worker: ai.ChatWorker | None = None
        self._build_body()
        self.quit_btn = self.add_button("退出 Black", danger=True)
        self.quit_btn.clicked.connect(self._request_quit)
        self.footer.addStretch(1)
        cancel = self.add_button("取消")
        cancel.clicked.connect(self.reject)
        save = self.add_button("保存设置", primary=True)
        save.clicked.connect(self._save)

    # ------------------------------------------------------------------ ui
    def _build_body(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMaximumHeight(510)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(0, 0, 6, 2)
        lay.setSpacing(13)
        scroll.setWidget(host)
        self.body.addWidget(scroll)

        # -- appearance --
        lay.addWidget(self._section("外观", "APPEARANCE"))
        ap = self._grid()
        self.appearance_group = QButtonGroup(self)
        self.appearance_group.setExclusive(True)
        appearance_row = QHBoxLayout()
        appearance_row.setContentsMargins(0, 0, 0, 0)
        appearance_row.setSpacing(7)
        current_appearance = theme.normalize_mode(self.store.settings.get("appearance", "dark"))
        for mode, label, icon_name in (("dark", "夜晚模式", "moon"), ("light", "白天模式", "sun")):
            btn = QToolButton()
            btn.setCheckable(True)
            btn.setChecked(mode == current_appearance)
            btn.setText(label)
            btn.setIcon(theme.icon(icon_name, theme.GOLD_SOFT, 14))
            btn.setIconSize(QSize(14, 14))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.setProperty("mode", mode)
            btn.setStyleSheet(
                f"QToolButton {{ background: rgba(255,255,255,5); border: 1px solid rgba(217,188,125,35); "
                "border-radius: 8px; padding: 3px 11px; color: #d7cdbb; font-size: 10px; } "
                f"QToolButton:hover {{ border-color: rgba(217,188,125,90); color: {theme.GOLD_BRIGHT}; }} "
                f"QToolButton:checked {{ border-color: {theme.GOLD}; background: rgba(217,188,125,16); "
                f"color: {theme.GOLD_BRIGHT}; }}"
            )
            self.appearance_group.addButton(btn)
            appearance_row.addWidget(btn)
        appearance_row.addStretch(1)
        ap.addWidget(self._label("主题"), 0, 0)
        ap.addLayout(appearance_row, 0, 1)
        theme_note = QLabel("夜晚模式是默认配色；白天模式使用暖色纸面与深金文字，左侧角色舞台和派蒙悄悄话会保留夜空感。切换立即生效，计时不会中断。")
        theme_note.setWordWrap(True)
        theme_note.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        ap.addWidget(theme_note, 1, 0, 1, 2)
        lay.addWidget(self._wrap(ap))

        # -- sound --
        lay.addWidget(self._section("音效", "SOUND"))
        snd = self._grid()
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setSingleStep(5)
        self.volume_slider.setPageStep(10)
        self.volume_slider.setValue(int(self.store.settings.get("sound_volume", 80) or 0))
        self.volume_slider.setFixedHeight(22)
        self.volume_slider.setCursor(Qt.PointingHandCursor)
        self.volume_slider.setToolTip("调整提示音、点击音与升级音的音量；拖到最左为静音。")
        self.volume_value = QLabel(f"{self.volume_slider.value()}%")
        self.volume_value.setFixedWidth(40)
        self.volume_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.volume_value.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        vol_row = QHBoxLayout()
        vol_row.setContentsMargins(0, 0, 0, 0)
        vol_row.setSpacing(8)
        vol_row.addWidget(self.volume_slider, 1)
        vol_row.addWidget(self.volume_value)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.sliderReleased.connect(self._preview_volume)
        snd.addWidget(self._label("音效音量"), 0, 0)
        snd.addLayout(vol_row, 0, 1)
        volume_note = QLabel("松手后会试听一声；调到 0% 就是静音。乐音页的音乐音量在那边单独调节。")
        volume_note.setWordWrap(True)
        volume_note.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        snd.addWidget(volume_note, 1, 0, 1, 2)
        lay.addWidget(self._wrap(snd))

        # -- companion --
        lay.addWidget(self._section("陪伴与低语", "COMPANION"))
        s = self._grid()
        self.name_edit = QLineEdit(str(self.store.settings.get("user_name", "旅行者")))
        self.name_edit.setMaxLength(18)
        s.addWidget(self._label("你怎么称呼"), 0, 0)
        s.addWidget(self.name_edit, 0, 1)

        self.whisper_avatar_combo = QComboBox()
        self.whisper_avatar_combo.setIconSize(QSize(22, 22))
        current_persona = get_whisper_avatar(str(self.store.settings.get("whisper_avatar", "派蒙")))
        current_choice = str(self.store.settings.get("whisper_avatar", "派蒙") or "派蒙")
        # "随机" is a mode rather than a face: every popup picks another one.
        self.whisper_avatar_combo.addItem(
            theme.icon("sparkle", theme.GOLD, 20), "随机（每次换一位）", RANDOM_CHOICE
        )
        for item in WHISPER_AVATARS:
            self.whisper_avatar_combo.addItem(QIcon(str(item["path"])), item["name"], item["speaker"])
        if current_choice == RANDOM_CHOICE:
            avatar_idx = 0
        else:
            avatar_idx = self.whisper_avatar_combo.findData(current_persona["speaker"])
        self.whisper_avatar_combo.setCurrentIndex(max(0, avatar_idx))
        self.whisper_avatar_combo.setToolTip("头像会决定右下角悄悄话的配图、名字和台词；选「随机」则每次换一位。")
        s.addWidget(self._label("悄悄话头像"), 1, 0)
        s.addWidget(self.whisper_avatar_combo, 1, 1)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 180)
        self.interval_spin.setSingleStep(5)
        self.interval_spin.setSuffix(" 分钟")
        self.interval_spin.setValue(int(self.store.settings.get("quote_interval_min", 20) or 20))
        s.addWidget(self._label("弹出间隔"), 2, 0)
        s.addWidget(self.interval_spin, 2, 1)

        self.whisper_toggle = ToggleSwitch(bool(self.store.settings.get("desktop_whisper", True)))
        s.addWidget(self._label("自动弹出"), 3, 0)
        s.addWidget(self._with_desc(self.whisper_toggle, "关闭后不再自动弹出，但仍可以用顶部的星星按钮手动叫 Black 说话。"), 3, 1)

        self.tts_toggle = ToggleSwitch(bool(self.store.settings.get("tts_enabled", False)))
        s.addWidget(self._label("朗读台词"), 4, 0)
        s.addWidget(self._with_desc(self.tts_toggle, "调用 Windows 自带中文语音。无需联网，声音取决于系统语音包。"), 4, 1)

        self.tts_rate = QComboBox()
        self.tts_rate.addItem("慢一些", -2)
        self.tts_rate.addItem("正常", 0)
        self.tts_rate.addItem("稍快", 2)
        cur_rate = int(self.store.settings.get("tts_rate", -1) or 0)
        idx = 0
        for i in range(self.tts_rate.count()):
            if self.tts_rate.itemData(i) == cur_rate:
                idx = i
        if idx == 0 and cur_rate == -1:
            idx = 1
        self.tts_rate.setCurrentIndex(idx)
        s.addWidget(self._label("朗读语速"), 5, 0)
        s.addWidget(self.tts_rate, 5, 1)
        lay.addWidget(self._wrap(s))

        # -- behavior --
        lay.addWidget(self._section("界面与行为", "BEHAVIOUR"))
        b = self._grid()
        self.top_toggle = ToggleSwitch(bool(self.store.settings.get("always_on_top", False)))
        b.addWidget(self._label("窗口置顶"), 0, 0)
        b.addWidget(self._with_desc(self.top_toggle, "让 Black 留在其他窗口上方。"), 0, 1)
        self.tray_toggle = ToggleSwitch(bool(self.store.settings.get("close_to_tray", True)))
        b.addWidget(self._label("关闭到托盘"), 1, 0)
        b.addWidget(self._with_desc(self.tray_toggle, "点右上角关闭时隐藏到系统托盘，计时不会中断；从托盘菜单可以真正退出。"), 1, 1)
        lay.addWidget(self._wrap(b))

        # -- music --
        lay.addWidget(self._section("乐音", "MUSIC"))
        m = self._grid()
        self.music_edit = QLineEdit(str(self.store.settings.get("music_folder", MUSIC)))
        self.music_edit.setReadOnly(True)
        choose = QPushButton("选择文件夹")
        choose.setObjectName("Ghost")
        choose.setCursor(Qt.PointingHandCursor)
        choose.setFixedHeight(31)
        choose.clicked.connect(self._choose_music)
        music_row = QHBoxLayout()
        music_row.setContentsMargins(0, 0, 0, 0)
        music_row.setSpacing(6)
        music_row.addWidget(self.music_edit, 1)
        music_row.addWidget(choose)
        m.addWidget(self._label("本地曲库"), 0, 0)
        m.addLayout(music_row, 0, 1)
        self.autoplay_toggle = ToggleSwitch(bool(self.store.settings.get("auto_play_bgm", False)))
        m.addWidget(self._label("启动时播放"), 1, 0)
        m.addWidget(self._with_desc(self.autoplay_toggle, "启动后自动播放曲库第一首。适合把 Black 当作桌面 BGM。"), 1, 1)
        lay.addWidget(self._wrap(m))

        # -- AI --
        lay.addWidget(self._section("AI 对话 · 可选", "OPENAI COMPATIBLE"))
        a = self._grid()
        self.base_edit = QLineEdit(str(self.store.settings.get("api_base", "https://api.deepseek.com")))
        self.base_edit.setPlaceholderText("https://api.deepseek.com")
        a.addWidget(self._label("接口地址"), 0, 0)
        a.addWidget(self.base_edit, 0, 1)
        self.model_edit = QLineEdit(str(self.store.settings.get("api_model", "deepseek-flash")))
        self.model_edit.setPlaceholderText("deepseek-flash")
        a.addWidget(self._label("模型"), 1, 0)
        a.addWidget(self.model_edit, 1, 1)
        self.key_edit = QLineEdit(str(self.store.settings.get("api_key", "")))
        self.key_edit.setPlaceholderText("sk-… 只保存在本机配置里")
        self.key_edit.setEchoMode(QLineEdit.Password)
        key_row = QHBoxLayout()
        key_row.setContentsMargins(0, 0, 0, 0)
        key_row.setSpacing(6)
        key_row.addWidget(self.key_edit, 1)
        self.eye_btn = QPushButton("显示")
        self.eye_btn.setObjectName("Ghost")
        self.eye_btn.setCursor(Qt.PointingHandCursor)
        self.eye_btn.setFixedSize(48, 31)
        self.eye_btn.clicked.connect(self._toggle_key_eye)
        key_row.addWidget(self.eye_btn)
        a.addWidget(self._label("API Key"), 2, 0)
        a.addLayout(key_row, 2, 1)
        test_row = QHBoxLayout()
        test_row.setContentsMargins(0, 0, 0, 0)
        test_row.setSpacing(8)
        self.test_btn = QPushButton("测试连接")
        self.test_btn.setObjectName("Ghost")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.setFixedHeight(31)
        self.test_btn.clicked.connect(self._test_ai)
        test_row.addWidget(self.test_btn)
        self.test_status = QLabel("填写后可以在这里测试；不填也不影响计时与离线陪伴。")
        self.test_status.setWordWrap(True)
        self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        test_row.addWidget(self.test_status, 1)
        a.addWidget(self._label(""), 3, 0)
        a.addLayout(test_row, 3, 1)

        links = QHBoxLayout()
        links.setContentsMargins(0, 0, 0, 0)
        links.setSpacing(10)
        apply_key = QPushButton("申请 DeepSeek API Key")
        apply_key.setObjectName("TextButton")
        apply_key.setCursor(Qt.PointingHandCursor)
        apply_key.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        apply_key.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://platform.deepseek.com/api_keys")))
        docs = QPushButton("查看 DeepSeek 官方文档")
        docs.setObjectName("TextButton")
        docs.setCursor(Qt.PointingHandCursor)
        docs.setStyleSheet(f"font-size: 10px; color: {theme.GOLD_SOFT};")
        docs.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://api-docs.deepseek.com/zh-cn/")))
        links.addWidget(apply_key)
        links.addWidget(docs)
        links.addStretch(1)
        a.addWidget(self._label("官方入口"), 4, 0)
        a.addLayout(links, 4, 1)

        note = QLabel(
            "Black 不内置任何 API Key，也不会替你申请。默认的接口与模型只是 DeepSeek 官方示例；"
            "不填写 Key 时，聊天使用本地离线陪伴。Key 以明文保存在本地 data/black.json，"
            "建议只在个人电脑上使用。"
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        a.addWidget(note, 5, 0, 1, 2)
        lay.addWidget(self._wrap(a))

        # -- data --
        lay.addWidget(self._section("本地数据", "YOUR OWN ARCHIVE"))
        d = self._grid()
        path_label = QLabel(str(self.store.config_path.parent))
        path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        path_label.setWordWrap(True)
        path_label.setStyleSheet(f"font-size: 9px; color: {theme.MUTED};")
        d.addWidget(self._label("数据目录"), 0, 0)
        d.addWidget(path_label, 0, 1)
        data_row = QHBoxLayout()
        data_row.setContentsMargins(0, 0, 0, 0)
        data_row.setSpacing(8)
        open_data = QPushButton("打开数据文件夹")
        open_data.setObjectName("Ghost")
        open_data.setCursor(Qt.PointingHandCursor)
        open_data.setFixedHeight(31)
        open_data.clicked.connect(lambda: os.startfile(str(self.store.config_path.parent)))  # noqa: S606
        backup = QPushButton("导出备份")
        backup.setObjectName("Ghost")
        backup.setCursor(Qt.PointingHandCursor)
        backup.setFixedHeight(31)
        backup.clicked.connect(self._backup)
        data_row.addWidget(open_data)
        data_row.addWidget(backup)
        data_row.addStretch(1)
        d.addWidget(self._label("备份"), 1, 0)
        d.addLayout(data_row, 1, 1)
        lay.addWidget(self._wrap(d))

        tip = QLabel("提示：所有计时与手札都是纯本地文件。把整个文件夹拷走，就带走了 Black 的全部记忆。")
        tip.setWordWrap(True)
        tip.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        lay.addWidget(tip)
        lay.addStretch(1)

    def _section(self, title: str, en: str) -> QWidget:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)
        t = QLabel(title)
        t.setStyleSheet(
            f"font-family: '{theme.SERIF}'; font-size: 14px; font-weight: 600; color: {theme.GOLD};"
        )
        e = QLabel(en)
        e.setStyleSheet(
            f"font-family: '{theme.DISPLAY}'; font-size: 8px; color: {theme.FAINT}; letter-spacing: 1px;"
        )
        lay.addWidget(t)
        lay.addWidget(e)
        lay.addStretch(1)
        return row

    def _grid(self) -> QGridLayout:
        grid = QGridLayout()
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(9)
        grid.setColumnStretch(1, 1)
        return grid

    def _label(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setStyleSheet(f"font-size: 10px; color: {theme.MUTED};")
        lab.setMinimumWidth(92)
        return lab

    def _with_desc(self, widget: QWidget, desc: str) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(widget, 0, Qt.AlignTop)
        lab = QLabel(desc)
        lab.setWordWrap(True)
        lab.setStyleSheet(f"font-size: 9px; color: {theme.FAINT};")
        lay.addWidget(lab, 1)
        return box

    def _wrap(self, grid: QGridLayout) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: rgba(8,14,21,75); border: 1px solid rgba(217,188,125,20); border-radius: 9px; }"
        )
        frame.setLayout(grid)
        return frame

    # ------------------------------------------------------------------ actions
    def _choose_music(self) -> None:
        current = self.music_edit.text() or str(MUSIC)
        folder = QFileDialog.getExistingDirectory(self, "选择本地音乐文件夹", current)
        if folder:
            self.music_edit.setText(folder)

    def _toggle_key_eye(self) -> None:
        if self.key_edit.echoMode() == QLineEdit.Password:
            self.key_edit.setEchoMode(QLineEdit.Normal)
            self.eye_btn.setText("隐藏")
        else:
            self.key_edit.setEchoMode(QLineEdit.Password)
            self.eye_btn.setText("显示")

    def _test_ai(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            self.test_status.setText("先填写 API Key。")
            self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.ROSE};")
            return
        if self._test_worker and self._test_worker.isRunning():
            return
        self.test_btn.setEnabled(False)
        self.test_status.setText("正在向接口打个招呼…")
        self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.GOLD_SOFT};")
        worker = ai.ChatWorker(
            self.base_edit.text().strip(),
            key,
            self.model_edit.text().strip() or "deepseek-flash",
            [
                {"role": "system", "content": "你是一个连接测试助手。只回复：连接成功。"},
                {"role": "user", "content": "ping"},
            ],
            self,
        )
        worker.ok.connect(self._test_ok)
        worker.failed.connect(self._test_failed)
        worker.finished.connect(lambda: self.test_btn.setEnabled(True))
        self._test_worker = worker
        worker.start()

    def _test_ok(self, reply: str) -> None:
        self.test_status.setText(f"连接成功：{reply[:60]}")
        self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.GREEN};")

    def _test_failed(self, message: str) -> None:
        self.test_status.setText(message)
        self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.ROSE};")

    def _backup(self) -> None:
        try:
            path = self.store.export_backup()
            self.test_status.setText(f"备份已写入：{path.name}")
            self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.GREEN};")
        except Exception as e:
            self.test_status.setText(f"备份失败：{e}")
            self.test_status.setStyleSheet(f"font-size: 9px; color: {theme.ROSE};")

    def _on_volume_changed(self, value: int) -> None:
        self.volume_value.setText(f"{value}%")
        if not self.volume_slider.isSliderDown():
            self._preview_volume()

    def _preview_volume(self) -> None:
        sounds = getattr(self.parent(), "sounds", None)
        if sounds is None:
            return
        sounds.volume = max(0, min(100, int(self.volume_slider.value()))) / 100.0
        sounds.click()

    def _save(self) -> None:
        name = self.name_edit.text().strip() or "旅行者"
        checked = self.appearance_group.checkedButton()
        appearance = str(checked.property("mode")) if checked is not None else "dark"
        self.result_data = {
            "user_name": name[:18],
            "appearance": appearance,
            "sound_volume": int(self.volume_slider.value()),
            "whisper_avatar": self.whisper_avatar_combo.currentData() or "派蒙",
            "quote_interval_min": int(self.interval_spin.value()),
            "desktop_whisper": bool(self.whisper_toggle.isChecked()),
            "tts_enabled": bool(self.tts_toggle.isChecked()),
            "tts_rate": int(self.tts_rate.currentData() or 0),
            "always_on_top": bool(self.top_toggle.isChecked()),
            "close_to_tray": bool(self.tray_toggle.isChecked()),
            "music_folder": self.music_edit.text().strip() or str(MUSIC),
            "auto_play_bgm": bool(self.autoplay_toggle.isChecked()),
            "api_base": self.base_edit.text().strip() or "https://api.deepseek.com",
            "api_model": self.model_edit.text().strip() or "deepseek-flash",
            "api_key": self.key_edit.text().strip(),
        }
        self.accept()

    def _request_quit(self) -> None:
        from ..dialogs import ConfirmDialog

        if not ConfirmDialog.ask(
            self,
            "退出 Black",
            "要退出 Black 吗？正在进行的计时会先收尾并写进今天的手札，之后可以从桌面快捷方式重新打开。",
            "退出",
            danger=True,
        ):
            return
        if self._test_worker and self._test_worker.isRunning():
            self._test_worker.wait(1600)
        self.quit_requested = True
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._test_worker and self._test_worker.isRunning():
            self._test_worker.wait(1600)
        super().closeEvent(event)

    def done(self, result: int) -> None:  # noqa: D401
        if self._test_worker and self._test_worker.isRunning():
            self._test_worker.wait(1800)
        super().done(result)
