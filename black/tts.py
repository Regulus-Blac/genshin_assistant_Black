from __future__ import annotations

import threading

from PyQt5.QtCore import QObject, pyqtSignal


class TTSService(QObject):
    """Tiny Windows SAPI wrapper. Runs off the UI thread and fails silently."""

    spoken = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._busy = False
        self._last_message = ""

    def speak(self, text: str, rate: int = 0) -> bool:
        text = (text or "").strip()
        if not text:
            return False
        if self._busy:
            return False
        self._busy = True
        thread = threading.Thread(target=self._run, args=(text, rate), daemon=True)
        thread.start()
        return True

    def _run(self, text: str, rate: int) -> None:
        try:
            import pythoncom
            import win32com.client

            pythoncom.CoInitialize()
            voice = win32com.client.Dispatch("SAPI.SpVoice")
            try:
                voice.Volume = 92
                voice.Rate = max(-5, min(5, int(rate)))
                voices = voice.GetVoices()
                chosen = None
                preferred = ("Chinese", "Huihui", "Xiaoxiao", "Yunxi", "Kangkang", "Yaoyao")
                for i in range(voices.Count):
                    v = voices.Item(i)
                    desc = str(v.GetDescription())
                    if any(token.lower() in desc.lower() for token in preferred):
                        chosen = v
                        break
                if chosen is not None:
                    voice.Voice = chosen
            except Exception:
                pass
            # SAPI flag 0 = synchronous, 2 = purge previous speech
            voice.Speak(text[:260], 0)
            self.spoken.emit()
        except Exception as e:
            self._last_message = str(e)
            self.failed.emit(self._last_message)
        finally:
            self._busy = False
            try:
                pythoncom.CoUninitialize()
            except Exception:
                pass
