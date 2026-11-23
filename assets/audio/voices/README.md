# 角色语音（随仓库分发）

这里放的是悄悄话会播放的角色语音。目录结构：

```text
assets/audio/voices/
├── index.json          # 每句话的文本、话题与原始来源 URL
├── 琴/line01.mp3 ...   # 每个角色若干条
├── 钟离/line01.mp3 ...
└── README.md
```

## 来源与用途

- 台词与音频来自《原神》官方观测枢 wiki 的角色语音页，经公开数据集
  [CSUSTers/mys-voice-genshin](https://github.com/CSUSTers/mys-voice-genshin) 整理，
  每条都能在 `index.json` 里找到原文与原始 CDN 地址。
- 本项目是**非商业的个人学习工具**，这些音频只用于本机悄悄话播放，不做销售、不做二次分发平台。
- 《原神》角色语音的著作权与录音制品权利归米哈游 / HOYOVERSE，角色配音的表演者权归各位声优。
  如果权利方认为这里的收录不合适，请提 Issue，我会立即移除对应文件。
- 只想用自己录音的话，把文件放到 `data/voice/<角色>/` 即可：用户目录优先于这里，
  而且 `data/` 不进 git（见 README「角色语音」）。

## 重新获取

```powershell
python tools/fetch_voices.py --list
python tools/fetch_voices.py --all --limit 5
```

脚本会按同样的目录结构覆盖更新本目录；`--limit` 控制每个角色保留几条。
