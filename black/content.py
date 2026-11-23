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
    # 1.7.2: 蒙德与璃月的老朋友
    "琴": {"avatar": "jean.png", "color": "#82d6c6", "title": "蒲公英骑士"},
    "迪卢克": {"avatar": "diluc.png", "color": "#ec9b7b", "title": "晨曦的暗面"},
    "安柏": {"avatar": "amber.png", "color": "#ec9b7b", "title": "飞行冠军"},
    "丽莎": {"avatar": "lisa.png", "color": "#bda0e8", "title": "蔷薇魔女"},
    "凯亚": {"avatar": "kaeya.png", "color": "#a9dfe8", "title": "寒风剑士"},
    "香菱": {"avatar": "xiangling.png", "color": "#ec9b7b", "title": "万民百味"},
    "北斗": {"avatar": "beidou.png", "color": "#bda0e8", "title": "无冕的龙王"},
    "凝光": {"avatar": "ningguang.png", "color": "#e0bd78", "title": "掩月天权"},
    "诺艾尔": {"avatar": "noelle.png", "color": "#e0bd78", "title": "未授勋之花"},
    "班尼特": {"avatar": "bennett.png", "color": "#ec9b7b", "title": "命运试金石"},
    "重云": {"avatar": "chongyun.png", "color": "#a9dfe8", "title": "雪融有踪"},
    "行秋": {"avatar": "xingqiu.png", "color": "#72cfe4", "title": "少年春衫薄"},
    "雷泽": {"avatar": "razor.png", "color": "#bda0e8", "title": "狼少年"},
    "迪奥娜": {"avatar": "diona.png", "color": "#a9dfe8", "title": "猫尾特调"},
    "砂糖": {"avatar": "sucrose.png", "color": "#82d6c6", "title": "无害甜度"},
    "七七": {"avatar": "qiqi.png", "color": "#a9dfe8", "title": "冻冻回魂夜"},
    "神里绫人": {"avatar": "ayato.png", "color": "#72cfe4", "title": "磐祭叶守"},
    "云堇": {"avatar": "yunjin.png", "color": "#e0bd78", "title": "红毹婵娟"},
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
    # 1.7.2: 扩充的悄悄话语料（蒙德 / 璃月的老朋友）
    {"speaker": "琴", "tags": ["focus"], "text": "先把今天要做的事写下来，一件一件划掉。秩序会让心也安静下来。"},
    {"speaker": "琴", "tags": ["exam"], "text": "临考前最怕自乱阵脚。把会做的稳稳拿下，剩下的再慢慢想。"},
    {"speaker": "琴", "tags": ["rest"], "text": "休息也是骑士团的规定。站起来活动一下，我替你看着时间。"},
    {"speaker": "迪卢克", "tags": ["focus"], "text": "安静下来做事，比任何豪言都可靠。剩下的交给时间。"},
    {"speaker": "迪卢克", "tags": ["night"], "text": "夜还长，但不必把自己熬成一盏快燃尽的灯。做完这一段就去睡。"},
    {"speaker": "迪卢克", "tags": ["courage"], "text": "你不需要向谁证明什么。把手里这件事做好，就已经足够了。"},
    {"speaker": "安柏", "tags": ["courage"], "text": "别怕摔倒！我第一次滑翔也摔进了灌木丛，站起来就又是新的开始。"},
    {"speaker": "安柏", "tags": ["focus"], "text": "先定一个小目标，比如十分钟？十分钟之后我给你鼓掌！"},
    {"speaker": "安柏", "tags": ["cute"], "text": "兔兔伯爵说它也要陪你一起。累了就靠一会儿，它不介意的。"},
    {"speaker": "丽莎", "tags": ["rest"], "text": "看书三十分钟就该让眼睛放个假，不然连字都会开始跳舞哦。"},
    {"speaker": "丽莎", "tags": ["focus"], "text": "与其一遍遍抄，不如先弄懂它为什么这样。找到钥匙，门自己就开了。"},
    {"speaker": "丽莎", "tags": ["cute"], "text": "哎呀，偷偷懒的小可爱。再坚持一页，姐姐就给你泡杯茶。"},
    {"speaker": "芭芭拉", "tags": ["courage"], "text": "为你唱一首小小的加油歌！你一定可以的，我保证！"},
    {"speaker": "芭芭拉", "tags": ["rest"], "text": "唱完这首就去喝水、伸个懒腰吧，嗓子和我都心疼你。"},
    {"speaker": "芭芭拉", "tags": ["focus"], "text": "把手机关掉一会儿，让世界安静几十分钟，专心其实也很舒服。"},
    {"speaker": "凯亚", "tags": ["focus"], "text": "计划不必完美，能执行的那一版才叫计划。"},
    {"speaker": "凯亚", "tags": ["exam"], "text": "考试考的不只是知识，还有你临场那一口气。稳住，你比你以为的更从容。"},
    {"speaker": "凯亚", "tags": ["night"], "text": "夜深了还亮着灯？别把自己当成不需要休息的人。"},
    {"speaker": "香菱", "tags": ["cute"], "text": "香喷喷的灵感来啦！不过先把这一页做完，锅热了才好吃嘛。"},
    {"speaker": "香菱", "tags": ["focus"], "text": "做菜要按顺序来，学习也一样。一步一步，火候到了自然香。"},
    {"speaker": "香菱", "tags": ["rest"], "text": "饿着肚子可不行。去吃点东西，回来我们继续。"},
    {"speaker": "北斗", "tags": ["courage"], "text": "风浪再大也是往前开。你只管掌好舵，剩下的交给船长我。"},
    {"speaker": "北斗", "tags": ["focus"], "text": "一口气干完最难的活，剩下的就不算什么了。干一杯，开工！"},
    {"speaker": "北斗", "tags": ["rest"], "text": "船上也讲究歇班。该睡就睡，明天才有力气。"},
    {"speaker": "凝光", "tags": ["focus"], "text": "把时间花在能留下痕迹的地方，这笔账我替你算得清。"},
    {"speaker": "凝光", "tags": ["exam"], "text": "应试也是一门生意。看清规则，再用最少的力气拿到你想要的。"},
    {"speaker": "凝光", "tags": ["courage"], "text": "你手里握着的，远比你想象的多。别急着看轻自己。"},
    {"speaker": "诺艾尔", "tags": ["focus"], "text": "把桌面收拾干净，心也会跟着整齐起来。需要我上去接住你吗？"},
    {"speaker": "诺艾尔", "tags": ["rest"], "text": "骑士也要按时休息的。你不说，我也会提醒你。"},
    {"speaker": "诺艾尔", "tags": ["courage"], "text": "再试一次吧。这一次不行，还有下一次，我会陪着你。"},
    {"speaker": "菲谢尔", "tags": ["cute"], "text": "本皇女准许你歇息片刻。你已足够勇敢，无需再向任何人证明。"},
    {"speaker": "菲谢尔", "tags": ["focus"], "text": "凡人的专注，亦有雷霆之威。若肯一意，便无坚不摧。"},
    {"speaker": "菲谢尔", "tags": ["exam"], "text": "区区试炼，何以畏之？吾与你同在，斩开它便是。"},
    {"speaker": "班尼特", "tags": ["courage"], "text": "今天运气不好也没关系！我这人运气一直烂，可还是能往前走。"},
    {"speaker": "班尼特", "tags": ["focus"], "text": "先把最想做的那件事做了，剩下的就顺起来了，相信我！"},
    {"speaker": "班尼特", "tags": ["cute"], "text": "冒险书上都是失败记录，可最后那几页我还没写呢。你也是。"},
    {"speaker": "重云", "tags": ["focus"], "text": "心静下来，气就顺了。别急，先深呼吸三次再开始。"},
    {"speaker": "重云", "tags": ["rest"], "text": "该冷的时候要冷，该休息的时候也别硬撑。"},
    {"speaker": "重云", "tags": ["exam"], "text": "考试像驱邪一样，胆气一乱就弱了。稳住心神，一点点来。"},
    {"speaker": "行秋", "tags": ["focus"], "text": "读书写字都讲究一个定力。把这页读完，我陪你品一壶茶。"},
    {"speaker": "行秋", "tags": ["courage"], "text": "行侠仗义不一定要有神力，肯把眼前的小事做到底，已经是了。"},
    {"speaker": "行秋", "tags": ["rest"], "text": "劳逸相济才是长久之计。今日到此也可，明日再续。"},
    {"speaker": "雷泽", "tags": ["cute"], "text": "我……陪你。一起，做事。"},
    {"speaker": "雷泽", "tags": ["courage"], "text": "狼不怕黑。你也不怕。"},
    {"speaker": "雷泽", "tags": ["focus"], "text": "一个一个来。做完了，就去吃。"},
    {"speaker": "迪奥娜", "tags": ["cute"], "text": "哼，才不是特意来陪你的！……不过，要是累了，我就借你靠一下。"},
    {"speaker": "迪奥娜", "tags": ["focus"], "text": "把最讨厌的那科先解决掉，剩下的都会变可爱。"},
    {"speaker": "迪奥娜", "tags": ["rest"], "text": "别一直盯着屏幕，眼睛会坏掉的！我……我是为了我自己才提醒你的。"},
    {"speaker": "砂糖", "tags": ["focus"], "text": "先做一个最小可行的尝试，失败了也能从中学到东西。"},
    {"speaker": "砂糖", "tags": ["cute"], "text": "我记录了很多次失败，可它们都通向答案。你也一样。"},
    {"speaker": "砂糖", "tags": ["rest"], "text": "累了就先停一下。我在旁边整理笔记，不会打扰你。"},
    {"speaker": "七七", "tags": ["cute"], "text": "七七……记得你。也记得你要休息。"},
    {"speaker": "七七", "tags": ["focus"], "text": "一步一步。做完了，七七给你记在本子上。"},
    {"speaker": "七七", "tags": ["rest"], "text": "困了……就睡。七七也会困。"},
    {"speaker": "神里绫人", "tags": ["focus"], "text": "无论局势如何，先做好眼下该做的那一件。"},
    {"speaker": "神里绫人", "tags": ["exam"], "text": "不必试图掌握全部，把关键的几步走稳就够了。"},
    {"speaker": "神里绫人", "tags": ["rest"], "text": "茶已经沏好。休息不是浪费，是为了让下一步更清楚。"},
    {"speaker": "云堇", "tags": ["focus"], "text": "唱腔讲究气息，做事讲究节奏。别急，跟着自己的板眼走。"},
    {"speaker": "云堇", "tags": ["courage"], "text": "台上一分钟，台下十年功。你今天的练习，都算数。"},
    {"speaker": "云堇", "tags": ["rest"], "text": "幕间休息也是最要紧的一部分。喝口水，听听风。"},
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
