"""Music discovery, download cache and playback for Black.

Online sources:
  * NetEase Cloud Music search/URL through the public GD Studio bridge.
  * iTunes Search API (30 second previews) as a fallback.

The app never bundles third-party songs.  Online tracks are fetched on demand
into a local cache for personal listening; availability depends on the public
interfaces and can change without notice.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import requests

# Must be set before QMediaPlayer chooses a backend.  See app.py for details.
if sys.platform == "win32":
    os.environ.setdefault("QT_MULTIMEDIA_PREFERRED_PLUGINS", "windowsmediafoundation")

from PyQt5.QtCore import QObject, QThread, QUrl, pyqtSignal
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer

from .paths import CACHE_DIR

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) BlackAssistant/1.0"
HEADERS = {"User-Agent": UA, "Referer": "https://music.163.com/"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".m4a", ".aac", ".ogg", ".wma"}
GD_API = "https://music-api.gdstudio.xyz/api.php"
_ORPHAN_THREADS: list[QThread] = []


@dataclass
class Track:
    source: str
    id: str
    title: str
    artist: str
    album: str = ""
    duration: int = 0
    preview_url: str = ""
    cover: str = ""

    @property
    def source_label(self) -> str:
        return "网易云 · 完整音源" if self.source == "netease" else "iTunes · 30 秒试听"

    @property
    def subtitle(self) -> str:
        bits = [self.artist or "未知艺人"]
        if self.album:
            bits.append(self.album)
        return " · ".join(bits)

    @property
    def key(self) -> str:
        return f"{self.source}:{self.id}"


@dataclass
class Playable:
    title: str
    subtitle: str
    path: Path | None = None
    track: Track | None = None
    duration: int = 0

    @property
    def is_online(self) -> bool:
        return self.track is not None

    @property
    def key(self) -> str:
        if self.track:
            return "online:" + self.track.key
        return "local:" + str(self.path)


def scan_folder(folder: str | Path, limit: int = 500) -> list[Path]:
    folder = Path(folder)
    if not folder.exists() or not folder.is_dir():
        return []
    found: list[Path] = []
    try:
        for p in sorted(folder.rglob("*")):
            if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
                found.append(p)
                if len(found) >= limit:
                    break
    except OSError:
        return found
    return found


def search_netease(query: str, limit: int = 10) -> list[Track]:
    params = {"types": "search", "source": "netease", "name": query, "count": limit, "pages": 1}
    r = requests.get(GD_API, params=params, headers=HEADERS, timeout=18)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        title = str(item.get("name", "")).strip()
        if not title:
            continue
        artists = item.get("artist") or []
        if isinstance(artists, str):
            artists = [artists]
        out.append(
            Track(
                source="netease",
                id=str(item.get("url_id") or item.get("id") or ""),
                title=title,
                artist=" / ".join(str(a) for a in artists),
                album=str(item.get("album", "")),
                duration=0,
            )
        )
    return out


def search_itunes(query: str, limit: int = 10) -> list[Track]:
    params = {
        "term": query,
        "media": "music",
        "entity": "song",
        "limit": limit,
        "country": "US",
    }
    r = requests.get("https://itunes.apple.com/search", params=params, headers=HEADERS, timeout=18)
    r.raise_for_status()
    results = r.json().get("results", [])
    out = []
    for item in results:
        preview = str(item.get("previewUrl", "") or "")
        if not preview:
            continue
        out.append(
            Track(
                source="itunes",
                id=str(item.get("trackId", "")),
                title=str(item.get("trackName", "")).strip() or "未知曲目",
                artist=str(item.get("artistName", "")).strip(),
                album=str(item.get("collectionName", "")).strip(),
                duration=int((item.get("trackTimeMillis") or 0) // 1000),
                preview_url=preview,
                cover=str(item.get("artworkUrl100", "") or ""),
            )
        )
    return out


def search_all(query: str, limit_each: int = 8) -> list[Track]:
    query = query.strip()
    if not query:
        return []
    tracks: list[Track] = []
    errors = []
    # NetEase first (usually the more useful full tracks), then iTunes previews.
    try:
        tracks.extend(search_netease(query, limit_each))
    except Exception as e:
        errors.append(f"网易云：{e}")
    try:
        tracks.extend(search_itunes(query, limit_each))
    except Exception as e:
        errors.append(f"iTunes：{e}")
    if not tracks:
        detail = "；".join(errors) if errors else "没有找到匹配曲目"
        raise RuntimeError(f"在线音乐暂时没有回应（{detail}）。可以先播放本地曲库。")
    return tracks


def resolve_stream(track: Track) -> str:
    if track.source == "itunes" and track.preview_url:
        return track.preview_url
    if track.source == "netease":
        last_error = ""
        for br in (320, 192, 128):
            try:
                r = requests.get(
                    GD_API,
                    params={"types": "url", "source": "netease", "id": track.id, "br": br},
                    headers=HEADERS,
                    timeout=20,
                )
                r.raise_for_status()
                data = r.json()
                url = str(data.get("url", "") or "")
                if url.startswith("http"):
                    return url
                last_error = f"方源返回空链接（{br}kbps）"
            except Exception as e:
                last_error = str(e)
        raise RuntimeError(f"这首网易云曲目暂时无法取得音源：{last_error}")
    raise RuntimeError("未知的在线音源")


def _safe_name(value: str) -> str:
    value = re.sub(r"[\\/:*?\"<>|\r\n\t]+", "_", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:48] or "track"


def cache_path_for(track: Track, cache_dir: Path | None = None) -> Path:
    cache_dir = cache_dir or (CACHE_DIR / "music")
    cache_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".mp3" if track.source == "netease" else ".m4a"
    digest = hashlib.sha1((track.source + ":" + track.id + ":" + track.title).encode("utf-8")).hexdigest()[:12]
    return cache_dir / f"{_safe_name(track.title)}_{digest}{suffix}"


def download_track(
    track: Track,
    *,
    progress: Callable[[int, str], None] | None = None,
    cache_dir: Path | None = None,
    max_mb: int = 60,
) -> Path:
    target = cache_path_for(track, cache_dir)
    if target.exists() and target.stat().st_size > 20_000:
        if progress:
            progress(100, "已使用本地缓存")
        return target
    url = resolve_stream(track)
    if progress:
        progress(0, "正在连接音源…")
    tmp = target.with_suffix(target.suffix + ".part")
    got = 0
    total = 0
    with requests.get(url, headers=HEADERS, timeout=(12, 60), stream=True, allow_redirects=True) as r:
        r.raise_for_status()
        ctype = str(r.headers.get("content-type", "")).lower()
        content_length = int(r.headers.get("content-length") or 0)
        if "text/html" in ctype:
            raise RuntimeError("音源返回了网页而不是音频，可能已失效。")
        total = content_length
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                f.write(chunk)
                got += len(chunk)
                if got > max_mb * 1024 * 1024:
                    raise RuntimeError("音频文件超过大小限制，已取消下载。")
                if progress:
                    pct = int(got / total * 100) if total else min(92, int(got / 500_000 * 10))
                    label = f"正在获取 {pct}% · {got / 1024 / 1024:.1f} MB"
                    progress(pct, label)
    if got < 8_000:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        raise RuntimeError("下载到的音频太小，可能不是有效文件。")
    # Some sources label m4a as mp3; the player sniffs the actual container.
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp.replace(target)
    if progress:
        progress(100, "已缓存到本地")
    return target


class SearchThread(QThread):
    ok = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, query: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        try:
            tracks = search_all(self.query)
            self.ok.emit(tracks)
        except Exception as e:
            self.failed.emit(str(e))


class DownloadThread(QThread):
    progress = pyqtSignal(int, str)
    ready = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, track: Track, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.track = track

    def run(self) -> None:
        try:
            path = download_track(self.track, progress=lambda p, s: self.progress.emit(p, s))
            self.ready.emit(str(path))
        except Exception as e:
            self.failed.emit(str(e))


class MusicEngine(QObject):
    state_changed = pyqtSignal(bool)
    track_changed = pyqtSignal(str, str, str, bool)
    position_changed = pyqtSignal(int, int)
    loading_changed = pyqtSignal(bool, str)
    error_occurred = pyqtSignal(str)
    queue_changed = pyqtSignal()
    about_to_play = pyqtSignal(object)

    def __init__(self, parent: QObject | None = None, volume: int = 42) -> None:
        super().__init__(parent)
        self.player = QMediaPlayer(self)
        self.player.setVolume(max(0, min(100, int(volume))))
        self.player.stateChanged.connect(self._on_state)
        self.player.mediaStatusChanged.connect(self._on_status)
        self.player.positionChanged.connect(self._on_position)
        self.player.durationChanged.connect(self._on_duration)
        self.player.error.connect(self._on_error)
        self.queue: list[Playable] = []
        self.index = -1
        self.repeat_mode = 1  # 0 off, 1 all, 2 one
        self.shuffle = False
        self._download: DownloadThread | None = None
        self._threads: list[DownloadThread] = []
        self._generation = 0
        self._play_token = 0
        self._loading = False
        self._current_title = ""
        self._current_subtitle = ""
        self._current_kind = "local"
        self._duration = 0

    # ------------------------------------------------------------------
    def set_volume(self, value: int) -> None:
        self.player.setVolume(max(0, min(100, int(value))))

    @property
    def volume(self) -> int:
        return int(self.player.volume())

    def is_playing(self) -> bool:
        return self.player.state() == QMediaPlayer.PlayingState

    def current_playable(self) -> Playable | None:
        if 0 <= self.index < len(self.queue):
            return self.queue[self.index]
        return None

    def current_text(self) -> tuple[str, str, str]:
        return self._current_title, self._current_subtitle, self._current_kind

    def play_queue(self, items: list[Playable], index: int = 0) -> None:
        self.queue = list(items)
        self.queue_changed.emit()
        if not self.queue:
            return
        self.index = max(0, min(index, len(self.queue) - 1))
        self._play_current()

    def play_local_folder(self, folder: str | Path, start_index: int = 0) -> list[Playable]:
        files = scan_folder(folder)
        items = [
            Playable(title=p.stem, subtitle="本地曲库", path=p, duration=0)
            for p in files
        ]
        if items and 0 <= start_index < len(items):
            self.play_queue(items, start_index)
        return items

    def ensure_playing(self, folder: str | Path) -> bool:
        if self.player.state() == QMediaPlayer.PlayingState:
            return True
        if self.player.state() == QMediaPlayer.PausedState and self.current_playable():
            self.player.play()
            return True
        if self.current_playable():
            self.player.play()
            return True
        items = self.play_local_folder(folder)
        return bool(items)

    def toggle(self) -> None:
        state = self.player.state()
        if state == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.current_playable():
            self.player.play()

    def stop(self) -> None:
        self._generation += 1
        for worker in list(self._threads):
            try:
                if worker.isRunning():
                    worker.quit()
            except RuntimeError:
                # The C++ object may already have been deleted after finishing.
                pass
        self.player.stop()
        self._set_loading(False, "")

    def next(self, *, automatic: bool = False) -> None:
        if not self.queue:
            return
        if self.repeat_mode == 2 and automatic:
            self.player.setPosition(0)
            self.player.play()
            return
        if self.shuffle and len(self.queue) > 1:
            import random

            choices = [i for i in range(len(self.queue)) if i != self.index]
            self.index = random.choice(choices)
        else:
            nxt = self.index + 1
            if nxt >= len(self.queue):
                if self.repeat_mode == 0:
                    if automatic:
                        self.player.stop()
                    return
                nxt = 0
            self.index = nxt
        self._play_current()

    def previous(self) -> None:
        if not self.queue:
            return
        prev = self.index - 1
        if prev < 0:
            prev = len(self.queue) - 1
        self.index = prev
        self._play_current()

    def seek(self, ms: int) -> None:
        self.player.setPosition(max(0, int(ms)))

    def _play_current(self) -> None:
        item = self.current_playable()
        if not item:
            return
        token = self._play_token + 1
        self._play_token = token
        self._current_title = item.title
        self._current_subtitle = item.subtitle
        self._current_kind = "online" if item.is_online else "local"
        if item.path and item.path.exists():
            self._start_local(item.path)
            return
        if item.track:
            cached = cache_path_for(item.track)
            if cached.exists() and cached.stat().st_size > 20_000:
                self._start_local(cached)
                return
            self._download_online(item.track, token)
            return
        self.error_occurred.emit("这个曲目没有可播放的文件。")

    def _start_local(self, path: Path) -> None:
        self._set_loading(False, "")
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(str(path))))
        self.player.play()
        self.about_to_play.emit(self.current_playable())

    def _download_online(self, track: Track, token: int) -> None:
        self.player.stop()
        self._set_loading(True, f"正在获取「{track.title}」…")
        self.track_changed.emit(track.title, track.subtitle, "online", False)
        if self._download:
            try:
                if self._download.isRunning():
                    # Keep the old thread alive but ignore its result via token.
                    pass
            except RuntimeError:
                self._download = None
        worker = DownloadThread(track, self)
        worker.progress.connect(lambda p, s: self._on_download_progress(p, s, token))
        worker.ready.connect(lambda path: self._on_download_ready(path, token))
        worker.failed.connect(lambda msg: self._on_download_failed(msg, token))
        worker.finished.connect(lambda: self._forget_thread(worker))
        self._download = worker
        self._threads.append(worker)
        worker.start()

    def _forget_thread(self, worker: DownloadThread) -> None:
        if self._download is worker:
            self._download = None
        if worker in self._threads:
            self._threads.remove(worker)
        worker.deleteLater()

    def shutdown(self) -> None:
        """Stop playback and give in-flight cache downloads a chance to end."""
        self._generation += 1
        self._play_token += 1
        try:
            self.player.stop()
        except Exception:
            pass
        for worker in list(self._threads):
            try:
                if worker.isRunning():
                    worker.wait(2200)
                if worker.isRunning():
                    # Never destroy a live QThread together with the window.  The
                    # daemon-like object is kept until the process exits.
                    worker.setParent(None)
                    _ORPHAN_THREADS.append(worker)
            except RuntimeError:
                pass
            if worker in self._threads:
                self._threads.remove(worker)

    def _on_download_progress(self, pct: int, label: str, token: int) -> None:
        if token != self._play_token:
            return
        self._set_loading(True, label)

    def _on_download_ready(self, path: str, token: int) -> None:
        if token != self._play_token:
            return
        self._set_loading(False, "")
        self._start_local(Path(path))

    def _on_download_failed(self, message: str, token: int) -> None:
        if token != self._play_token:
            return
        self._set_loading(False, "")
        self.error_occurred.emit(f"在线曲目获取失败：{message}")

    def _set_loading(self, loading: bool, text: str) -> None:
        self._loading = loading
        self.loading_changed.emit(loading, text)

    def _on_state(self, state) -> None:
        playing = state == QMediaPlayer.PlayingState
        self.state_changed.emit(playing)
        if self._current_title:
            self.track_changed.emit(self._current_title, self._current_subtitle, self._current_kind, playing)

    def _on_status(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia:
            self.next(automatic=True)
        elif status == QMediaPlayer.LoadedMedia:
            self._duration = int(self.player.duration())
            self.position_changed.emit(int(self.player.position()), self._duration)

    def _on_position(self, pos: int) -> None:
        self.position_changed.emit(int(pos), int(self.player.duration()))

    def _on_duration(self, duration: int) -> None:
        self._duration = int(duration)
        self.position_changed.emit(int(self.player.position()), self._duration)

    def _on_error(self, error) -> None:
        if error == QMediaPlayer.NoError:
            return
        message = self.player.errorString() or "播放器遇到未知错误"
        self._set_loading(False, "")
        self.error_occurred.emit(f"无法播放这首音频：{message}")
