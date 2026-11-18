"""Character voices, contextual whispers and the offline fallback chat."""
from __future__ import annotations

import hashlib
import random
import re
from datetime import datetime

SPEAKERS: dict[str, dict] = {
    "Black": {"avatar": "black.png", "color": "#d9bc7d", "title": "夜之眷属 · 你的书桌猫"},
    "温迪": {"avatar": "venti.png", "color": "#7fd8c8", "title": "风色诗人"},
    "钟离": {"avatar": "zhongli.png", "color": "#d8b26a", "title": "往生堂客卿"},
    "纳西妲": {"avatar": "nahida_official.png", "color": "#9fd08a", "title": "小吉祥草王"},
    "胡桃": {"avatar": "hutao.jpg", "color": "#e58b70", "title": "往生堂第七十七代堂主"},
    "可莉": {"avatar": "klee_official.png", "color": "#ef9c82", "title": "火花骑士"},
    "刻晴": {"avatar": "keqing.jpg", "color": "#b79bea", "title": "玉衡星"},
    "芙宁娜": {"avatar": "furina.png", "color": "#79c7eb", "title": "众水、众方、众民与众律法的女王"},
    "雷电将军": {"avatar": "raiden.jpg", "color": "#b9a4ea", "title": "一心净土"},
    "八重神子": {"avatar": "yae.jpg", "color": "#e7a0b8", "title": "鸣神大社宫司"},
    "珊瑚宫心海": {"avatar": "kokomi.jpg", "color": "#93cbdf", "title": "现人神巫女"},
    "宵宫": {"avatar": "yoimiya.jpg", "color": "#efb174", "title": "夏祭的女王"},
    "芭芭拉": {"avatar": "barbara.jpg", "color": "#8bc6ed", "title": "闪耀偶像"},
    "派蒙": {"avatar": "paimon.png", "color": "#e8ddbd", "title": "最好的向导"},
    "香菱": {"avatar": "xiangling.jpg", "color": "#e9a37c", "title": "万民百味"},
    "凝光": {"avatar": "ningguang.jpg", "color": "#e4c68b", "title": "天权星"},
    "诺艾尔": {"avatar": "noelle.jpg", "color": "#d8c4b2", "title": "未授勋的女仆"},
    "荧": {"avatar": "lumine.jpg", "color": "#e6d49b", "title": "旅行者"},
    "空": {"avatar": "aether.png", "color": "#e6d49b", "title": "旅行者"},
    "菲谢尔": {"avatar": "fischl.jpg", "color": "#b799da", "title": "断罪皇女"},
    "桑多涅": {"avatar": "sandrone.jpg", "color": "#c7b5ce", "title": "木偶"},
    "沃雅妮莎": {"avatar": "black.png", "color": "#7fd3d1", "title": "潮声中的歌者"},
    "小王子": {"avatar": "brand_night.png", "color": "#d9bc7d", "title": "猫尾酒馆的黑色小王子"},
    "彩特琳德": {"avatar": "brand_day.png", "color": "#b9c7e8", "title": "白鸦的旅人"},
}

