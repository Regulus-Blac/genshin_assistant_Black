from __future__ import annotations

import json
import os
import shutil
import uuid
from collections import defaultdict
from datetime import date as date_cls
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from . import content
from .levels import (
    LevelInfo,
    format_duration,
    format_short_duration,
    level_info,
)
from .paths import (
    CHAT_PATH,
    CONFIG_PATH,
    DATA_DIR,
    JOURNAL_DIR,
    MUSIC,
    ensure_dirs,
)

WEEKDAYS = "一二三四五六日"
APP_VERSION = 1
MAX_SESSIONS = 6000
MAX_CHAT = 120
USER_NOTES_MARKER = "<!-- BLACK:USER-NOTES -->"

DEFAULT_SETTINGS: dict[str, Any] = {
    "user_name": "旅行者",
    "assistant_name": "Black",
    "quote_interval_min": 20,
    "desktop_whisper": True,
    "tts_enabled": False,
    "tts_rate": -1,
    "always_on_top": False,
    "close_to_tray": True,
    "music_folder": str(MUSIC),
    "music_volume": 42,
    "sound_volume": 80,
    "auto_play_bgm": False,
    "music_mode": "sequence",
    "music_rate": 1.0,
    "local_order": [],
    "last_local_track": "",
    "whisper_avatar": "派蒙",
    "character": "vodyanitsa",
    "character_order": [],
    "look": "",
    "appearance": "dark",
    "api_base": "https://api.deepseek.com",
    "api_model": "deepseek-flash",
    "api_key": "",
    "art": "art_snow.jpg",
    "first_run_done": False,
}


def _default_exams() -> list[dict]:
    return [
        {
            "id": "cet6",
            "name": "六级考试",
            "short": "CET-6",
            "date": "2026-12-12",
            "time": "15:00",
            "end_time": "17:25",
            "note": "全国大学英语六级笔试 · 记得打印准考证",
            "element": "hydro",
            "color": "#72cfd9",
        },
        {
            "id": "algorithm",
            "name": "算法考试",
            "short": "ALGORITHM",
            "date": "2026-12-26",
            "time": "09:00",
            "end_time": "11:00",
            "note": "示例日期，点开卡片改成你的真实考试时间",
            "element": "electro",
            "color": "#b79bea",
        },
    ]


def _default_subjects() -> list[dict]:
    now = datetime.now().isoformat(timespec="seconds")
    return [
        {
            "id": "algo",
            "name": "算法",
            "element": "dendro",
            "color": "#96cc8e",
            "goal_min": 90,
            "note": "刷题 · 复杂度 · 手写模板",
            "created": now,
            "days": {},
            "seen_level": 1,
        },
        {
            "id": "english",
            "name": "英语",
            "element": "hydro",
            "color": "#73cfe0",
            "goal_min": 45,
            "note": "六级听力 · 阅读 · 单词",
            "created": now,
            "days": {},
            "seen_level": 1,
        },
        {
            "id": "research",
            "name": "科研",
            "element": "electro",
            "color": "#c1a0eb",
            "goal_min": 60,
            "note": "论文 · 实验 · 笔记",
            "created": now,
            "days": {},
            "seen_level": 1,
        },
    ]


def _default_data() -> dict:
    return {
        "version": APP_VERSION,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "settings": dict(DEFAULT_SETTINGS),
        "exams": _default_exams(),
        "subjects": _default_subjects(),
        "active": None,
        "sessions": [],
        "playlists": [
            {"id": "local", "name": "本地曲库", "builtin": True, "tracks": []},
        ],
        "launches": 1,
    }


