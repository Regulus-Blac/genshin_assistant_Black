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
        return self.store.is_active(subject_id)

    def start(self, subject_id: str) -> bool:
        """Start one subject's timer; other running timers keep counting."""
        if self.store.start(subject_id):
            if not self._timer.isActive():
                self._timer.start()
            self.active_changed.emit(subject_id)
            self.tick.emit()
            return True
        return False

    def pause(self, subject_id: str | None = None) -> dict | None:
        """Stop one timer, or every running timer when no id is given."""
        if subject_id is None:
            return self.pause_all()
        if not self.store.is_active(subject_id):
            return None
        summary = self.store.pause(subject_id=subject_id)
        self._save_acc = 0
        if summary and summary.get("seconds", 0) > 0:
            self.session_finished.emit(summary)
        ups = self.store.collect_level_ups()
        if ups:
            self.level_ups.emit(ups)
        self.active_changed.emit(subject_id)
        self.tick.emit()
        return summary

    def pause_all(self) -> dict | None:
        if not self.store.actives():
            return None
        summaries = self.store.pause_all()
        self._save_acc = 0
        for summary in summaries:
            if summary.get("seconds", 0) > 0:
                self.session_finished.emit(summary)
        ups = self.store.collect_level_ups()
        if ups:
            self.level_ups.emit(ups)
        self.active_changed.emit(None)
        self.tick.emit()
        return summaries[-1] if summaries else None

    def toggle(self, subject_id: str) -> None:
        if self.is_active_subject(subject_id):
            self.pause(subject_id)
        else:
            self.start(subject_id)

    def _tick(self) -> None:
        now = datetime.now()
        new_day = now.date().isoformat()
        if new_day != self._day:
            self._day = new_day
            self.day_changed.emit(new_day)

        if self.store.actives():
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
        if not self.store.actives():
            self._timer.stop()
            return None
        return self.pause_all()