# (speaker, text, tags)
QUOTES: list[dict] = [
    {"speaker": "Black", "tags": ["focus", "default"], "text": "书桌这一小块地方，今天也归我守着了。你只管往前走，我替你看着时间。"},
    {"speaker": "Black", "tags": ["focus"], "text": "别急着追赶谁。把眼前这一页弄懂，就已经比刚才的你更强一点了。"},
    {"speaker": "Black", "tags": ["cute"], "text": "喵。不是催你，只是尾巴不小心扫到计时按钮了。真的。"},
    {"speaker": "Black", "tags": ["rest"], "text": "眼睛离开屏幕二十秒，看看窗外。提瓦特的风也会路过你的窗台。"},
    {"speaker": "Black", "tags": ["night"], "text": "夜已经很深了。真正厉害的人，也懂得在该收工的时候收工。"},
    {"speaker": "Black", "tags": ["exam"], "text": "考试只是把你会的东西换一种方式写出来。别把它想成一头会喷火的龙。"},
    {"speaker": "Black", "tags": ["courage"], "text": "你已经坐到书桌前了。最难的这一步，其实已经完成了。"},
    {"speaker": "Black", "tags": ["cute", "default"], "text": "如果今天也能认真一会儿，我就在你的冒险记录上盖一个金色的小爪印。"},
    {"speaker": "温迪", "tags": ["rest", "focus"], "text": "风带来故事的种子，时间使之发芽。你现在的每一分钟，也正在长成未来的样子。"},
    {"speaker": "温迪", "tags": ["courage"], "text": "别怕走调。风从不要求每一片叶子唱同一个音。"},
    {"speaker": "钟离", "tags": ["focus"], "text": "凡事皆有代价。既然选择了这段时间，便让它落地生根，别叫它白白流走。"},
    {"speaker": "钟离", "tags": ["exam"], "text": "临阵磨枪并非无用，只是枪杆须得平日里握稳。今天练的，都是明日的底气。"},
    {"speaker": "纳西妲", "tags": ["focus", "default"], "text": "知识不是背在身上的重量，而是让你看见更多世界的窗。慢慢推开它就好。"},
    {"speaker": "纳西妲", "tags": ["rest"], "text": "做不完的事情可以分很多次完成。树也不是一天就长到云里的。"},
    {"speaker": "胡桃", "tags": ["cute"], "text": "偶尔发会儿呆也没关系，本堂主替你保密——不过计时器可不会保密哦。"},
    {"speaker": "胡桃", "tags": ["focus"], "text": "今日事今日毕，明日还有明日的热闹。先把这一页收进兜里吧。"},
    {"speaker": "可莉", "tags": ["cute", "courage"], "text": "可莉也觉得你超厉害的！认真起来的样子，像蹦蹦炸弹一样闪闪发光！"},
    {"speaker": "可莉", "tags": ["rest"], "text": "休息的时候可以吃一块蛋糕吗？可莉觉得可以。琴团长不在，悄悄地。"},
    {"speaker": "刻晴", "tags": ["focus"], "text": "效率不是把自己逼到喘不过气，而是知道下一步该做什么。列出三件事，然后开始。"},
    {"speaker": "刻晴", "tags": ["exam"], "text": "把错题当成敌人留下的破绽。看穿一次，下一次就不会再被它骗到。"},
    {"speaker": "芙宁娜", "tags": ["courage", "default"], "text": "主角登场前也会紧张。但帷幕拉开的那一刻，所有的练习都会成为你的光。"},
    {"speaker": "芙宁娜", "tags": ["cute"], "text": "今天的掌声先欠着。等你完成这一轮，我再隆重地为你鼓一次掌！"},
    {"speaker": "雷电将军", "tags": ["focus"], "text": "永恒并非停滞，而是无数个当下被认真对待之后，留下的形状。"},
    {"speaker": "八重神子", "tags": ["cute", "focus"], "text": "哎呀，偷懒的小狐狸被我看见了。再写十分钟，就放你去喝茶。"},
    {"speaker": "八重神子", "tags": ["rest"], "text": "书读累了就来陪我坐一会儿。点心我带了，故事也带了，只差一个听众。"},
    {"speaker": "珊瑚宫心海", "tags": ["focus"], "text": "先把任务拆成能完成的小块。再复杂的战局，也要一子一子地落下。"},
    {"speaker": "珊瑚宫心海", "tags": ["rest"], "text": "记得补水。长时间专注之后，身体也需要被好好照看。"},
    {"speaker": "宵宫", "tags": ["courage", "cute"], "text": "把今天的不开心写下来，折成烟花放掉。明天要用亮晶晶的心情出发呀！"},
    {"speaker": "芭芭拉", "tags": ["courage"], "text": "为努力到现在的你献上一首歌——不用很完美，只要是你自己的节奏。"},
    {"speaker": "派蒙", "tags": ["cute", "rest"], "text": "再坚持一下下！等结束了，我们去吃好吃的。派蒙请客……呃，下次一定。"},
    {"speaker": "香菱", "tags": ["rest"], "text": "学习像做菜，火候太急会糊，太小又不熟。找到自己的火候最要紧。"},
    {"speaker": "凝光", "tags": ["exam", "focus"], "text": "时间是最昂贵的筹码。把它押在真正重要的地方，回报才配得上你的野心。"},
    {"speaker": "诺艾尔", "tags": ["courage"], "text": "今天也辛苦了。即使只完成了一点点，也请允许我为你感到骄傲。"},
    {"speaker": "荧", "tags": ["focus"], "text": "旅途的意义，不只在终点。你走过的每一步，都会在某个地方留下光。"},
    {"speaker": "空", "tags": ["focus"], "text": "不必一次走完全部地图。先点亮最近的那座七天神像吧。"},
    {"speaker": "菲谢尔", "tags": ["cute"], "text": "断罪之皇女命令你：喝一口水，伸一个懒腰，然后继续。这是契约。"},
    {"speaker": "桑多涅", "tags": ["focus"], "text": "精密的东西都需要校准。你的专注力也一样，累了就重新调一次弦。"},
    {"speaker": "沃雅妮莎", "tags": ["courage", "default"], "text": "潮声会记得每一次歌唱。哪怕今天只有很轻的一句，也已经落进海里了。"},
    {"speaker": "Black", "tags": ["focus"], "text": "计时开始之后，世界会安静一点。那些没想通的事，也会慢慢露出线头。"},
    {"speaker": "Black", "tags": ["rest"], "text": "去接杯水吧。我会把刚才那页书压在爪子底下，不让它跑掉。"},
    {"speaker": "Black", "tags": ["exam"], "text": "把大目标拆成今天的三道题。考场上没有巨龙，只有一道一道你练过的小关卡。"},
    {"speaker": "Black", "tags": ["night"], "text": "凌晨的灯很漂亮，但明天清醒的脑子更漂亮。收工吧，旅行者。"},
    {"speaker": "Black", "tags": ["cute"], "text": "你摸鱼的时候，我的耳朵会动。别问我为什么，猫的直觉。"},
    {"speaker": "钟离", "tags": ["rest"], "text": "弦绷得太紧，便听不出曲子的余韵。歇一歇，再启程。"},
    {"speaker": "纳西妲", "tags": ["courage"], "text": "你不需要成为最聪明的那个人。你只需要比昨天多懂一点点。"},
    {"speaker": "温迪", "tags": ["night"], "text": "把今天的疲惫交给夜风吧。明早醒来，我们再去追新的蒲公英。"},
    {"speaker": "芙宁娜", "tags": ["exam"], "text": "考试是舞台，不是审判。把你练过的那一段，优雅地演完就好。"},
    {"speaker": "胡桃", "tags": ["night"], "text": "还不睡？再熬下去，明天见到的本堂主可就要打哈欠啦。"},
    {"speaker": "刻晴", "tags": ["rest"], "text": "休息不是偷懒，是为了让下一段时间真正属于你。"},
    {"speaker": "小王子", "tags": ["cute", "default"], "text": "猫尾酒馆今天也很安静。我把最靠窗的位置留给你了，书翻到哪一页了？"},
    {"speaker": "小王子", "tags": ["focus"], "text": "杯子里的酒会见底，专注的时间不会。再坐一会儿吧，我陪你。"},
    {"speaker": "小王子", "tags": ["night"], "text": "夜里的猫不催人。困了就收工，明天再把没做完的事叼回来。"},
    {"speaker": "彩特琳德", "tags": ["courage", "default"], "text": "白鸦会替旅人记住方向。别怕走慢，只要还在往前。"},
    {"speaker": "彩特琳德", "tags": ["focus"], "text": "桌前的灯已经替你亮着了。先把这一页看完，再想下一段路。"},
    {"speaker": "彩特琳德", "tags": ["rest"], "text": "风从窗外经过时，不妨抬头看一眼。休息也是旅途的一部分。"},
]