def _dt(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _today_key(d: date_cls | datetime | None = None) -> str:
    d = d or date_cls.today()
    if isinstance(d, datetime):
        d = d.date()
    return d.isoformat()


def _parse_date(value: str) -> date_cls | None:
    try:
        return date_cls.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _safe_slug(value: str) -> str:
    out = "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in "-_")
    return out[:24] or uuid.uuid4().hex[:8]


class Store:
    """Local JSON store for timers, streaks, exams and journal entries."""

    def __init__(
        self,
        config_path: Path | None = None,
        journal_dir: Path | None = None,
        *,
        now: datetime | None = None,
    ) -> None:
        ensure_dirs()
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.journal_dir = Path(journal_dir) if journal_dir else JOURNAL_DIR
        self.journal_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.chat_path = self.config_path.parent / "chat.json"
        self.data: dict = {}
        self.chat: list[dict] = []
        self.recovered_note: str = ""
        self._last_saved: datetime | None = None
        self._load(now=now)
        self._backup_once()
        self._load_chat()
        self.data["launches"] = int(self.data.get("launches", 0)) + 1
        self.save()

    # ------------------------------------------------------------------ load
    def _load(self, *, now: datetime | None = None) -> None:
        now = now or datetime.now()
        if not self.config_path.exists():
            self.data = _default_data()
            self.save()
            return
        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("not an object")
        except Exception:
            # Keep a rescue copy, then start fresh rather than crash on launch.
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            rescue = self.config_path.with_name(f"black.corrupt-{stamp}.json")
            try:
                shutil.copyfile(self.config_path, rescue)
            except Exception:
                pass
            self.data = _default_data()
            self.recovered_note = "配置文件无法读取，已启用一份新的本地数据。"
            self.save()
            return

        self.data = raw
        self._normalise()
        self._recover_active(now=now)
        self._normalise_seen_levels()
        self.save()

    def _normalise(self) -> None:
        data = self.data
        data.setdefault("version", APP_VERSION)
        data.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
        if not isinstance(data.get("settings"), dict):
            data["settings"] = {}
        for k, v in DEFAULT_SETTINGS.items():
            data["settings"].setdefault(k, v)
        # Migrate the old bundled DeepSeek example to the current official
        # defaults, but only while the user hasn't supplied a key of their own.
        settings = data["settings"]
        if (
            not str(settings.get("api_key", "") or "").strip()
            and str(settings.get("api_base", "")) == "https://api.deepseek.com/v1"
            and str(settings.get("api_model", "")) == "deepseek-chat"
        ):
            settings["api_base"] = "https://api.deepseek.com"
            settings["api_model"] = "deepseek-flash"
        if not settings.get("character"):
            settings["character"] = "vodyanitsa"
        if str(settings.get("appearance", "dark")).lower() not in ("dark", "light", "day"):
            settings["appearance"] = "dark"
        if "exams" not in data or not isinstance(data.get("exams"), list):
            data["exams"] = _default_exams()
        if "subjects" not in data or not isinstance(data.get("subjects"), list):
            data["subjects"] = _default_subjects()
        if not isinstance(data.get("sessions"), list):
            data["sessions"] = []
        data["sessions"] = data["sessions"][-MAX_SESSIONS:]
        self._normalise_playlists(data)
        # Timers: 1.7 allows several subjects to run at the same time.  Older
        # files kept exactly one timer in "active"; fold it into the new list.
        legacy = data.get("active")
        actives = data.get("actives")
        if not isinstance(actives, list):
            actives = []
        if isinstance(legacy, dict) and legacy.get("subject_id") and legacy.get("started_at"):
            if not any(item.get("subject_id") == legacy["subject_id"] for item in actives if isinstance(item, dict)):
                actives.append(legacy)
        clean_actives = []
        seen: set[str] = set()
        for entry in actives:
            if not isinstance(entry, dict):
                continue
            sid = str(entry.get("subject_id") or "")
            if not sid or sid in seen or not entry.get("started_at"):
                continue
            seen.add(sid)
            clean_actives.append(
                {
                    "subject_id": sid,
                    "started_at": str(entry["started_at"]),
                    "heartbeat": str(entry.get("heartbeat") or entry["started_at"]),
                }
            )
        data["actives"] = clean_actives
        data["active"] = None
        data.setdefault("launches", 0)

        clean_subjects = []
        for sub in data["subjects"]:
            if not isinstance(sub, dict):
                continue
            sub.setdefault("id", uuid.uuid4().hex[:8])
            sub.setdefault("name", "未命名")
            sub.setdefault("element", "anemo")
            sub.setdefault("color", "#d9bc7d")
            sub.setdefault("goal_min", 60)
            sub.setdefault("note", "")
            sub.setdefault("created", datetime.now().isoformat(timespec="seconds"))
            if not isinstance(sub.get("days"), dict):
                sub["days"] = {}
            sub["days"] = {
                str(k): max(0, int(v))
                for k, v in sub["days"].items()
                if _parse_date(str(k)) is not None and isinstance(v, (int, float))
            }
            sub["goal_min"] = max(5, min(720, int(sub.get("goal_min", 60) or 60)))
            clean_subjects.append(sub)
        data["subjects"] = clean_subjects

        clean_exams = []
        for exam in data["exams"]:
            if not isinstance(exam, dict) or not exam.get("name"):
                continue
            exam.setdefault("id", _safe_slug(exam["name"]))
            exam.setdefault("short", exam["id"].upper())
            exam.setdefault("date", "")
            exam.setdefault("time", "09:00")
            exam.setdefault("end_time", "")
            exam.setdefault("note", "")
            exam.setdefault("element", "hydro")
            exam.setdefault("color", "#72cfd9")
            clean_exams.append(exam)
        data["exams"] = clean_exams

    def _normalise_seen_levels(self) -> None:
        for sub in self.data.get("subjects", []):
            if "seen_level" not in sub:
                total = sum(int(v) for v in sub.get("days", {}).values())
                sub["seen_level"] = level_info(total, self.best_streak(sub)).level
            else:
                try:
                    sub["seen_level"] = max(1, int(sub["seen_level"]))
                except (TypeError, ValueError):
                    sub["seen_level"] = 1

    def _normalise_playlists(self, data: dict) -> None:
        raw = data.get("playlists")
        if not isinstance(raw, list):
            raw = []
        clean: list[dict] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                continue
            pid = str(item.get("id") or "").strip()
            if not pid or pid in seen:
                continue
            if pid == "local":
                clean.append(
                    {
                        "id": "local",
                        "name": "本地曲库",
                        "builtin": True,
                        "tracks": [],
                    }
                )
                seen.add(pid)
                continue
            tracks = item.get("tracks")
            if not isinstance(tracks, list):
                tracks = []
            clean.append(
                {
                    "id": pid,
                    "name": str(item.get("name") or "未命名歌单")[:40],
                    "builtin": False,
                    "tracks": [t for t in tracks if isinstance(t, dict)],
                }
            )
            seen.add(pid)
        if "local" not in seen:
            clean.insert(0, {"id": "local", "name": "本地曲库", "builtin": True, "tracks": []})
        data["playlists"] = clean

    def _recover_active(self, *, now: datetime) -> None:
        notes = []
        for entry in list(self.actives()):
            start = _dt(entry.get("started_at"))
            heartbeat = _dt(entry.get("heartbeat")) or start
            sid = str(entry.get("subject_id"))
            sub = self.subject(sid)
            if not start or not heartbeat or not sub:
                self._drop_active(sid)
                continue
            if (now - heartbeat).total_seconds() <= 180:
                continue
            # The app was probably force-closed; only count up to the last
            # heartbeat so hours spent with a closed laptop are not added.
            summary = self.pause(now=heartbeat, save=False, subject_id=sid)
            if summary and summary.get("seconds", 0) > 0:
                notes.append(
                    f"「{sub['name']}」在 {heartbeat.strftime('%H:%M')} 自动收尾，记录了 "
                    f"{format_short_duration(summary['seconds'])}"
                )
        if notes:
            self.recovered_note = "上次的计时" + "；".join(notes) + "。"

    def _drop_active(self, subject_id: str) -> None:
        self.data["actives"] = [
            item for item in self.actives() if item.get("subject_id") != subject_id
        ]

    def _backup_once(self) -> None:
        if not self.config_path.exists():
            return
        backup_dir = self.config_path.parent / "backup"
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d")
            target = backup_dir / f"black-{stamp}.json"
            if not target.exists():
                shutil.copyfile(self.config_path, target)
            old = sorted(backup_dir.glob("black-*.json"))
            for p in old[:-12]:
                p.unlink(missing_ok=True)
        except Exception:
            pass

    # ------------------------------------------------------------------ save
    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.config_path.with_suffix(".json.tmp")
        payload = json.dumps(self.data, ensure_ascii=False, indent=2)
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self.config_path)
        self._last_saved = datetime.now()

    @property
    def settings(self) -> dict:
        return self.data.setdefault("settings", {})

    def update_settings(self, **values) -> None:
        self.settings.update(values)
        self.save()

    # ------------------------------------------------------------------ playlists
    def playlists(self) -> list[dict]:
        return [dict(item) for item in self.data.get("playlists", [])]

    def playlist(self, playlist_id: str) -> dict | None:
        for item in self.data.get("playlists", []):
            if item.get("id") == playlist_id:
                return item
        return None

    def create_playlist(self, name: str) -> dict:
        name = (name or "未命名歌单").strip()[:40] or "未命名歌单"
        item = {
            "id": "pl-" + uuid.uuid4().hex[:10],
            "name": name,
            "builtin": False,
            "tracks": [],
        }
        self.data.setdefault("playlists", []).append(item)
        self.save()
        return item

    def rename_playlist(self, playlist_id: str, name: str) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin"):
            return False
        item["name"] = (name or "").strip()[:40] or item.get("name", "未命名歌单")
        self.save()
        return True

    def delete_playlist(self, playlist_id: str) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin"):
            return False
        self.data["playlists"] = [p for p in self.data["playlists"] if p.get("id") != playlist_id]
        self.save()
        return True

    @staticmethod
    def playlist_entry_key(entry: dict) -> str:
        if str(entry.get("kind")) == "online":
            track = entry.get("track") or {}
            return f"online:{track.get('source', '')}:{track.get('id', '')}"
        return "local:" + str(entry.get("path", ""))

    def add_to_playlist(self, playlist_id: str, entry: dict) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin") or not isinstance(entry, dict):
            return False
        key = self.playlist_entry_key(entry)
        if not key or key == "local:":
            return False
        if any(self.playlist_entry_key(t) == key for t in item.get("tracks", [])):
            return False
        item.setdefault("tracks", []).append(entry)
        self.save()
        return True

    def remove_from_playlist(self, playlist_id: str, index: int) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin"):
            return False
        tracks = item.get("tracks", [])
        if not 0 <= index < len(tracks):
            return False
        tracks.pop(index)
        self.save()
        return True

    def move_playlist_track(self, playlist_id: str, index: int, delta: int) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin"):
            return False
        tracks = item.get("tracks", [])
        target = index + delta
        if not 0 <= index < len(tracks) or not 0 <= target < len(tracks):
            return False
        tracks[index], tracks[target] = tracks[target], tracks[index]
        self.save()
        return True

    def set_playlist_tracks(self, playlist_id: str, tracks: list[dict]) -> bool:
        item = self.playlist(playlist_id)
        if not item or item.get("builtin"):
            return False
        item["tracks"] = list(tracks)
        self.save()
        return True

    def set_local_order(self, paths: list[str]) -> None:
        self.settings["local_order"] = [str(p) for p in paths]
        self.save()

    def update_local_path(self, old: str, new: str) -> None:
        old_path = str(old)
        new_path = str(new)
        order = [new_path if str(p) == old_path else str(p) for p in self.settings.get("local_order", [])]
        self.settings["local_order"] = order
        for item in self.playlists():
            if item.get("builtin"):
                continue
            changed = False
            tracks = list(item.get("tracks", []))
            for entry in tracks:
                if not isinstance(entry, dict) or entry.get("kind") != "local":
                    continue
                if str(entry.get("path", "")) == old_path:
                    entry["path"] = new_path
                    entry["title"] = Path(new_path).stem
                    changed = True
            if changed:
                self.set_playlist_tracks(str(item["id"]), tracks)
        self.save()

    def move_track_between_playlists(self, source_id: str, target_id: str, index: int) -> bool:
        source = self.playlist(source_id)
        target = self.playlist(target_id)
        if not source or not target or target.get("builtin"):
            return False
        tracks = source.get("tracks", [])
        if not 0 <= index < len(tracks):
            return False
        entry = tracks[index]
        if any(self.playlist_entry_key(t) == self.playlist_entry_key(entry) for t in target.get("tracks", [])):
            return False
        target.setdefault("tracks", []).append(entry)
        tracks.pop(index)
        self.save()
        return True

    # ------------------------------------------------------------------ active
    def actives(self) -> list[dict]:
        """Every running timer, one entry per subject (several may run at once).

        Returns the live list object when nothing needed cleaning, so callers
        can append/remove entries directly.
        """
        raw = self.data.get("actives")
        if not isinstance(raw, list):
            raw = []
            self.data["actives"] = raw
            return raw
        valid: list[dict] = []
        changed = False
        for entry in raw:
            if not isinstance(entry, dict) or not self.subject(entry.get("subject_id")):
                changed = True
                continue
            valid.append(entry)
        if changed:
            self.data["actives"] = valid
            return valid
        return raw

    def active(self, subject_id: str | None = None) -> dict | None:
        """First running timer (compatibility helper), or the one for a subject."""
        for entry in self.actives():
            if subject_id is None or entry.get("subject_id") == subject_id:
                return entry
        return None

    def is_active(self, subject_id: str) -> bool:
        return any(entry.get("subject_id") == subject_id for entry in self.actives())

    def active_subjects(self) -> list[dict]:
        names = []
        for entry in self.actives():
            sub = self.subject(entry.get("subject_id"))
            if sub:
                names.append(sub)
        return names

    def active_subject(self) -> dict | None:
        running = self.active_subjects()
        return running[0] if running else None

    def active_elapsed(self, now: datetime | None = None, subject_id: str | None = None) -> int:
        entry = self.active(subject_id)
        if not entry:
            return 0
        start = _dt(entry.get("started_at"))
        if not start:
            return 0
        return max(0, int(((now or datetime.now()) - start).total_seconds()))

    def _live_map(self, now: datetime | None = None) -> dict[str, dict[str, int]]:
        """Live seconds per subject and calendar day for every running timer."""
        now = now or datetime.now()
        result: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for entry in self.actives():
            start = _dt(entry.get("started_at"))
            if not start or now <= start:
                continue
            sid = str(entry.get("subject_id"))
            cursor = start
            while cursor.date() < now.date():
                boundary = datetime.combine(cursor.date() + timedelta(days=1), time.min)
                secs = int((boundary - cursor).total_seconds())
                if secs > 0:
                    result[sid][_today_key(cursor)] += secs
                cursor = boundary
            secs = int((now - cursor).total_seconds())
            if secs > 0:
                result[sid][_today_key(cursor)] += secs
        return {sid: dict(days) for sid, days in result.items()}

    def start(self, subject_id: str, now: datetime | None = None) -> bool:
        """Start a timer for one subject; other running timers keep running."""
        now = now or datetime.now()
        sub = self.subject(subject_id)
        if not sub:
            return False
        if self.is_active(subject_id):
            return False
        self.actives().append(
            {
                "subject_id": subject_id,
                "started_at": now.isoformat(timespec="seconds"),
                "heartbeat": now.isoformat(timespec="seconds"),
            }
        )
        self.data["active"] = None  # legacy single-timer key, no longer used
        self.save()
        return True

    def pause(
        self,
        now: datetime | None = None,
        *,
        save: bool = True,
        subject_id: str | None = None,
    ) -> dict | None:
        """Stop one timer (or the first running one) and record its segments."""
        entry = self.active(subject_id)
        if not entry:
            return None
        now = now or datetime.now()
        start = _dt(entry.get("started_at"))
        sid = str(entry.get("subject_id"))
        sub = self.subject(sid)
        remaining = [item for item in self.actives() if item is not entry]
        self.data["actives"] = remaining
        if not start or not sub or now <= start:
            if save:
                self.save()
            return {"subject_id": sid, "seconds": 0, "dates": []}

        total = 0
        dates: list[str] = []
        cursor = start
        while cursor.date() < now.date():
            boundary = datetime.combine(cursor.date() + timedelta(days=1), time.min)
            secs = int((boundary - cursor).total_seconds())
            if secs > 0:
                self._add_segment(sub, sid, cursor, boundary, secs)
                dates.append(_today_key(cursor))
                total += secs
            cursor = boundary
        secs = int((now - cursor).total_seconds())
        if secs > 0:
            self._add_segment(sub, sid, cursor, now, secs)
            dates.append(_today_key(cursor))
            total += secs
        if save:
            self.save()
        return {"subject_id": sid, "name": sub["name"], "seconds": total, "dates": dates}

    def pause_all(self, now: datetime | None = None, *, save: bool = True) -> list[dict]:
        """Stop every running timer, returning one summary per subject."""
        summaries = []
        for entry in list(self.actives()):
            summary = self.pause(now, save=False, subject_id=str(entry.get("subject_id")))
            if summary:
                summaries.append(summary)
        if save:
            self.save()
        return summaries

    def _add_segment(self, sub: dict, sid: str, start: datetime, end: datetime, seconds: int) -> None:
        key = _today_key(start)
        sub.setdefault("days", {})
        sub["days"][key] = int(sub["days"].get(key, 0)) + int(seconds)
        sessions = self.data.setdefault("sessions", [])
        sessions.append(
            {
                "id": uuid.uuid4().hex[:12],
                "subject_id": sid,
                "date": key,
                "start": start.isoformat(timespec="seconds"),
                "end": end.isoformat(timespec="seconds"),
                "seconds": int(seconds),
            }
        )
        if len(sessions) > MAX_SESSIONS:
            del sessions[: len(sessions) - MAX_SESSIONS]

    def heartbeat(self, now: datetime | None = None, *, save: bool = True) -> None:
        running = self.actives()
        if not running:
            return
        now = now or datetime.now()
        stamp = now.isoformat(timespec="seconds")
        for entry in running:
            entry["heartbeat"] = stamp
        if save:
            self.save()

    # ------------------------------------------------------------------ subjects
    def subject(self, subject_id: str | None) -> dict | None:
        if not subject_id:
            return None
        for sub in self.data.get("subjects", []):
            if sub.get("id") == subject_id:
                return sub
        return None

    def _day_seconds(self, sub: dict, key: str, now: datetime | None = None) -> int:
        value = int(sub.get("days", {}).get(key, 0))
        live = self._live_map(now).get(sub["id"], {})
        return value + int(live.get(key, 0))

    def _total_seconds(self, sub: dict, now: datetime | None = None) -> int:
        total = sum(int(v) for v in sub.get("days", {}).values())
        total += sum(self._live_map(now).get(sub["id"], {}).values())
        return total

    def best_streak(self, sub: dict, now: datetime | None = None) -> int:
        keys = {k for k, v in sub.get("days", {}).items() if int(v) > 0}
        keys.update(k for k, v in self._live_map(now).get(sub["id"], {}).items() if v > 0)
        dates = sorted(d for d in (_parse_date(k) for k in keys) if d is not None)
        best = 0
        run = 0
        prev = None
        for d in dates:
            if prev is not None and d == prev + timedelta(days=1):
                run += 1
            else:
                run = 1
            best = max(best, run)
            prev = d
        return best

    def _streak_ending(self, sub: dict, end: date_cls, now: datetime | None = None) -> int:
        keys = {k for k, v in sub.get("days", {}).items() if int(v) > 0}
        keys.update(k for k, v in self._live_map(now).get(sub["id"], {}).items() if v > 0)
        run = 0
        cur = end
        while cur.isoformat() in keys:
            run += 1
            cur -= timedelta(days=1)
        return run

    def current_streak(self, sub: dict, now: datetime | None = None) -> int:
        now = now or datetime.now()
        today = now.date()
        if self._day_seconds(sub, today.isoformat(), now) > 0:
            return self._streak_ending(sub, today, now)
        yesterday = today - timedelta(days=1)
        if self._day_seconds(sub, yesterday.isoformat(), now) > 0:
            return self._streak_ending(sub, yesterday, now)
        return 0

    def subject_info(self, sub: dict, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        today_key = _today_key(now)
        today = self._day_seconds(sub, today_key, now)
        total = self._total_seconds(sub, now)
        best = self.best_streak(sub, now)
        level = level_info(total, best)
        goal_seconds = max(300, int(sub.get("goal_min", 60)) * 60)
        sessions = [
            s for s in self.data.get("sessions", [])
            if s.get("subject_id") == sub["id"] and s.get("date") == today_key
        ]
        is_active = self.is_active(sub["id"])
        try:
            color = str(sub.get("color", "#d9bc7d"))
        except Exception:
            color = "#d9bc7d"
        return {
            "id": sub["id"],
            "name": sub.get("name", "未命名"),
            "element": sub.get("element", "anemo"),
            "color": color,
            "goal_min": int(sub.get("goal_min", 60)),
            "note": sub.get("note", ""),
            "today_seconds": today,
            "total_seconds": total,
            "streak": self.current_streak(sub, now),
            "best_streak": best,
            "level": level,
            "goal_seconds": goal_seconds,
            "goal_progress": min(1.0, today / goal_seconds if goal_seconds else 0),
            "active": is_active,
            "live_seconds": self.active_elapsed(now, subject_id=sub["id"]) if is_active else 0,
            "today_sessions": sessions,
        }

    def subjects(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        return [self.subject_info(s, now) for s in self.data.get("subjects", [])]

    def add_subject(self, name: str, *, element: str = "dendro", color: str = "#96cc8e", goal_min: int = 60, note: str = "") -> dict:
        name = name.strip()
        if not name:
            raise ValueError("名称不能为空")
        if len(name) > 16:
            name = name[:16]
        sid = _safe_slug(name)
        existing = {s["id"] for s in self.data["subjects"]}
        while sid in existing:
            sid = f"{sid}-{uuid.uuid4().hex[:4]}"
        sub = {
            "id": sid,
            "name": name,
            "element": element,
            "color": color,
            "goal_min": max(5, min(720, int(goal_min))),
            "note": note.strip()[:80],
            "created": datetime.now().isoformat(timespec="seconds"),
            "days": {},
            "seen_level": 1,
        }
        self.data["subjects"].append(sub)
        self.save()
        return sub

    def update_subject(self, subject_id: str, **values) -> bool:
        sub = self.subject(subject_id)
        if not sub:
            return False
        if "name" in values:
            name = str(values["name"]).strip()
            if not name:
                raise ValueError("名称不能为空")
            sub["name"] = name[:16]
        if "goal_min" in values:
            sub["goal_min"] = max(5, min(720, int(values["goal_min"])))
        for key in ("element", "color", "note"):
            if key in values:
                sub[key] = values[key]
        self.save()
        return True

    def delete_subject(self, subject_id: str) -> bool:
        sub = self.subject(subject_id)
        if not sub:
            return False
        if self.is_active(subject_id):
            self.pause(subject_id=subject_id)
        self.data["subjects"] = [s for s in self.data["subjects"] if s.get("id") != subject_id]
        self.save()
        return True

    def total_today(self, now: datetime | None = None) -> int:
        now = now or datetime.now()
        return sum(self._day_seconds(s, _today_key(now), now) for s in self.data["subjects"])

    def total_goal_today(self) -> int:
        return sum(max(300, int(s.get("goal_min", 60)) * 60) for s in self.data["subjects"])

    def total_all(self, now: datetime | None = None) -> int:
        now = now or datetime.now()
        return sum(self._total_seconds(s, now) for s in self.data["subjects"])

    def overall(self, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        today = self.total_today(now)
        goal = max(1, self.total_goal_today())
        running = self.active_subjects()
        return {
            "today_seconds": today,
            "today_text": format_duration(today),
            "goal_seconds": goal,
            "goal_progress": min(1.0, today / goal),
            "total_seconds": self.total_all(now),
            "active_name": "、".join(sub["name"] for sub in running) if running else None,
            "active_names": [sub["name"] for sub in running],
            "active_elapsed": max(
                (self.active_elapsed(now, subject_id=sub["id"]) for sub in running),
                default=0,
            ),
            "study_count": len([s for s in self.subjects(now) if s["today_seconds"] > 0]),
            "subject_count": len(self.data["subjects"]),
        }

    # ------------------------------------------------------------------ exams
    def exam_info(self, exam: dict, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        out = dict(exam)
        d = _parse_date(exam.get("date", ""))
        if not d:
            out.update({"days": None, "label": "待设定", "date_label": "尚未设定日期", "target": None, "passed": False, "same_day": False})
            return out
        try:
            hh, mm = [int(x) for x in str(exam.get("time", "09:00")).split(":")[:2]]
        except Exception:
            hh, mm = 9, 0
        target = datetime.combine(d, time(hh, mm))
        delta = target - now
        days = (d - now.date()).days
        if delta.total_seconds() <= 0:
            label = "已结束"
        elif days == 0:
            label = "今天"
        else:
            label = f"D-{days}"
        weekday = WEEKDAYS[d.weekday()]
        date_label = f"{d.year}.{d.month:02d}.{d.day:02d} 周{weekday} {hh:02d}:{mm:02d}"
        remaining = max(0, int(delta.total_seconds()))
        hours_left = int((remaining % 86400) // 3600)
        minutes_left = int((remaining % 3600) // 60)
        out.update(
            {
                "days": days if delta.total_seconds() > 0 else None,
                "label": label,
                "date_label": date_label,
                "target": target.isoformat(timespec="seconds"),
                "passed": delta.total_seconds() <= 0,
                "same_day": days == 0 and delta.total_seconds() > 0,
                "hours_left": hours_left,
                "minutes_left": minutes_left,
            }
        )
        return out

    def exams(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        items = [self.exam_info(e, now) for e in self.data.get("exams", [])]
        fallback = datetime.max
        items.sort(key=lambda x: (_parse_date(x.get("date", "")) or date_cls.max, x.get("time", "00:00")))
        return items

    def exam(self, exam_id: str) -> dict | None:
        for e in self.data.get("exams", []):
            if e.get("id") == exam_id:
                return e
        return None

    def save_exam(self, exam: dict) -> dict:
        name = str(exam.get("name", "")).strip()
        if not name:
            raise ValueError("考试名称不能为空")
        date_value = str(exam.get("date", "")).strip()
        if not _parse_date(date_value):
            raise ValueError("请选择有效的考试日期")
        payload = dict(exam)
        payload["name"] = name[:24]
        payload["date"] = date_value
        try:
            payload["time"] = time.fromisoformat(str(exam.get("time", "09:00"))[:5]).strftime("%H:%M")
        except Exception:
            payload["time"] = "09:00"
        payload["short"] = str(exam.get("short") or payload.get("id") or name).upper()[:16]
        payload["note"] = str(exam.get("note", ""))[:100]
        payload["element"] = exam.get("element", "hydro")
        payload["color"] = exam.get("color", "#72cfd9")
        existing = self.exam(str(payload.get("id", "")))
        if existing:
            existing.update(payload)
            result = existing
        else:
            payload["id"] = str(payload.get("id") or _safe_slug(name))
            while self.exam(payload["id"]):
                payload["id"] = f"{_safe_slug(name)}-{uuid.uuid4().hex[:4]}"
            self.data.setdefault("exams", []).append(payload)
            result = payload
        self.data["exams"].sort(key=lambda x: (x.get("date") or "9999", x.get("time") or ""))
        self.save()
        return result

    def delete_exam(self, exam_id: str) -> bool:
        before = len(self.data.get("exams", []))
        self.data["exams"] = [e for e in self.data.get("exams", []) if e.get("id") != exam_id]
        changed = len(self.data["exams"]) != before
        if changed:
            self.save()
        return changed

    def context(self, now: datetime | None = None) -> dict:
        now = now or datetime.now()
        overall = self.overall(now)
        exams = [
            {"name": e["name"], "days": e.get("days"), "label": e.get("label"), "date_label": e.get("date_label")}
            for e in self.exams(now)
        ]
        running = self.active_subjects()
        names = [sub["name"] for sub in running]
        return {
            "name": self.settings.get("user_name", "旅行者"),
            "exams": exams,
            "today_seconds": overall["today_seconds"],
            "today_text": overall["today_text"],
            "active": bool(names),
            "active_name": "、".join(names) if names else None,
            "active_names": names,
            "late": now.hour >= 23 or now.hour < 5,
            "overall": overall,
        }

    # ------------------------------------------------------------------ levels
    def collect_level_ups(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        ups = []
        changed = False
        for sub in self.data.get("subjects", []):
            info = self.subject_info(sub, now)
            seen = int(sub.get("seen_level", info["level"].level))
            if info["level"].level > seen:
                ups.append(
                    {
                        "id": sub["id"],
                        "name": sub["name"],
                        "level": info["level"].level,
                        "title": info["level"].title,
                        "old_level": seen,
                        "color": info["color"],
                        "element": info["element"],
                    }
                )
                sub["seen_level"] = info["level"].level
                changed = True
        if changed:
            self.save()
        return ups

    # ------------------------------------------------------------------ journal
    def journal_path(self, date_key: str) -> Path:
        return self.journal_dir / f"{date_key}.md"

    def daily_markdown(self, date_key: str, quote: dict | None = None, *, now: datetime | None = None) -> str:
        now = now or datetime.now()
        d = _parse_date(date_key) or now.date()
        key = d.isoformat()
        quote = quote or content.daily_quote(key)
        weekday = WEEKDAYS[d.weekday()]
        subjects = [self.subject_info(s, now) for s in self.data.get("subjects", [])]

        total = 0
        rows = []
        details = []
        study_names = []
        for info in subjects:
            sub = self.subject(info["id"])
            day_seconds = self._day_seconds(sub, key, now) if sub else 0
            total += day_seconds
            goal_seconds = info["goal_seconds"]
            pct = min(100, round(day_seconds / goal_seconds * 100)) if goal_seconds else 0
            total_seconds = info["total_seconds"]
            streak = self._streak_ending(sub, d, now) if sub else 0
            level = level_info(total_seconds, info["best_streak"])
            rows.append(
                f"| {info['name']} | {format_duration(day_seconds)} | {format_short_duration(total_seconds)} | {streak} 天 | {level.level} | {pct}% |"
            )
            sessions = [
                s for s in self.data.get("sessions", [])
                if s.get("subject_id") == info["id"] and s.get("date") == key
            ]
            if day_seconds > 0:
                study_names.append(info["name"])
            lines = [
                f"### {info['name']} · Lv.{level.level} {level.title}",
                "",
                f"- 今日：**{format_duration(day_seconds)}**（目标 {info['goal_min']} 分钟 · {pct}%）",
                f"- 累计：{format_duration(total_seconds)}",
                f"- 连续修习：{streak} 天",
            ]
            if sessions:
                def _session_time(value: str) -> str:
                    parsed = _dt(value)
                    return parsed.strftime("%H:%M") if parsed else "--:--"
                times = "、".join(f"{_session_time(s['start'])}–{_session_time(s['end'])}（{format_short_duration(s['seconds'])}）" for s in sessions)
                lines.append(f"- 今日计时：{times}")
            else:
                lines.append("- 今日计时：暂无已结束的计时段")
            details.append("\n".join(lines) + "\n")

        if total <= 0:
            headline = "今天还没有在书桌前留下计时。休息也是一种准备，但如果你愿意，Black 会陪你从十分钟开始。"
        elif total < 30 * 60:
            headline = "轻轻的开始也算数。专注的火苗还小，别急着让它烧成森林。"
        elif total < 2 * 3600:
            headline = "今天的光已经落在书页上了。稳定的一小段，比完美的一整天更容易坚持。"
        else:
            headline = "今天走了很远。提瓦特的风会记得这段安静而认真的时间。"

        goals_done = 0
        for info in subjects:
            sub = self.subject(info["id"])
            if sub and self._day_seconds(sub, key, now) >= info["goal_seconds"]:
                goals_done += 1

        longest = 0
        longest_name = ""
        for info in subjects:
            if info["streak"] > longest:
                longest = info["streak"]
                longest_name = info["name"]

        quote = quote or {"speaker": "Black", "text": ""}
        quote_text = str(quote.get("text", "")).strip()
        quote_speaker = str(quote.get("speaker", "Black"))
        lines = [
            f"# {d.year}年{d.month}月{d.day}日 · 修习手札",
            "",
            f"> 周{weekday} · 由 Black 自动记录于 {now.strftime('%H:%M')}",
            "",
            headline,
            "",
            "## 今日总览",
            "",
            f"- **总修习时长**：{format_duration(total)}",
            f"- **目标达成**：{goals_done} / {max(1, len(subjects))} 个方向",
            f"- **连续修习**：{longest_name or '—'} {longest} 天" if longest else "- **连续修习**：—",
            f"- **今日完成条目**：{'、'.join(study_names) if study_names else '暂无'}",
            "",
            "| 方向 | 今日 | 累计 | 连续 | 等级 | 今日目标 |",
            "|:---|--:|--:|--:|--:|--:|",
            *rows,
            "",
            "## 分项明细",
            "",
            *details,
            "## Black 的手札",
            "",
            f"> {quote_speaker}：{quote_text}" if quote_text else "> 今天也辛苦了。明天见，旅行者。",
            "",
            "---",
            "",
            "*这一页由 Black 在你本地生成。数据只留在这台电脑上。*",
            "",
            "## 旅行者手记",
            "",
            USER_NOTES_MARKER,
            "",
        ]
        return "\n".join(lines)

    def write_daily_note(self, date_key: str | None = None, quote: dict | None = None, *, now: datetime | None = None) -> Path:
        now = now or datetime.now()
        key = date_key or _today_key(now)
        path = self.journal_path(key)
        preserved = ""
        if path.exists():
            try:
                old = path.read_text(encoding="utf-8")
                if USER_NOTES_MARKER in old:
                    preserved = old.split(USER_NOTES_MARKER, 1)[1]
            except Exception:
                preserved = ""
        text = self.daily_markdown(key, quote=quote, now=now)
        if preserved.strip():
            text = text.replace(
                USER_NOTES_MARKER + "\n",
                USER_NOTES_MARKER + "\n" + preserved.lstrip("\n").rstrip() + "\n",
                1,
            )
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        return path

    def journal_dates(self) -> list[str]:
        dates = sorted(
            (p.stem for p in self.journal_dir.glob("*.md") if _parse_date(p.stem)),
            reverse=True,
        )
        today = _today_key()
        if today not in dates:
            dates.insert(0, today)
        return dates

    def journal_text(self, date_key: str) -> str:
        path = self.journal_path(date_key)
        if path.exists():
            return path.read_text(encoding="utf-8")
        return self.daily_markdown(date_key)

    # ------------------------------------------------------------------ chat
    def _load_chat(self) -> None:
        if not self.chat_path.exists():
            self.chat = []
            return
        try:
            raw = json.loads(self.chat_path.read_text(encoding="utf-8"))
            messages = raw.get("messages", []) if isinstance(raw, dict) else raw
            self.chat = [m for m in messages if isinstance(m, dict) and m.get("role") in ("user", "assistant")]
        except Exception:
            self.chat = []

    def append_chat(self, role: str, content: str) -> None:
        self.chat.append(
            {
                "role": role,
                "content": str(content)[:8000],
                "time": datetime.now().isoformat(timespec="seconds"),
            }
        )
        self.chat = self.chat[-MAX_CHAT:]
        self.chat_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.chat_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"messages": self.chat}, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.chat_path)

    def clear_chat(self) -> None:
        self.chat = []
        self.chat_path.unlink(missing_ok=True)

    # ------------------------------------------------------------------ export
    def export_backup(self) -> Path:
        backup_dir = self.config_path.parent / "backup"
        backup_dir.mkdir(parents=True, exist_ok=True)
        target = backup_dir / f"black-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        shutil.copyfile(self.config_path, target)
        return target


def data_dir() -> Path:
    return DATA_DIR
