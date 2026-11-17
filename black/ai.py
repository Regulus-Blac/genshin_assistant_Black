from __future__ import annotations

import requests
from PyQt5.QtCore import QThread, pyqtSignal

from . import content as content_mod


def normalize_endpoint(base: str) -> str:
    base = (base or "").strip().rstrip("/")
    if not base:
        return "https://api.deepseek.com/chat/completions"
    if base.endswith("/chat/completions"):
        return base
    return base + "/chat/completions"


def build_system_prompt(context: dict) -> str:
    exams = context.get("exams", [])
    exam_bits = "；".join(
        f"{e.get('name')} {e.get('label')}" for e in exams if e.get("days") is not None
    ) or "考试日期尚未设定"
    active = context.get("active_name")
    status = f"正在修习「{active}」" if active else "当前待机"
    today = context.get("today_text", "0 分钟")
    return (
        "你是 Black，一只住在提瓦特书桌边的黑猫，也是旅行者的学习陪伴助手。"
        "你嘴硬心软、温柔但不腻，偶尔借用原神角色们的意象，但不要冒充游戏角色。"
        "你说话简洁自然，中文为主，一般 1~3 句，最多 120 字；不要使用大量网络热梗，不要每句都带喵。"
        "你的任务是陪伴、鼓励、帮助拆解学习任务，并在对方疲惫时建议休息。"
        f"当前信息：{status}；今日修习 {today}；{exam_bits}。"
        "不要编造用户没有告诉你的个人经历。若被问到无法确认的游戏设定，坦白说不确定。"
        "回复不要使用 Markdown 表格，尽量用短句。"
    )


class ChatWorker(QThread):
    ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, base_url: str, api_key: str, model: str, messages: list[dict], parent=None) -> None:
        super().__init__(parent)
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.messages = messages

    def run(self) -> None:
        if not self.api_key.strip():
            self.failed.emit("还没有填写 API Key。")
            return
        try:
            r = requests.post(
                normalize_endpoint(self.base_url),
                headers={
                    "Authorization": f"Bearer {self.api_key.strip()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model or "deepseek-flash",
                    "messages": self.messages,
                    "temperature": 0.8,
                    "max_tokens": 700,
                    "stream": False,
                },
                timeout=(12, 75),
            )
            if r.status_code in (401, 403):
                self.failed.emit("API Key 被拒绝或没有权限，请到设置里检查。")
                return
            if r.status_code == 429:
                self.failed.emit("接口请求太频繁或额度不足，稍后再试。")
                return
            if not r.ok:
                detail = ""
                try:
                    data = r.json()
                    detail = str(data.get("error", {}).get("message", ""))[:180]
                except Exception:
                    detail = r.text[:180]
                self.failed.emit(f"接口返回 {r.status_code}：{detail or '未知错误'}")
                return
            data = r.json()
            choices = data.get("choices") or []
            if not choices:
                self.failed.emit("接口没有返回可用的回复。")
                return
            message = choices[0].get("message") or {}
            reply = str(message.get("content") or "").strip()
            if not reply:
                self.failed.emit("接口返回了空回复。")
                return
            self.ok.emit(reply)
        except requests.Timeout:
            self.failed.emit("接口响应超时。可以稍后重试，或先和离线模式里的我说话。")
        except requests.ConnectionError:
            self.failed.emit("连接不上接口。检查网络、Base URL，或先使用离线陪伴。")
        except Exception as e:
            self.failed.emit(f"对话失败：{type(e).__name__} · {str(e)[:140]}")


def offline_reply_for(text: str, context: dict) -> str:
    return content_mod.offline_reply(text, context)
