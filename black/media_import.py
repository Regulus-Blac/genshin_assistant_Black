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
import time
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


def _season_episodes(sections: list) -> list[dict]:
    """Flatten a Bilibili season into download entries."""
    entries: list[dict] = []
    for section in sections:
        section_title = clean_html(section.get("title") or "")
        for episode in section.get("episodes") or []:
            ep_bvid = str(episode.get("bvid") or "")
            arc = episode.get("arc") or {}
            if not ep_bvid:
                continue
            entries.append({
                "title": clean_html(episode.get("title") or ep_bvid),
                "url": f"https://www.bilibili.com/video/{ep_bvid}",
                "duration": int(arc.get("duration") or 0),
                "group": section_title or "合集",
            })
    return entries


def bilibili_scopes(url: str) -> dict:
    """All the scopes a Bilibili video can be imported in.

    A video can be a multi-P upload (``pages``) *and* one episode of a UP's
    season (``ugc_season``).  They are very different scopes: the 至冬 OST album
    is 102 parts of one video, while the UP's "OST 合集" is 44 other albums.
    So ``pages`` is the default and the season (or the section that actually
    contains this video) is offered as an alternative instead of replacing it.
    """
    bvid = _parse_bvid(url)
    if not bvid:
        return {"title": "", "scopes": []}
    r = requests.get(
        "https://api.bilibili.com/x/web-interface/view",
        params={"bvid": bvid},
        headers=BILI_HEADERS,
        timeout=20,
    )
    r.raise_for_status()
    payload = r.json()
    if payload.get("code") != 0:
        return {"title": "", "scopes": []}
    data = payload.get("data") or {}
    title = clean_html(data.get("title") or bvid)

    scopes: list[dict] = []
    pages = data.get("pages") or []
    if isinstance(pages, list) and len(pages) > 1:
        entries = []
        for i, page in enumerate(pages, 1):
            entries.append({
                "title": clean_html(page.get("part") or f"P{i}"),
                "url": f"https://www.bilibili.com/video/{bvid}?p={i}",
                "duration": int(page.get("duration") or 0),
                "group": f"P{i}",
            })
        scopes.append({"id": "pages", "label": f"本视频的分P（{len(entries)} 段）", "entries": entries})

    season = data.get("ugc_season") or {}
    sections = season.get("sections") or []
    if sections:
        season_title = clean_html(season.get("title") or "合集")
        current = None
        for index, section in enumerate(sections):
            episodes = section.get("episodes") or []
            if any(str(ep.get("bvid") or "") == bvid for ep in episodes):
                current = (index, section, episodes)
                break
        if current is not None:
            index, section, episodes = current
            section_title = clean_html(section.get("title") or "")
            section_label = section_title if section_title and section_title != "正片" else season_title
            if len(episodes) > 1:
                scopes.append({
                    "id": f"section-{index}",
                    "label": f"所在合集《{section_label}》（{len(episodes)} 段）",
                    "entries": _season_episodes([section]),
                })
        every = _season_episodes(sections)
        if len(every) > 1 and all(len(scope["entries"]) != len(every) for scope in scopes):
            scopes.append({
                "id": "season",
                "label": f"整个合集《{season_title}》（{len(every)} 段）",
                "entries": every,
            })
    return {"title": title, "scopes": scopes}


def probe_media(url: str) -> dict:
    """Look before downloading: is this a single video or a collection?"""
    url = str(url or "").strip()
    info = bilibili_scopes(url)
    scopes = info.get("scopes") or []
    if scopes:
        return {
            "kind": "collection",
            "title": info.get("title") or "B站合集",
            "scopes": scopes,
            "entries": scopes[0]["entries"],
        }

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
        return {
            "kind": "collection",
            "title": clean_html(info.get("title") or "播放列表"),
            "scopes": [{"id": "playlist", "label": f"播放列表（{len(flat)} 段）", "entries": flat}],
            "entries": flat,
        }
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


def friendly_download_error(message: str) -> str:
    """Short, actionable Chinese text for the common yt-dlp failures."""
    text = str(message)
    low = text.lower()
    if "unable to extract initial state" in low:
        return "B 站解析被拦截（多半需要登录或触发了风控），稍后重试或更新 yt-dlp"
    if "video unavailable" in low or "404" in text or "not found" in low:
        return "视频不存在或已被删除"
    if "private" in low:
        return "视频是私密的，无法下载"
    if "sign in" in low or "login" in low or "cookies" in low:
        return "需要登录 B 站才能下载"
    if "timed out" in low or "timeout" in low:
        return "网络超时"
    if "ffmpeg" in low:
        return "ffmpeg 转换失败"
    return text[:140]


def _retryable(message: str) -> bool:
    low = str(message).lower()
    return any(
        key in low
        for key in (
            "unable to extract initial state",
            "timed out",
            "timeout",
            "temporarily",
            "connection reset",
            "502",
            "503",
        )
    )


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
    attempts = 2
    for attempt in range(1, attempts + 1):
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
            message = str(e)
            if attempt < attempts and _retryable(message):
                progress(0, f"解析失败，正在重试（{attempt}/{attempts - 1}）…")
                time.sleep(1.5)
                continue
            raise RuntimeError(f"yt-dlp 解析失败：{friendly_download_error(message)}") from e
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"下载或转换失败：{type(e).__name__} · {str(e)[:300]}") from e
    raise RuntimeError("下载失败：重试后仍未成功")


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
    """Download one or more videos sequentially and convert each one to MP3.

    A single broken link must not throw away the songs that already arrived:
    failures are skipped (with a short reason) and reported at the end.
    """

    progress = pyqtSignal(int, str)
    done = pyqtSignal(list)
    failed = pyqtSignal(str)
    skipped = pyqtSignal(str)

    def __init__(self, urls, output_dir: str | Path, parent=None) -> None:
        super().__init__(parent)
        if isinstance(urls, str):
            urls = [urls]
        self.urls = [str(u) for u in urls if u]
        self.output_dir = output_dir

    def run(self) -> None:
        saved: list[str] = []
        failures: list[tuple[int, str]] = []
        total = max(1, len(self.urls))
        for index, url in enumerate(self.urls, 1):
            def hook(pct: int, text: str, _i: int = index) -> None:
                overall = int(((_i - 1) + max(0, min(100, pct)) / 100) / total * 100)
                prefix = f"第 {_i}/{total} 首 · " if total > 1 else ""
                self.progress.emit(overall, f"{prefix}{text}")

            try:
                saved.append(str(download_audio(url, self.output_dir, progress=hook)))
            except Exception as e:
                reason = friendly_download_error(str(e))
                failures.append((index, reason))
                self.progress.emit(
                    int(index / total * 100),
                    f"第 {index}/{total} 首失败，已跳过：{reason}",
                )
                # Small pause between items: blasting Bilibili back to back is
                # what usually triggers its anti-bot page.
                if index < total:
                    time.sleep(0.8)
        if saved:
            self.done.emit(saved)
        if failures:
            sample = "；".join(f"第 {i} 首：{msg}" for i, msg in failures[:3])
            extra = f" 等 {len(failures)} 首" if len(failures) > 3 else ""
            if saved:
                self.skipped.emit(f"已跳过 {len(failures)} 首{extra}（{sample}），其余 {len(saved)} 首已保存。")
            else:
                self.failed.emit(f"全部 {len(failures)} 首都没能下载：{sample}")
        elif not saved:
            self.failed.emit("没有可下载的内容")
