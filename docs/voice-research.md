# 原神角色语音获取可行性调研

> 调研日期：2026-11-23
> 调研对象：能否为 `assistant_Black`（Windows / Python / PyQt5 桌面学习助手）取得“原版声优配音”的原神角色语音
> 调研方式：web_search / web_fetch 查证 + 本机 HTTP 实测（curl / yt-dlp / ffprobe）
> 约束：本任务只新增本文档，不改代码、不装依赖、不把音频下载进仓库。文中所有“可下载”仅指**技术上可访问**，不代表获得授权。

---

## 一、结论摘要

1. **能拿到真正由原版声优配音的语音，但没有“官方公开的角色语音 API”。** 原神没有面向开发者的语音接口；官方只在游戏客户端、官方 wiki 和官方视频里以不同形式发布声音。
2. **最现实的三条路**：
   - **官方中文观测枢 wiki 的逐条 MP3**：每条台词一个 `<audio>`，官方 CDN 直链，带台词文本；但站点已改为 SPA、无公开 API、只覆盖中文，批量抓取要靠内部接口，脆弱。
   - **Yatta（原 Project Amber / ambr.top）的逐条 OGG**：`https://gi.yatta.moe/assets/Audio/{CHS|EN|JP|KR}/{avatarId}/{voiceFile}.ogg`，无需登录，实测 200，适合脚本；但它是第三方镜像，无授权、无文档、可能随时改。
   - **现成数据集**：Hugging Face 的 `simon3000/genshin-voice`（630,912 条 wav，75 个 parquet 合计约 335.7 GB，可按角色 ZIP 下载）、`w4123/GenshinVoice`（91,971 条，更新到 3.8，已停更）、`CSUSTers/mys-voice-genshin`（从官方 wiki 抓的 3,178 条 MP3 / 449 MB）。
3. **不建议**：
   - 用 HoneyHunterWorld 做脚本批量下载：Cloudflare 挑战，实测 403；
   - 从 B 站/YouTube 批量提取：音频混着 BGM/音效，非会员最高 135 kbps AAC（实测），版权与平台条款风险高；
   - 把音频提交进仓库或随安装包分发：已有米哈游律师函要求下架“下载库”的先例（2026-07）。
4. **合规红线**：语音的著作权/录音制品权利归米哈游（HOYOVERSE）；声优的表演者权、声音人格权另算。官方只明确“游戏内音乐限于个人非商业使用”；公开渠道能查到的主要是《原神同人周边正式运行指引 V1.3》（只管实体周边），没有查到与崩铁同级别的“原神同人衍生作品创作指引”。**本地个人使用风险相对低但仍是用户协议灰区；随开源仓库分发风险高。**
5. **给本项目的建议**：**不内置任何原神音频、不做内置下载器**；提供“用户自行导入语音包”的能力，音频只落在已被 `.gitignore` 忽略的 `data/voice/`，清单只存元数据。最小可用版本约 **6–10 小时**。

---

## 二、调研方法与限制

- 本机网络能直连：`gi.yatta.moe`、`genshin.honeyhunterworld.com`、`static.wikia.nocookie.net`、`uploadstatic.mihoyo.com`、`api.github.com`、`hf-mirror.com`、`www.bilibili.com`、`support.hoyoverse.com`。
- 本机网络**不能稳定直连**：`wiki.hoyolab.com`、`sg-wiki-api.hoyolab.com`、`huggingface.co`、`genshin-impact.fandom.com`。因此 HoYoWiki 的页面内容用搜索摘要和第三方评测交叉验证，HF 用 `hf-mirror.com` 镜像查元数据；相关结论在文中单独标注“未实测”。
- 实测记录见附录 A。文件大小、版本号、接口行为都可能变化，本文只代表 2026-11-23 的情况。
- 重要区分：**“能 HTTP 200 下载” ≠ “有版权许可”**。本文把“技术可达”和“合规可用”分开写。

---

## 三、官方渠道

### 3.1 游戏内语音包（最正统的“原版声优”来源）

原神 PC/移动端支持中、日、英、韩四种语音包，玩家可在游戏内安装/删除：

