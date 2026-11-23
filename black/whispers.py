"""Avatar choices for the customised desktop whisper.

The library is built from the local character portraits plus the two supplied
brand illustrations.  Each entry owns a speaker, so the words in the popup
change with the selected face instead of always being Paimon's.
"""
from __future__ import annotations

import random

from . import content
from .paths import AVATARS, avatar_path

_ORDER = [
    "派蒙",
    "Black",
    "小王子",
    "彩特琳德",
    "芙宁娜",
    "胡桃",
    "纳西妲",
    "雷电将军",
    "八重神子",
    "珊瑚宫心海",
    "宵宫",
    "刻晴",
    "温迪",
    "钟离",
    "可莉",
    "芭芭拉",
    "香菱",
    "凝光",
    "诺艾尔",
    "荧",
    "空",
    "菲谢尔",
    "桑多涅",
    "沃雅妮莎",
]


def _build() -> list[dict]:
    quote_speakers = {str(q.get("speaker", "")) for q in content.QUOTES}
    out: list[dict] = []
    seen: set[str] = set()
    for speaker in _ORDER + sorted(quote_speakers - set(_ORDER)):
        if speaker in seen or speaker not in quote_speakers:
            continue
        meta = content.SPEAKERS.get(speaker, {})
        filename = str(meta.get("avatar", "black.png"))
        if speaker == "派蒙":
            filename = "paimon_official.png"
        elif speaker == "小王子":
            filename = "brand_night.png"
        elif speaker == "彩特琳德":
            filename = "brand_day.png"
        path = avatar_path(filename)
        if not Path_exists(path):
            continue
        role = str(meta.get("title", "提瓦特的朋友"))
        if speaker == "派蒙":
            role = "提瓦特最好的向导"
        out.append(
            {
                "speaker": speaker,
                "name": speaker,
                "role": role,
                "color": str(meta.get("color", "#d9bc7d")),
                "avatar": filename,
                "path": path,
            }
        )
        seen.add(speaker)
    return out


def Path_exists(path) -> bool:
    try:
        return path.exists()
    except Exception:
        return False


WHISPER_AVATARS: list[dict] = _build()
_BY_SPEAKER = {item["speaker"]: item for item in WHISPER_AVATARS}
_DEFAULT = _BY_SPEAKER.get("派蒙") or (WHISPER_AVATARS[0] if WHISPER_AVATARS else None)


def get_whisper_avatar(speaker: str | None) -> dict:
    if speaker and speaker in _BY_SPEAKER:
        return _BY_SPEAKER[speaker]
    if _DEFAULT is not None:
        return _DEFAULT
    return {
        "speaker": "Black",
        "name": "Black",
        "role": "你的书桌猫",
        "color": "#d9bc7d",
        "avatar": "black.png",
        "path": AVATARS / "black.png",
    }


RANDOM_CHOICE = "随机"


def choose_whisper_avatar(speaker: str | None) -> dict:
    """Resolve the configured persona; "随机" picks a different face each call."""
    if speaker == RANDOM_CHOICE and WHISPER_AVATARS:
        return random.choice(WHISPER_AVATARS)
    return get_whisper_avatar(speaker)