TAG_LABELS = {
    "focus": "专注",
    "rest": "休憩",
    "exam": "备考",
    "night": "夜色",
    "cute": "小互动",
    "courage": "勇气",
    "default": "陪伴",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _exam_days(context: dict | None) -> list[dict]:
    if not context:
        return []
    return [e for e in context.get("exams", []) if e.get("days") is not None]


def pick_quote(
    *,
    context: dict | None = None,
    tags: list[str] | None = None,
    exclude: set[str] | None = None,
    rng: random.Random | None = None,
    speaker: str | None = None,
) -> dict:
    """Pick a quote appropriate for the current moment.

    Context supports ``active`` (bool), ``late`` (bool), ``today_seconds`` and
    ``exams`` (each with ``name`` and ``days``).  When ``speaker`` is given,
    prefer that character's own lines (used by the whisper-avatar setting).
    """
    rng = rng or random.Random()
    exclude = exclude or set()
    source_pool = [q for q in QUOTES if not speaker or q["speaker"] == speaker]
    if not source_pool:
        source_pool = list(QUOTES)
    now_tags = list(tags or [])
    if context:
        if context.get("late"):
            now_tags.append("night")
        if context.get("active") and context.get("today_seconds", 0) >= 100 * 60:
            now_tags.append("rest")
        if any(0 <= e.get("days", 999) <= 10 for e in _exam_days(context)):
            now_tags.append("exam")
        if not now_tags:
            now_tags.append("default")
    if not now_tags:
        now_tags = ["default", "focus"]

    pool = [q for q in source_pool if any(t in q["tags"] for t in now_tags) and q["text"] not in exclude]
    if not pool:
        pool = [q for q in source_pool if q["text"] not in exclude] or source_pool

    # Exam proximity deserves a tailored line every now and then.
    if context and "exam" in now_tags and rng.random() < 0.45 and not speaker:
        exams = sorted(_exam_days(context), key=lambda x: x["days"])
        if exams:
            e = exams[0]
            days = int(e["days"])
            if days == 0:
                text = f"今天是{e['name']}的日子。深呼吸，检查文具和证件。你已经准备了这么久，现在只需要把会的东西写下来。"
            elif days <= 3:
                text = f"距离{e['name']}只剩 {days} 天了。别开新坑，翻错题、早点睡，让状态站在你这边。"
            else:
                text = f"距离{e['name']}还有 {days} 天。今天不需要惊天动地，只要比昨天多弄懂一道题。"
            return {"speaker": "Black", "tags": ["exam"], "text": text}

    return rng.choice(pool)


def daily_quote(date_key: str) -> dict:
    seed = int(hashlib.sha1(("black-" + date_key).encode("utf-8")).hexdigest()[:12], 16)
    rng = random.Random(seed)
    pool = [q for q in QUOTES if "default" in q["tags"] or "focus" in q["tags"]]
    return rng.choice(pool)


def greeting(now: datetime | None = None, name: str = "旅行者") -> str:
    now = now or datetime.now()
    h = now.hour
    if h < 5:
        return f"夜还很深，{name}。"
    if h < 9:
        return f"早上好，{name}。"
    if h < 12:
        return f"上午好，{name}。"
    if h < 14:
        return f"午安，{name}。"
    if h < 18:
        return f"下午好，{name}。"
    if h < 23:
        return f"晚上好，{name}。"
    return f"夜深了，{name}。"


def greeting_sub(now: datetime | None = None, active: bool = False) -> str:
    now = now or datetime.now()
    if active:
        return "我正在替你看着计时。专心走你的路，别回头。"
    if now.hour < 5:
        return "提瓦特的星星还亮着。写完这一点，就去睡吧。"
    if now.hour < 11:
        return "先把最重要的一件事做好，今天就会轻很多。"
    if now.hour < 14:
        return "吃饱、喝足，再慢慢开始。不急这一小会儿。"
    if now.hour < 18:
        return "午后容易走神。要不要先从最简单的十分钟开始？"
    if now.hour < 23:
        return "今晚的风很适合读书。挑一件，按开始就好。"
    return "该收尾了。把今天留在手札里，明天再继续。"


def format_countdown_line(exams: list[dict]) -> str:
    live = [e for e in exams if e.get("days") is not None]
    if not live:
        return "考试日期还没有设定。点开考试卡片，把目标写下来吧。"
    live.sort(key=lambda x: x["days"])
    e = live[0]
    days = int(e["days"])
    if days == 0:
        return f"{e['name']}就在今天。稳住，你可以的。"
    if days < 0:
        return "所有考试都已结束。要不要给自己倒一杯庆祝的茶？"
    return f"最近的一场是{e['name']}，还有 {days} 天。"


def offline_reply(text: str, context: dict | None = None) -> str:
    """A warm, rule-based reply when no API key is configured."""
    text = _clean(text).lower()
    context = context or {}
    exams = context.get("exams", [])
    today = context.get("today_text", "0 分钟")
    active = context.get("active_name")

    if any(k in text for k in ("你是谁", "名字", "black")):
        return "我是 Black，一只住在你书桌边的黑猫。平时替你看时间、记手札，偶尔借提瓦特朋友们的嘴说几句鼓励的话。"
    if any(k in text for k in ("累", "困", "难受", "焦虑", "摆烂", "不想学")):
        return "那就先不要逼自己。离开椅子，喝口水，走两分钟。回来之后只学十分钟也可以——我陪你数着。"
    if any(k in text for k in ("考试", "六级", "算法", "复习", "准备")):
        line = format_countdown_line(exams)
        return f"{line} 今天你已经投入 {today}。别一次想完整本书，先挑一个最薄弱的点，把它磨亮。"
    if any(k in text for k in ("开始", "学习", "专注", "计时")):
        if active:
            return f"你正在修习「{active}」。我这边计时没有停，先专心把这一段走完吧。"
        return "那就点一下卡片上的开始键。我会把这段时间记进手札，也会在合适的时候提醒你休息。"
    if any(k in text for k in ("音乐", "歌", "bgm", "听歌")):
        return "去「乐音」页吧。本地曲库里有两首我写的环境乐，也可以联网找歌。别让选歌比学习还久哦。"
    if any(k in text for k in ("手札", "记录", "总结")):
        return "每天的学习会自动写成一页手札，点左边的「手札」就能看到。计时暂停和退出时，我也会补写。"
    if any(k in text for k in ("谢谢", "爱你", "喜欢")):
        return "哼，猫可不是那么好哄的。……不过，尾巴尖轻轻摇了一下，就当没看见吧。"
    if any(k in text for k in ("你好", "在吗", "hi", "hello", "嗨")):
        return f"{greeting(name=context.get('name', '旅行者'))} 我在。{format_countdown_line(exams)} 要我陪你开始一段专注吗？"
    if any(k in text for k in ("加油", "鼓励", "安慰")):
        q = pick_quote(context=context)
        return f"{q['speaker']}：{q['text']}"

    q = pick_quote(context=context)
    return (
        "我听见了。现在还没有接入 AI，所以只能用自己的方式回答你——"
        f"但这句话我想认真说：{q['text']} 如果愿意，也可以去设置里填一个兼容 OpenAI 的接口，我就能陪你聊得更远。"
    )
