"""Genshin-like study levels: time and consistency both matter."""
from __future__ import annotations

import math
from dataclasses import dataclass

# Cumulative hours required for each level.  The curve starts gently and then
# grows steadily, similar to an adventure-rank style progression.
_HOURS = [
    0, 0.5, 1.5, 3, 5, 8, 12, 17, 23, 30,
    38, 47, 57, 68, 80, 95, 112, 131, 152, 175,
    200, 230, 263, 300, 340, 385, 435, 490, 550, 615,
]
MAX_LEVEL = len(_HOURS)
THRESHOLDS = [int(h * 3600) for h in _HOURS]

_TIERS = [
    (1, 4, "初识"),
    (5, 8, "勤学"),
    (9, 12, "精进"),
    (13, 16, "心流"),
    (17, 20, "通达"),
    (21, 24, "造诣"),
    (25, 27, "大师"),
    (28, 30, "传说"),
]

# Every consecutive day grants a small permanent resonance bonus.  It is capped
# so that long absences never feel punished, but consistency is still valuable.
STREAK_BONUS_SECONDS = 10 * 60
STREAK_BONUS_CAP_DAYS = 30


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    xp_seconds: int
    floor_seconds: int
    next_seconds: int | None
    progress: float
    to_next_seconds: int

    @property
    def is_max(self) -> bool:
        return self.next_seconds is None

    @property
    def label(self) -> str:
        return f"Lv.{self.level} {self.title}"


def effective_seconds(total_seconds: int, best_streak: int) -> int:
    return max(0, int(total_seconds)) + min(max(0, int(best_streak)), STREAK_BONUS_CAP_DAYS) * STREAK_BONUS_SECONDS


def level_from_seconds(xp_seconds: float) -> int:
    xp = max(0, int(xp_seconds))
    level = 1
    for idx, threshold in enumerate(THRESHOLDS):
        if xp >= threshold:
            level = idx + 1
        else:
            break
    return min(level, MAX_LEVEL)


def level_info(total_seconds: int, best_streak: int = 0) -> LevelInfo:
    xp = effective_seconds(total_seconds, best_streak)
    level = level_from_seconds(xp)
    title = "初识"
    for lo, hi, name in _TIERS:
        if lo <= level <= hi:
            title = name
            break
    if level >= MAX_LEVEL:
        return LevelInfo(level, title, xp, THRESHOLDS[-1], None, 1.0, 0)
    floor = THRESHOLDS[level - 1]
    nxt = THRESHOLDS[level]
    span = max(1, nxt - floor)
    progress = min(1.0, max(0.0, (xp - floor) / span))
    return LevelInfo(level, title, xp, floor, nxt, progress, max(0, nxt - xp))


def format_duration(seconds: float, style: str = "full") -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if style == "clock":
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    if style == "hhmm":
        return f"{h:02d}:{m:02d}"
    if h and m:
        return f"{h} 小时 {m} 分"
    if h:
        return f"{h} 小时"
    if m:
        return f"{m} 分钟"
    return f"{s} 秒"


def format_short_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, _ = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m" if m else f"{h}h"
    return f"{m}m"
