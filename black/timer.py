from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import QObject, QTimer, pyqtSignal

from .store import Store


class TimerEngine(QObject):
    """One-second heartbeat around the store's wall-clock timer."""

    tick = pyqtSignal()
    active_changed = pyqtSignal(object)  # subject id or None
    session_finished = pyqtSignal(object)  # summary returned by Store.pause
    level_ups = pyqtSignal(list)
    day_changed = pyqtSignal(str)  # new date key
    heartbeat_saved = pyqtSignal()

    def __init__(self, store: Store, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._save_acc = 0
        self._level_acc = 0
        self._day = datetime.now().date().isoformat()
        # Keep the heartbeat running even while idle so date rollover, D-day
        # labels and the journal can update if Black is left open overnight.
        self._timer.start()

    def is_active_subject(self, subject_id: str) -> bool:
        active = self.store.active()
        return bool(active and active.get("subject_id") == subject_id)

    def start(self, subject_id: str) -> bool:
        active = self.store.active()
        if active and active.get("subject_id") != subject_id:
            # Finishing through pause() makes switching directions trigger the
            # same journal write, chime and level-up checks as a manual pause.
            self.pause()
        if self.store.start(subject_id):
            if not self._timer.isActive():
                self._timer.start()
            self.active_changed.emit(subject_id)
            self.tick.emit()
            return True
        return False

    def pause(self) -> dict | None:
        was_active = bool(self.store.active())
        summary = self.store.pause()
        self._save_acc = 0
        if summary and summary.get("seconds", 0) > 0:
            self.session_finished.emit(summary)
        if was_active:
            ups = self.store.collect_level_ups()
            if ups:
                self.level_ups.emit(ups)
            self.active_changed.emit(None)
            self.tick.emit()
        return summary

    def toggle(self, subject_id: str) -> None:
        if self.is_active_subject(subject_id):
            self.pause()
        else:
            self.start(subject_id)

    def _tick(self) -> None:
        now = datetime.now()
        new_day = now.date().isoformat()
        if new_day != self._day:
            self._day = new_day
            self.day_changed.emit(new_day)

        if self.store.active():
            self.store.heartbeat(now, save=False)
            self._save_acc += 1
            self._level_acc += 1
            if self._save_acc >= 20:
                self.store.save()
                self._save_acc = 0
                self.heartbeat_saved.emit()
            if self._level_acc >= 12:
                ups = self.store.collect_level_ups(now)
                if ups:
                    self.level_ups.emit(ups)
                self._level_acc = 0
        self.tick.emit()

    def shutdown(self) -> dict | None:
        if not self.store.active():
            self._timer.stop()
            return None
        summary = self.pause()
        return summary