- 官方说明：[How do I manage my Voice Packs?](https://support.hoyoverse.com/hc/en-us/articles/50913742098841-How-do-I-manage-my-Voice-Packs)（2025-09 更新，明确英/日/中/韩四种、体积大、建议 Wi-Fi）。
- PC 端文件位置：`Genshin Impact game\GenshinImpact_Data\StreamingAssets\AudioAssets`，里面是 Wwise 的 `.pck` 包，不是可直接播放的 wav/ogg。移动端在 `YuanShen_Data/Persistent/AudioAssets`。
  - 参考：[dvingerh/genshin-audio-exporter README](https://github.com/dvingerh/genshin-audio-exporter)、[CosmicPredator/Resonance-Extractor](https://github.com/CosmicPredator/Resonance-Extractor)。
- 体积（Windows 压缩下载数据，7.0 版本）：中文 12.7 GiB、英文 16.5 GiB、日文 14.9 GiB、韩文 13.3 GiB；安装后通常更大（社区报告单语言约 8–20 GB）。来源：[AZA.GG 原神容量变化](https://genshin.aza.gg/db/gamesize?l=zh-cn)。
- 格式/解包：`.pck` 内的音频是 Wwise `.wem`，可用 vgmstream 播放/转换；`.pck` 可用 QuickBMS 的 wav_scanner 或 AnimeWwise 等工具拆。参考：[vgmstream issue #1470](https://github.com/vgmstream/vgmstream/issues/1470)、[Escartem/AnimeWwise](https://github.com/Escartem/AnimeWwise)（2026-10 仍在更新，Genshin 音乐名映射到 5.3）。
- **结论**：这是 100% 原版、四语言、全台词的来源；但**不是“下载即可用”**：要装 12–16 GiB、要解包、要面对版本更新；而且解包/提取很可能落入用户协议禁止的反向工程/复制条款（见第八节）。适合“用户自己已经有游戏”的本地场景，不适合做进安装包。

### 3.2 官方 wiki：中文观测枢 vs 国际 HoYoWiki

**中文观测枢（bbs.mihoyo.com / baike.mihoyo.com 的 `/ys/obc/content/{id}/detail`）**

- 角色语音页历史上把每条语音做成 HTML5 `<audio controls controlslist="nodownload"><source src="...mp3">`。证据：开源爬虫 [CSUSTers/mys-voice-genshin](https://github.com/CSUSTers/mys-voice-genshin) 的正则与成果——`res/audio` 共 **3,178 个文件、449 MB**，`res/csv` 里“话题 / 文本 / 音频 URL”三列齐全；README 明确“数据拉取自米游社-观测枢 wiki”。
- 音频直链在官方 CDN `uploadstatic.mihoyo.com/ys-obc/...mp3`，实测仍可用：例如迪奥娜“初次见面”那条
  `https://uploadstatic.mihoyo.com/ys-obc/2021/02/27/4359827/7e2e60dc2131c8647e4b201721ad9d10_7451259770016763169.mp3`
  → HTTP 200、`audio/mp3`、133,101 字节、16.58 秒、48 kHz 单声道 64 kbps（ffprobe 实测）。
- 但当前角色页（如 [芙宁娜 500291](https://baike.mihoyo.com/ys/obc/content/500291/detail?visit_device=pc&bbs_presentation_style=no_header)、[玛薇卡 503613](https://baike.mihoyo.com/ys/obc/content/503613/detail?visit_device=pc&bbs_presentation_style=no_header)）是 Nuxt SPA，直接 GET 只有 19 KB 壳；旧的内容 ID 在新 `content/info` 接口里大量返回“内容不存在”。**没有公开 API 文档**，要批量拿只能逆向内部 `content/info` 接口或解析页面数据，接口和 ID 会变。
- 芙宁娜页面的搜索摘要还写着“四国语音展示请下划浏览”，说明新角色页可能用**视频**而非逐条 MP3 展示四国语音；这一点我没有在 2026-11 逐页验证。

**国际 HoYoWiki（wiki.hoyolab.com）**

- 第三方评测（2022 年文章，2026-11 仍可访问）：Voice-Over 区“只有文本，没有附音频”（*At Voice-Over there is a text that you can hear in the game (no audio attached)*）。来源：[What is The Genshin Impact HoYoWiki?](https://expertgamereviews.com/what-is-the-genshin-impact-hoyowiki/)。
- 本机无法直连 `wiki.hoyolab.com` / `sg-wiki-api.hoyolab.com`，未能实测其当前是否新增音频。

**结论**：官方 wiki 是“官方发布、带台词、逐条可播”的最好来源，但**中文站已 SPA 化且无 API、国际站偏文本**；它能支撑“人工整理几十条”，不适合作为应用内置的稳定下载源。

### 3.3 官方 PV / 角色演示 / 原声带 / 壁纸站

- 官方角色 PV、角色演示（Character Demo）、拾枝杂谈等发布在官方频道：[YouTube @GenshinImpact](https://www.youtube.com/@GenshinImpact)、[B 站原神官方空间](https://space.bilibili.com/401742377)。这些视频里台词与 BGM、音效混在一起，**不是干净的单句语音**，只适合做“氛围音”或人工二次剪辑。
- 官方原声带（HOYO-MiX）是音乐，不含角色台词；官方壁纸/资料站没有音频下载。
- **结论**：官方视频不能替代语音包；仅用于宣传素材。

### 3.4 官方 API

- 没有找到任何“角色语音”官方 API。HoYoLAB 的公开接口主要围绕游戏记录、签到、社区内容，且多为未公开文档；官方 wiki 的 `content/info` 是内部接口，不是对外 API。
- **结论：官方 API 这条路不存在。**

---

## 四、官方素材镜像 / 数据挖掘仓库

> 这一类的共同点：**音频本身是解包产物，仓库作者没有版权，许可证只覆盖代码**；“能下载”不等于“能合法再分发”。

| 仓库/数据集 | 内容 | 体积/条数 | 格式 | 最近更新 | 许可 | 评价 |
|---|---|---|---|---|---|---|
| [simon300000/genshin-voice](https://github.com/simon300000/genshin-voice) + [HF 数据集](https://huggingface.co/datasets/simon3000/genshin-voice) | 全游戏语音 + 说话人 + 转写 + 游戏内文件名 | **630,912 条 wav**；75 个 parquet，**335.71 GB**；按角色 ZIP（如 Diona.zip 325 MB） | parquet / wav / zip | 2026-08（README 统计 2026-07-16） | **无 license**，gated=False | 最全、最新，但太大；适合按角色 ZIP 取少量 |
| [w4123/GenshinVoice](https://github.com/w4123/GenshinVoice) | 角色语音 + `result.json` 文本 | 91,971 条（第三方汇总页），更新到 3.8 | wav + json | 2023-07 | README：仅供学习，版权归米哈游 | 中文社区最知名；已停更，网盘分发 |
| [CSUSTers/mys-voice-genshin](https://github.com/CSUSTers/mys-voice-genshin) | **官方观测枢 wiki 抓取**，CSV 含话题/文本/URL | 3,178 条 / 449 MB 音频（仓库 910 MB） | mp3 + csv | 2023-02 | 代码 GPLv3；音频版权归米哈游 | 官方中文语音的现成快照，最省事；但老（约 3.5 前） |
| [Escartem/GenshinAudio](https://github.com/Escartem/GenshinAudio) | 全音频（音乐、语音、音效） | **约 16 GB**（zip 18 GB，clone 34 GB） | 未命名文件（hash） | 2025-05，已停止更新 | 无 license | 只有英文；文件名不可读，人工找台词很痛苦 |
| [AI-Hobbyist/Genshin_Datasets](https://github.com/AI-Hobbyist/Genshin_Datasets) | SVC/SVS/TTS 用角色语音包 | 6.2 版四语言 7z；仓库 122 MB | wav/7z | 2026-01 | 未写明；第三方数据集 | 按角色打包，适合 TTS；版权同样归米哈游 |
| [Sycamore0/GenshinData](https://github.com/Sycamore0/GenshinData) | 文本/配置（`FettersExcelConfigData`、`TextMap` 等） | 916 MB，7.3 万文件 | json | 2023-07，停更 | 无 license；README 有“如米哈游要求可删” | **不含音频**，但对“ID→台词”映射极有用 |
| Dimbreath/GenshinData、Dimbreath/AnimeGameData | 曾是最常用的数据仓库 | — | — | 2022 年被下架 | — | GitHub 现 404；[NGA 讨论](https://bbs.nga.cn/read.php?tid=34108256)、[Internet Archive 快照](https://archive.org/details/github.com-Dimbreath-GenshinData_-_2022-05-27_04-46-52) |
| [theBowja/GenshinData-scripts](https://github.com/theBowja/GenshinData-scripts) | 从 `ExcelBinOutput` 抽数据、`voice/audio.js` 抽语音 | 2 MB | Node 脚本 | 2026-11 | 无 license | `voice/audio.js` 依赖已 404 的 `Razmoth/Audio`，**开箱即坏** |
| [ScobbleQ/HoYo-Assets](https://github.com/ScobbleQ/HoYo-Assets) | 原神/星铁 **美术** 资源 | 538 MB | png 等 | 2026-07 | 无 license | 只有图，**没有音频**，别被名字误导 |

**解包/转换工具（只解决“怎么拆”，不解决“能不能用”）**

- [dvingerh/genshin-audio-exporter](https://github.com/dvingerh/genshin-audio-exporter)：MIT，191 stars，2023-08 停更；支持导出 wav/mp3/ogg/flac。
- [CosmicPredator/Resonance-Extractor](https://github.com/CosmicPredator/Resonance-Extractor)：GUI，2024-09，支持 `.pck`。
- [Escartem/AnimeWwise](https://github.com/Escartem/AnimeWwise)：2026-10 仍更新，能保留原始文件名/路径；Genshin 音乐名映射到 5.3，语音同理可用旧 map。
- [vgmstream](https://github.com/vgmstream/vgmstream)：播 `.wem` 的通用工具。

**命名/格式规律（解包后）**

- 游戏内语音文件名形如 `VO_friendship\VO_raidenShogun\vo_raidenEi_dialog_pendant.wem`（见 HF 数据集的 `inGameFilename` 字段），解包工具会转成 `.wav`/`.wem`；HF 那份还带 `speaker`、`transcription`、`language`，是最好用的“可读元数据”。
- Escartem 那份是 hash 文件名，无映射，基本只能按目录（`English(US)/PCK`、`External`）盲听。
- 官方 wiki 那份是 `https://uploadstatic.mihoyo.com/ys-obc/{年}/{月}/{日}/{数字}/{hash}_{id}.mp3`，文件名不可读，但 CSV 里有话题和文本。

**许可与合规风险**

- 这些仓库的“license”只覆盖脚本；音频版权归米哈游。`simon300000`、`w4123`、`Escartem` 都没有从版权方获得的再分发许可。
- 已有执法先例：`360NENZ/GI-Download-Library` 在 2026-07-30 收到上海贯道律师事务所代表米哈游的律师函，仓库代码与历史全部移除，只剩说明（[README](https://github.com/360NENZ/GI-Download-Library)）。这说明“只放下载链接/下载库”也会被发函。
- Dimbreath 的数据仓库 2022 年被下架；`Razmoth/Audio` 也已 404。**这类仓库生命周期很短，不能作为产品依赖。**

---

## 五、第三方站点

| 站点 | 直链规律 | 语言 | 格式 | 登录/反爬 | 实测 | 评价 |
|---|---|---|---|---|---|---|
| **Yatta（原 ambr.top）** | `https://gi.yatta.moe/assets/Audio/{CHS\|EN\|JP\|KR}/{avatarId}/{voiceFile}.ogg` | 中/英/日/韩（无繁体） | OGG Vorbis 48 kHz 单声道 | 无需登录；`robots.txt` 全放行；Cloudflare 但未挑战 | 200，单条 8–300 KB | **最适合脚本**；但第三方镜像、无授权、无文档 |
| **HoneyHunterWorld** | `https://genshin.honeyhunterworld.com/audio/quotes/{角色}/{id}_{cn\|jp\|en\|kr}.wav`（也有 `.ogg`） | 四语言 | wav/ogg | **Cloudflare 挑战** | `curl` 403，`Cf-Mitigated: challenge` | 浏览器能听，脚本抓不了 |
| **Fandom / Fextralife 等 wiki** | `https://static.wikia.nocookie.net/gensin-impact/images/.../VO_*.ogg` | 以英文为主 | OGG | 需带 `Referer`，否则 403 | 带 Referer 后 200，29,089 字节 | 文件多、命名可读；但英文、音质参差 |
| **Biligame 中文 wiki（大概率只有文本）** | `https://wiki.biligame.com/ys/{角色名}` 的“语音”分区 | 中文 | 未见音频直链 | 无 | 页面 200，但页面与「角色语音」页都没有 `.ogg/.mp3/.wav` 直链（实测），语音播放器由前端渲染 | 中配不建议走 Wiki，改从游戏 `*.pck` 提取 |
| **酷狗/QQ 音乐等** | 专辑《[原神]角色语音合集》 | 中/日 | 流媒体 | 需 App/登录 | — | 只能在线听，不能批量下载 |
| **ModelScope / OneDrive / 百度 AI Studio** | 数据集直链 | 多语言 | 7z/zip | 部分需登录 | 未逐一实测 | 作为数据集备选，版权同上 |

### 5.1 Yatta（重点）

- `ambr.top` 现在 302 到 `https://gi.yatta.moe`，Project Amber 已并入 Yatta。
- 实测（2026-11-23）：
  - `https://gi.yatta.moe/assets/Audio/CHS/10000032/1202.ogg` → 200，`audio/ogg`，40,360 字节（迪奥娜）；
  - `.../CHS/10000005/24001.ogg`（旅行者）→ 200，334,225 字节；
  - `.../CHS/10000115/100003.ogg`（2025 年角色 Dahlia）→ 200，12,744 字节；说明至少覆盖到 2025 年角色；
  - `CHS/EN/JP/KR` 均 200，`CHT` 404。
- 音频规格：OGG Vorbis、48 kHz、单声道、约 86–103 kbps；单条 0.5–10 秒、8–300 KB。
- **ID 映射已打通**：`voiceFile` 来自 `FettersExcelConfigData.json`（角色好感/档案语音），例如迪奥娜的 `fetterId=20013` 对应 `voiceFile=1201`、`20014→1202`；Yatta 的路径末段就是 `voiceFile`。台词文本在 `TextMap` 里用 `voiceFileTextTextMapHash` 查。也就是说：**用一份 `FettersExcelConfigData` + `TextMapCHS` 就能生成“角色 / 话题 / 文本 / 音频 URL”表**。我用 Sycamore0 的 2023 数据验证了迪奥娜的 ID 对应关系，但该数据只到 3.8，**新角色需要更新的数据包**（AI-Hobbyist 的 6.2 包或 HF 的 `result.json` 可补）。
- 限制：无官方文档、无 SLA；路径/语言代码可能变；没有繁体；站点素材的授权状态不明。`robots.txt` 允许抓取不等于版权许可。

### 5.2 HoneyHunterWorld

- 直链形如 `https://genshin.honeyhunterworld.com/audio/quotes/diona/1202_cn.wav`、`.../fischl/1203_jp.ogg`（中文 wiki 的 `<sm2>` 播放器就这么引用）。
- 实测 `curl` 返回 **403 + Cloudflare challenge**（`Cf-Mitigated: challenge`），浏览器正常。**不能作为脚本源**；手工逐条下载可行但很慢。

### 5.3 Fandom

- 角色语音页（[Voice-Over](https://genshin-impact.fandom.com/wiki/Voice-Over)）里每条台词嵌 `VO_*.ogg`；文件在 `static.wikia.nocookie.net`。
- 实测：不带 `Referer` 时 403；带 `Referer: https://genshin-impact.fandom.com/` 后 200（`VO_Cui'er_01.ogg`，29,089 字节）。
- 规模参考：[mrzjy/multimodal-genshin-impact](https://github.com/mrzjy/multimodal-genshin-impact) 从 Fandom 抓了 **152,274 个 .ogg**（含音效/语音），整包约 90 GB。说明 Fandom 的音频量很大，但英文为主、命名不统一、音质未知。
- 文本是 CC BY-SA，**音频不是**；批量转存仍有版权风险。

### 5.4 Biligame 中文 wiki（待独立验证）

- 并行调研称 `https://wiki.biligame.com/ys/%E7%90%B4` 角色页有“语音”分区、站内附件可直接访问、页面 200。
- 我本次没有独立复现（时间/网络限制），因此只把它列为“中配备选”：结构不规整、需要按页面解析、附件域名和防盗链可能变，解析成本高于 Yatta，且授权状态同样不明。

---

## 六、视频平台（B 站 / YouTube）

- B 站存在大量“角色语音合集/语音包（含下载）”视频，例如：
  - [BV1Gd4y1v7RN](https://www.bilibili.com/video/BV1Gd4y1v7RN/)（11:26，胡桃等角色语音合集）
  - [BV1kV411o7er](https://www.bilibili.com/video/BV1kV411o7er/)（多 P，钟离/公子/迪奥娜好感语音，中&日配）
- 用本机 `yt-dlp 2026.10.26` 实测 BV1Gd4y1v7RN 的音频格式：
  - `30216` m4a 34 kbps；`30232` m4a 73 kbps；`30280` m4a 135 kbps；
  - 1080P60 需要大会员/Cookies；不登录最高 135 kbps AAC。
  - 11 分钟的合集，135 kbps 约 11 MB。
- 音质与内容问题：视频里的台词通常**混着 BGM、技能音效、UI 音**，不是干净单句；同一 P 里可能有多角色；需要人工切分。用 `yt-dlp -x --audio-format mp3` 只能“把混音转成 MP3”，不能分离人声。
- YouTube 同理，官方频道与个人合集都有；国内网络通常需要代理。工具：[yt-dlp](https://github.com/yt-dlp/yt-dlp)（B 站/YouTube 都支持）。
- **结论**：适合“快速搞几条氛围语音”，不适合做“逐条角色台词库”；版权和平台条款风险高于本地解包。

---

## 七、拿不到 / 非常困难 / 高风险的清单

| 目标 | 卡在哪 | 证据 |
|---|---|---|
| 官方“角色语音”公开 API | 不存在；官方从未提供 | 官方站点/文档中无此 API；wiki 只有内部 `content/info` |
| 官方 wiki 一键批量下载 | 页面 SPA 化、无公开 API、内容 ID 变更、仅中文 | 旧 ID 在新接口返回“内容不存在”；CSUSTers 抓取基于旧 HTML |
| 国际 HoYoWiki 语音音频 | 评测称 Voice-Over 只有文本、无音频；本机无法直连验证 | [expertgamereviews](https://expertgamereviews.com/what-is-the-genshin-impact-hoyowiki/) |
| HoneyHunter 脚本下载 | Cloudflare 挑战（403） | 实测 `Cf-Mitigated: challenge` |
| Fandom 无 Referer 直链 | 403 防盗链 | 实测：无 Referer 403、带 Referer 200 |
| HF 全集 | 335.71 GB、无 license、下载成本极高 | HF API / 镜像实测 |
| 已下架的数据仓库 | Dimbreath 2022 被下架、Razmoth 404 | NGA / Archive / GitHub 404 |
| 视频提取“干净台词” | 混 BGM/音效、最高 135 kbps（非会员） | yt-dlp `-F` 实测 |
| 随仓库/安装包分发音频 | 著作权 + 律师函/DMCA | 360NENZ 2026-07 律师函；Dimbreath 下架 |
| 商用（含捐赠/付费） | 官方只允许个人非商业；声优表演者权 | 官方 FAQ + 同人周边指引 |

---

## 八、合规说明

### 8.1 权利归属

- 游戏本体、角色、台词文本、录音制品（含中/日/英/韩配音）的权利归**米哈游 / HOYOVERSE**（上海米哈游网络科技股份有限公司）。
- 声优的**表演者权**（中国《著作权法》的表演者权、录音制作者权）以及日本声优的**声音/肖像人格权**是另一层权利；即使米哈游同意，商用还可能涉及声优授权。
- 原声带（HOYO-MiX）是音乐作品，和角色台词是两套权利，不能混用。

### 8.2 官方规则（原文/官方链接）

| 文件 | 关键内容 | 对本项目意味着 |
|---|---|---|
| [Can I use in-game music for my fan-made content?](https://support.hoyoverse.com/hc/en-us/articles/50333834244633-Can-I-use-in-game-music-for-my-fan-made-content)（2025-10 更新） | “HoYoverse's in-game music is limited to personal, non-commercial use.” 并指向 [Legal FAQ](https://www.hoyolab.com/article/143107) | 官方对“游戏内声音”的口径是**个人非商业**；角色语音只会更严，不会更松 |
| [What are the guidelines for creating and selling fan-made content?](https://support.hoyoverse.com/hc/en-us/articles/51005649400729-What-are-the-guidelines-for-creating-and-selling-fan-made-content)（2025-10） | 指向 [Fan Art Special Program](https://www.hoyolab.com/article/30075725)，主要管同人图/周边售卖 | 没有授权“音频再分发” |
| [《原神》同人周边正式运行指引 V1.3](https://weibo.com/ttarticle/p/show?id=2309405154229781397777)（[B 站转载](https://www.bilibili.com/read/cv41301447)） | 审核范围是**实体周边**，明确“不含虚拟物品的制作与销售” | 不能用它给“语音包分发”背书 |
| [《崩坏：星穹铁道》同人衍生作品创作指引](https://hsr.hoyoverse.com/zh-tw/news/111203)（同类官方文件；公开渠道未查到原神对应总指引） | 使用“角色配音、角色乐曲、游戏音乐、声音样本”等素材，**仅限于个人非商业使用**，并需保留法律声明；涉及配音人员声音的另需授权 | 可视为米哈游对“角色配音”的通用态度：**个人非商业可以谈，商业/分发不行** |
| [米哈游游戏使用许可及服务协议](https://ys.mihoyo.com/main/company/terms)（官方页面，SPA；条款摘录见 [Law Insider](https://www.lawinsider.com/zh/contracts/aXH4uhMA6CA)） | 禁止“复制、翻录、反编译、反汇编、传播和陈列……图文音像资料的全部或部分内容”，禁止反向工程 | **解包提取语音本身就违反用户协议**；传播更重 |

### 8.3 执法/下架先例

- **2026-07-30**：`360NENZ/GI-Download-Library` 收到上海贯道律师事务所代表米哈游的律师函，仓库代码与历史全部删除（[README](https://github.com/360NENZ/GI-Download-Library)）。它主要是“下载库/链接库”，并非直接托管音频，仍被发函。
- **2022**：`Dimbreath/GenshinData` 被要求下架（[NGA 讨论](https://bbs.nga.cn/read.php?tid=34108256)、[Internet Archive 快照](https://archive.org/details/github.com-Dimbreath-GenshinData_-_2022-05-27_04-46-52)）。
- `Razmoth/Audio`、`Dimbreath/AnimeGameData` 现均为 404；说明这类仓库随时可能消失。

### 8.4 风险矩阵

| 使用方式 | 用户协议 | 著作权 | 被发函/下架概率 | 建议 |
|---|---|---|---|---|
| 用户本机、自己从游戏/官方 wiki 弄 10–30 条，仅自己听 | 违反（解包/复制） | 个人使用，一般不被追究 | 极低 | 可做，但别传播、别商用 |
| 应用内置“从 Yatta/官方 wiki 下载”按钮 | 违反 | 帮助他人复制/传播 | 中高 | **不建议**；至少默认关闭并声明 |
| 音频提交进公开仓库 | 违反 | 复制 + 信息网络传播 | 高 | **禁止**；`.gitignore` + 历史清理 |
| 随安装包/绿色版分发 | 违反 | 复制 + 发行 | 高 | **禁止** |
| 直播/视频二创 | 官方对“音乐”允许个人非商业 | 可能属合理使用/官方默许 | 低 | 加署名、不商用 |
| 付费/捐赠/广告变现 | 违反 | 商业使用 | 很高 | **不要** |

### 8.5 实务建议

1. **仓库里永远不出现音频**：`data/` 已被 `.gitignore` 整目录忽略；但注意 **`assets/audio/custom/` 没有被整目录忽略**（只按扩展名忽略了 mp3/ogg 等，WAV 仍可能被跟踪），不要把语音放进那里。UI 音效可以，语音不行。
2. **应用不内置任何第三方音频 URL**，也不默认开启下载；把“从哪来”交给用户。
3. 如果提供脚本，放在 `tools/` 里、由用户自己运行、默认 dry-run，并在 README 写清楚“仅限个人非商业、版权归米哈游”。
4. 应用内加一句轻量声明（设置页/关于页）：“语音包由用户自行导入，Black 不分发游戏音频；版权归 HOYOVERSE，请勿商用/传播。”
5. 如果收到 DMCA/律师函：立即下架相关音频与链接、保留代码、不争论；参考 360NENZ 的处理方式。

---

## 九、给 `assistant_Black` 的建议方案（MVP）

### 9.1 目标与非目标

- 目标：让用户**自己导入 10–30 条**喜欢的角色语音，绑定到“计时结束 / 升级 / 悄悄话 / 摸头”等事件；离线播放；可随时删除。
- 非目标：不做全量语音库、不做在线抓取、不随仓库分发、不做“原神语音大全”这种产品定位。

### 9.2 现有代码里可复用的东西（只读调研，未改动）

- `black/sounds.py`：`QSound` 播放 WAV，支持 `assets/audio/custom/` 与 `data/sounds/` 覆盖，音量走 `sound_volume`。**只适合 WAV**。
- `black/media_import.py`：`yt-dlp` + `imageio-ffmpeg` 把视频/音频转 MP3，已有 UI 线程封装；可复用来做“导入并转码”。
- `black/music_service.py`：`QMediaPlayer` 播放 MP3/OGG/FLAC 等，已有播放/暂停/错误处理；**语音播放应走它，而不是 QSound**（Windows 上 QSound 对 OGG 支持不可靠）。
- `black/pages/settings.py`：已有音量滑杆与设置持久化，可加“语音音量/启用语音”开关。
- `tools/install_genshin_sfx.py`：已有“把用户收集的音效装进 custom 目录”的先例，可照着写一个 `tools/install_voice_pack.py`（但不放进 `assets/`）。

### 9.3 数据与目录设计

```
data/voice/                     # 整个 data/ 已被 .gitignore
  my-pack/
    manifest.json
    audio/
      diona_hello.mp3
      nahida_study.mp3
```

`manifest.json` 示例（只存元数据，不存版权内容）：

```json
{
  "name": "我的原神语音",
  "language": "zh-CN",
  "note": "用户自行导入，仅本地个人使用；版权归 HOYOVERSE",
  "lines": [
    {
      "id": "diona_hello",
      "character": "迪奥娜",
      "text": "初次见面…",
      "file": "audio/diona_hello.mp3",
      "event": "timer_done",
      "volume": 0.8
    }
  ]
}
```

- `event` 可枚举：`timer_done`、`levelup`、`whisper`、`pat`、`manual`。
- 文件名校验：只允许 `audio/` 下的相对路径，防目录穿越；单文件 < 5 MB；总包 < 100 MB。
- 导入时用 `hashlib.sha1` 去重；转码统一为 MP3 128 kbps 或 WAV 44.1 kHz（体积换兼容性）。

### 9.4 播放与事件绑定

- 新增 `black/voice.py`：`VoicePack`（扫描/校验 manifest）、`VoicePlayer`（`QMediaPlayer` 单实例、播放前 stop、防重叠、失败静默）。
- 事件挂接（不改现有业务逻辑，只加信号）：
  - `timer.py` 完成时 → `voice.play("timer_done")`；
  - `levels.py` 升级时 → `levelup`；
  - `whispers.py` / `paimon_popup.py` 弹出时 → `whisper`（可选，和文字一起）。
- 设置页新增：启用语音、语音音量、导入语音包、打开语音目录、清空。默认**关闭**，第一次导入后询问是否启用。
- 播放失败（文件丢失/解码失败）只记日志，不弹窗，不影响计时。

### 9.5 合规护栏（必须写进代码/文档）

- 仓库不包含任何 `.mp3/.ogg/.wav` 语音；`data/voice/` 默认在 `.gitignore` 内。
- 应用不发网络请求下载语音；不内置 Yatta/HoneyHunter/官方 wiki 的 URL。
- 导入界面明确写：“请只导入你有权使用的音频；原神语音版权归米哈游，仅供个人非商业使用。”
- 关于页/README 增加“非官方、与米哈游无关联”的声明。
- 如果以后加“示例语音”，只用自己录的/CC0 的，不用原神原声。

### 9.6 工作量估算（小时级）

| 任务 | 估时 | 说明 |
|---|---|---|
| 目录扫描 + manifest 解析 + 校验 | 1.5–2 h | 含坏文件/缺文件处理 |
| `VoicePlayer`（QMediaPlayer、防重叠、音量） | 1.5–2 h | 复用 `music_service` 的模式 |
| 导入 UI（选文件夹/ZIP、转码、进度、去重） | 2–3 h | 复用 `media_import` 的 ffmpeg 封装 |
| 设置页开关 + 事件绑定（计时/升级/悄悄话） | 2 h | 3 个挂点 |
| 合规文案 + `.gitignore` 检查 + 测试 | 1–2 h | 含手动验收 |
| **MVP 合计** | **6–10 h** | 只做本地导入与播放 |
| 可选：官方 wiki / Yatta 抓取脚本（用户自己跑） | +6–10 h | 解析 SPA/接口、限速、重试；脆弱，不建议进主程序 |
| 可选：台词浏览器/角色筛选 | +3–4 h | 需要一份 metadata 表 |

### 9.7 最小验证步骤（不改代码也能先试）

1. 选 10 条：官方观测枢 wiki 角色页逐条播放/下载，或 Yatta 直链（如迪奥娜 `.../CHS/10000032/1201.ogg`）。
2. 用项目已有的 `imageio-ffmpeg` 转成 MP3/WAV：
   `ffmpeg -i in.ogg -ac 1 -ar 48000 -b:a 128k out.mp3`
3. 放到 `data/voice/demo/audio/`，写 `manifest.json`，把 `event` 设为 `timer_done`。
4. 先用系统播放器确认音质与台词；确认后再写 `voice.py`。
5. **不要 `git add data/`**；`data/` 已被忽略，但仍建议 `git status` 复核。

### 9.8 验收标准

- 断网状态下能播放已导入的语音；
- 连续触发 10 次计时结束，不出现重叠/爆音/卡顿；
- 删除 `data/voice/` 后应用正常启动、只提示“未导入语音”；
- `git status` 中没有任何音频文件；
- 设置页有“仅限个人非商业使用”的说明。

---

## 十、参考链接

### 官方

- [HoYoverse Help：How do I manage my Voice Packs?](https://support.hoyoverse.com/hc/en-us/articles/50913742098841-How-do-I-manage-my-Voice-Packs)
- [HoYoverse Help：Can I use in-game music for my fan-made content?](https://support.hoyoverse.com/hc/en-us/articles/50333834244633-Can-I-use-in-game-music-for-my-fan-made-content)
- [HoYoverse Help：What are the guidelines for creating and selling fan-made content?](https://support.hoyoverse.com/hc/en-us/articles/51005649400729-What-are-the-guidelines-for-creating-and-selling-fan-made-content)
- [HoYoverse Legal FAQ（HoYoLAB）](https://www.hoyolab.com/article/143107)
- [Fan Art Special Program（HoYoLAB）](https://www.hoyolab.com/article/30075725)
- [《崩坏：星穹铁道》同人衍生作品创作指引](https://hsr.hoyoverse.com/zh-tw/news/111203)
- [《原神》同人周边正式运行指引 V1.3（微博）](https://weibo.com/ttarticle/p/show?id=2309405154229781397777)
- [《原神》同人周边正式运行指引 V1.3（B 站转载）](https://www.bilibili.com/read/cv41301447)
- [《原神》官网](https://ys.mihoyo.com/)
- [《原神》官网角色页（示例）](https://ys.mihoyo.com/main/character/mondstadt)
- [《原神》用户协议入口](https://ys.mihoyo.com/main/company/terms)
- [HoYoWiki（国际）](https://wiki.hoyolab.com/pc/genshin/home)
- [中文观测枢](https://bbs.mihoyo.com/ys/obc)
- [官方 YouTube 频道](https://www.youtube.com/@GenshinImpact)
- [官方 B 站空间](https://space.bilibili.com/401742377)

### 官方 wiki 音频（示例/证据）

- [官方 CDN 上的迪奥娜“初次见面”MP3](https://uploadstatic.mihoyo.com/ys-obc/2021/02/27/4359827/7e2e60dc2131c8647e4b201721ad9d10_7451259770016763169.mp3)
- [CSUSTers/mys-voice-genshin（官方观测枢抓取，3,178 条 / 449 MB）](https://github.com/CSUSTers/mys-voice-genshin)
- [芙宁娜 观测枢页面](https://baike.mihoyo.com/ys/obc/content/500291/detail?visit_device=pc&bbs_presentation_style=no_header)
- [玛薇卡 观测枢页面](https://baike.mihoyo.com/ys/obc/content/503613/detail?visit_device=pc&bbs_presentation_style=no_header)
- [HoYoWiki 语音区“无音频”的第三方评测](https://expertgamereviews.com/what-is-the-genshin-impact-hoyowiki/)

### 数据集 / 仓库

- [simon300000/genshin-voice（GitHub）](https://github.com/simon300000/genshin-voice)
- [simon3000/genshin-voice（Hugging Face）](https://huggingface.co/datasets/simon3000/genshin-voice)
- [HF 镜像](https://hf-mirror.com/datasets/simon3000/genshin-voice)
- [w4123/GenshinVoice](https://github.com/w4123/GenshinVoice)
- [GenshinVoice 数据集汇总页](https://www.global-datasets.com/d/genshinvoice)
- [Escartem/GenshinAudio](https://github.com/Escartem/GenshinAudio)
- [AI-Hobbyist/Genshin_Datasets](https://github.com/AI-Hobbyist/Genshin_Datasets)
- [Sycamore0/GenshinData](https://github.com/Sycamore0/GenshinData)
- [theBowja/GenshinData-scripts](https://github.com/theBowja/GenshinData-scripts)
- [ScobbleQ/HoYo-Assets](https://github.com/ScobbleQ/HoYo-Assets)
- [360NENZ/GI-Download-Library（律师函说明）](https://github.com/360NENZ/GI-Download-Library)
- [Dimbreath/GenshinData 的 Internet Archive 快照](https://archive.org/details/github.com-Dimbreath-GenshinData_-_2022-05-27_04-46-52)
- [NGA：Dim 的 GitHub 数据库被要求下架](https://bbs.nga.cn/read.php?tid=34108256)
- [mrzjy/multimodal-genshin-impact（Fandom 152,274 个 ogg）](https://github.com/mrzjy/multimodal-genshin-impact)
- [andri-jpg/genshin-wiki-audio（Fandom 语音 Selenium 脚本）](https://github.com/andri-jpg/genshin-wiki-audio)

### 工具

- [dvingerh/genshin-audio-exporter](https://github.com/dvingerh/genshin-audio-exporter)
- [CosmicPredator/Resonance-Extractor](https://github.com/CosmicPredator/Resonance-Extractor)
- [Escartem/AnimeWwise](https://github.com/Escartem/AnimeWwise)
- [vgmstream issue #1470（.pck 处理）](https://github.com/vgmstream/vgmstream/issues/1470)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [AZA.GG 原神容量变化（各语言语音包体积）](https://genshin.aza.gg/db/gamesize?l=zh-cn)

### 第三方站点

- [Yatta（原 ambr）](https://gi.yatta.moe/chs)
- [Yatta 音频示例：迪奥娜 1202（CHS）](https://gi.yatta.moe/assets/Audio/CHS/10000032/1202.ogg)
- [HoneyHunterWorld 音频示例](https://genshin.honeyhunterworld.com/audio/quotes/diona/1202_cn.wav)
- [Fandom Voice-Over 页](https://genshin-impact.fandom.com/wiki/Voice-Over)
- [Fandom 音频示例（需 Referer）](https://static.wikia.nocookie.net/gensin-impact/images/f/f0/VO_Cui%27er_01.ogg)
- [Biligame 中文 wiki 角色页示例（待验证）](https://wiki.biligame.com/ys/%E7%90%B4)

### 视频

- [B 站 BV1Gd4y1v7RN](https://www.bilibili.com/video/BV1Gd4y1v7RN/)
- [B 站 BV1kV411o7er](https://www.bilibili.com/video/BV1kV411o7er/)

### 法律条文（参考）

- [《中华人民共和国著作权法》](https://www.gov.cn/guoqing/2021-10/29/content_5647633.htm)（表演者权、录音制作者权、信息网络传播权）
- [米哈游游戏使用许可及服务协议（Law Insider 摘录）](https://www.lawinsider.com/zh/contracts/aXH4uhMA6CA)

---

## 附录 A：实测记录（2026-11-23）

| # | URL / 操作 | 结果 |
|---|---|---|
| 1 | `HEAD https://genshin.honeyhunterworld.com/audio/quotes/diona/1202_cn.wav` | **403**，`Cf-Mitigated: challenge`，Cloudflare |
| 2 | `GET https://gi.yatta.moe/assets/Audio/CHS/10000032/1202.ogg` | **200**，`audio/ogg`，40,360 B |
| 3 | `GET .../CHS/10000005/24001.ogg` | **200**，334,225 B |
| 4 | `GET .../CHS/10000115/100003.ogg` | **200**，12,744 B |
| 5 | `GET .../CHT/10000115/100003.ogg` | **404** |
| 6 | `GET .../EN`、`.../JP`、`.../KR` 的 `10000115/100003.ogg` | 均 **200**（15,507 / 16,022 / 16,585 B） |
| 7 | `GET https://static.wikia.nocookie.net/.../VO_Cui%27er_01.ogg`（无 Referer） | **403**，Varnish |
| 8 | 同上（带 `Referer: https://genshin-impact.fandom.com/`） | **200**，`audio/ogg`，29,089 B |
| 9 | `GET https://uploadstatic.mihoyo.com/ys-obc/2021/02/27/4359827/7e2e...mp3` | **200**，`audio/mp3`，133,101 B |
| 10 | `ffprobe` 上一条 | 16.58 s，48 kHz，mono，64 kbps |
| 11 | `ffprobe` Yatta 10000115/100003.ogg | 0.98 s，48 kHz，mono，Vorbis 86 kbps |
| 12 | `yt-dlp -F BV1Gd4y1v7RN` | 34 / 73 / 135 kbps m4a；1080P60 需大会员 |
| 13 | `GET https://api-static.mihoyo.com/.../content/info?content_id=500291` | 200，但内容不存在（旧 ID 失效） |
| 14 | `GET https://api-static.mihoyo.com/.../content/info?content_id=7469` | 200，NPC 条目，无音频字段 |
| 15 | `GET https://gi.yatta.moe/robots.txt` | `User-agent: *` / `Disallow:`（全放行） |
| 16 | `GET https://bbs.mihoyo.com/ys/obc/content/1621/detail` | 200，19,589 B SPA 壳，无 `<audio>` |
| 17 | HF API `simon3000/genshin-voice` | 75 个 parquet，合计 **335.71 GB**；13,606 个文件；`gated=false` |
| 18 | HF `Diona.zip` HEAD | `Content-Length: 325,247,573`（约 310 MiB） |

> 说明：第 7 条“无 Referer 403”是防盗链，不代表文件不可下载；第 13/14 条说明官方 wiki 的内部接口仍在，但内容 ID 体系已变，旧抓取脚本不能直接复用。

---

## 附录 B：一句话回答“能不能拿到”

**能，拿到的都是“游戏内音频的转储或转码”，不是官方授权分发的素材。**
最省事：官方中文 wiki 的逐条 MP3（人工 10–30 条）或 Yatta 的 OGG 直链（脚本）。
最完整：HF 630,912 条 / 335.7 GB，但下载与合规成本都高。
最不该做：把音频提交进仓库、随安装包分发、或做“一键下载全角色语音”的内置功能。
