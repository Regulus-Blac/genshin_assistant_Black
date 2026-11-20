"""Bilibili search / general media-to-MP3 import for Black.

Instead of driving fragile web converters, the app uses yt-dlp to fetch the
audio stream and the bundled ffmpeg to create a local MP3.  Direct Bilibili
links work, and a keyword search picks public videos from Bilibili's search
interface.  Other yt-dlp-supported sites work with direct URLs as well.
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from PyQt5.QtCore import QThread, pyqtSignal

try:
    import yt_dlp
    from yt_dlp.utils import DownloadError
except Exception:  # pragma: no cover - shown as a friendly UI message
    yt_dlp = None
    DownloadError = Exception

try:
    import imageio_ffmpeg
except Exception:  # pragma: no cover
    imageio_ffmpeg = None

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
BILI_HEADERS = {"User-Agent": UA, "Referer": "https://www.bilibili.com/"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".flac", ".wav", ".aac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mkv", ".webm", ".flv", ".mov", ".ts", ".m4v"}


@dataclass
class BiliResult:
    bvid: str
    title: str
    author: str
    duration: str
    duration_seconds: int
    url: str
    pic: str = ""

    @property
    def display(self) -> str:
        return f"{self.title}  ·  {self.author}  ·  {self.duration}"


def clean_html(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", str(value or ""))).strip()


def parse_duration(value) -> int:
    try:
        parts = [int(x) for x in str(value).split(":")]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
    except Exception:
        pass
    try:
        return int(value)
    except Exception:
        return 0


def ffmpeg_executable() -> str | None:
    if imageio_ffmpeg is None:
        return None
    try:
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def dependencies_ready() -> tuple[bool, str]:
    if yt_dlp is None:
        return False, "缺少 yt-dlp。请运行：python -m pip install yt-dlp imageio-ffmpeg"
    if ffmpeg_executable() is None:
        return False, "缺少 ffmpeg。请运行：python -m pip install imageio-ffmpeg"
    return True, ""


def bilibili_search(query: str, limit: int = 12) -> list[BiliResult]:
    query = query.strip()
    if not query:
        return []
    r = requests.get(
        "https://api.bilibili.com/x/web-interface/wbi/search/type",
        params={"search_type": "video", "keyword": query, "page": 1},
        headers=BILI_HEADERS,
        timeout=25,
    )
    r.raise_for_status()
    data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(data.get("message") or "B站搜索接口没有返回结果")
    rows = (data.get("data") or {}).get("result") or []
    out: list[BiliResult] = []
    for item in rows[:limit]:
        bvid = str(item.get("bvid") or "")
        if not bvid:
            continue
        title = clean_html(item.get("title", "")) or bvid
        duration = str(item.get("duration", ""))
        out.append(
            BiliResult(
                bvid=bvid,
                title=title,
                author=clean_html(item.get("author", "")),
                duration=duration,
                duration_seconds=parse_duration(duration),
                url=f"https://www.bilibili.com/video/{bvid}",
                pic=str(item.get("pic", "") or ""),
            )
        )
    return out


BVID_RE = re.compile(r"(BV[0-9A-Za-z]{10})")


def _parse_bvid(url: str) -> str:
    match = BVID_RE.search(str(url or ""))
    return match.group(1) if match else ""


def _fmt_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def bilibili_parts(url: str) -> list[dict]:
    """Return the parts/collection of a Bilibili video.

    Bilibili exposes two different multi-video shapes: ``pages`` (多 P, one BV
    with several parts) and ``ugc_season`` (UP 主的合集, several BVs).  yt-dlp
    only downloads the first one when ``noplaylist`` is on, which is why a
    collection used to import just its first song.
    """
    bvid = _parse_bvid(url)
    if not bvid:
        return []
    r = requests.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid},
        headers=BILI_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") != 0:
        return []
    data = payload.get("data") or {}

    parts: list[dict] = []
    season = data.get("ugc_season") or {}
    sections = season.get("sections") or []
    for section in sections:
        section_title = clean_html(section.get("title") or "")
        for episode in section.get("episodes") or []:
            ep_bvid = str(episode.get("bvid") or "")
            arc = episode.get("arc") or {}
            if not ep_bvid:
                continue
            parts.append({
                "title": clean_html(episode.get("title") or ep_bvid),
                "url": f"https://www.bilibili.com/video/{ep_bvid}",
                "duration": int(arc.get("duration") or 0),
                "group": section_title or "合集",
            })
    if len(parts) > 1:
        return parts

    pages = data.get("pages") or []
    if isinstance(pages, list) and len(pages) > 1:
        for i, page in enumerate(pages, 1):
            parts.append({
                "title": clean_html(page.get("part") or f"P{i}"),
                "url": f"https://www.bilibili.com/video/{bvid}?p={i}",
                "duration": int(page.get("duration") or 0),
                "group": "分P",
            })
    return parts


def probe_media(url: str) -> dict:
    """Look before downloading: is this a single video or a collection?"""
    url = str(url or "").strip()
    bili = bilibili_parts(url)
    if bili:
        return {"kind": "collection", "title": "B站合集", "entries": bili}

    ok, detail = dependencies_ready()
    if not ok:
        raise RuntimeError(detail)
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "http_headers": BILI_HEADERS,
        "socket_timeout": 30,
        "retries": 2,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if not info:
        return {"kind": "single", "title": "", "entries": []}
    entries = info.get("entries") or []
    flat = []
    for i, entry in enumerate(entries, 1):
        if not entry:
            continue
        flat.append({
            "title": clean_html(entry.get("title") or f"第 {i} 段"),
            "url": str(entry.get("webpage_url") or entry.get("url") or ""),
            "duration": int(entry.get("duration") or 0),
            "group": "播放列表",
        })
    if len(flat) > 1:
        return {"kind": "collection", "title": clean_html(info.get("title") or "播放列表"), "entries": flat}
    return {"kind": "single", "title": clean_html(info.get("title") or ""), "entries": []}


def safe_filename(name: str, max_len: int = 86) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", name).strip()
    name = re.sub(r"\s+", " ", name)
    return name[:max_len] or "BGM"


def _unique_path(folder: Path, name: str, suffix: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    base = safe_filename(name)
    path = folder / f"{base}{suffix}"
    n = 2
    while path.exists():
        path = folder / f"{base} ({n}){suffix}"
        n += 1
    return path


def _progress_hook_factory(callback: Callable[[int, str], None]):
    def hook(d: dict) -> None:
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            got = d.get("downloaded_bytes") or 0
            if total:
                pct = min(92, int(got / total * 88))
                mb = got / 1024 / 1024
                callback(pct, f"正在获取音频 · {mb:.1f} MB")
            else:
                callback(20, "正在获取音频…")
        elif d.get("status") == "finished":
            callback(94, "下载完成，正在转换为 MP3…")

    return hook


def download_audio(url: str, output_dir: str | Path, *, progress: Callable[[int, str], None] | None = None) -> Path:
    ok, detail = dependencies_ready()
    if not ok:
        raise RuntimeError(detail)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    progress = progress or (lambda p, s: None)
    ffmpeg = ffmpeg_executable()
    outtmpl = str(output_dir / "%(title).70s [%(id)s].%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ffmpeg_location": ffmpeg,
        "restrictfilenames": False,
        "windowsfilenames": True,
        "progress_hooks": [_progress_hook_factory(progress)],
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "http_headers": BILI_HEADERS,
        "retries": 3,
        "socket_timeout": 30,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info is None:
                raise RuntimeError("没有解析到可下载的音频")
            prepared = Path(ydl.prepare_filename(info)).with_suffix(".mp3")
            if prepared.exists():
                progress(100, "已保存 MP3")
                return prepared
            track_id = str(info.get("id") or "")
            for candidate in sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True):
                if track_id and track_id in candidate.name:
                    progress(100, "已保存 MP3")
                    return candidate
            # The postprocessor may have used a truncated title; fall back to
            # the newest MP3 if it was written during this call.
            newest = sorted(output_dir.glob("*.mp3"), key=lambda p: p.stat().st_mtime, reverse=True)
            if newest:
                progress(100, "已保存 MP3")
                return newest[0]
            raise RuntimeError("转换完成后没有找到 MP3 文件")
    except DownloadError as e:
        raise RuntimeError(f"yt-dlp 解析失败：{str(e)[:300]}") from e
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(f"下载或转换失败：{type(e).__name__} · {str(e)[:300]}") from e


def convert_local_media(input_path: str | Path, output_dir: str | Path) -> Path:
    ok, detail = dependencies_ready()
    if not ok:
        raise RuntimeError(detail)
    input_path = Path(input_path)
    if not input_path.exists():
        raise RuntimeError(f"文件不存在：{input_path}")
    ffmpeg = ffmpeg_executable()
    target = _unique_path(Path(output_dir), input_path.stem, ".mp3")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "192k",
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not target.exists():
        message = (proc.stderr or "")[-400:].strip()
        raise RuntimeError(f"ffmpeg 转换失败：{message or '未知错误'}")
    return target


class SearchThread(QThread):
    ok = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, query: str, parent=None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        try:
            self.ok.emit(bilibili_search(self.query))
        except Exception as e:
            self.failed.emit(str(e))


class ProbeThread(QThread):
    """Ask whether a link is a single video or a collection before importing."""

    ok = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.url = url

    def run(self) -> None:
        try:
            self.ok.emit(probe_media(self.url))
        except Exception as e:
            self.failed.emit(str(e))


class ImportThread(QThread):
    """Download one or more videos sequentially and convert each one to MP3."""

    progress = pyqtSignal(int, str)
    done = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, urls, output_dir: str | Path, parent=None) -> None:
        super().__init__(parent)
        if isinstance(urls, str):
            urls = [urls]
        self.urls = [str(u) for u in urls if u]
        self.output_dir = output_dir

    def run(self) -> None:
        saved: list[str] = []
        total = max(1, len(self.urls))
        try:
            for index, url in enumerate(self.urls, 1):
                def hook(pct: int, text: str, _i: int = index) -> None:
                    overall = int(((_i - 1) + max(0, min(100, pct)) / 100) / total * 100)
                    prefix = f"第 {_i}/{total} 首 · " if total > 1 else ""
                    self.progress.emit(overall, f"{prefix}{text}")

                saved.append(str(download_audio(url, self.output_dir, progress=hook)))
            self.done.emit(saved)
        except Exception as e:
            if saved:
                self.done.emit(saved)
            self.failed.emit(f"已完成 {len(saved)}/{total} 首，之后失败：{e}")
