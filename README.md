# Black · 提瓦特驻留终端

<img src="docs/icon_512.png" width="88" align="right" alt="Black 的小王子图标">

Black 是一个本地优先的 Windows 桌面学习助手：用提瓦特风格的界面陪你计时、记录手札、看考试倒计时，也会在桌角偶尔说一句话。

- 修习计时、考试倒计时、60 级等级与连续修习（前期轻松，后期明显变慢）
- 每日 Markdown 手札
- 35 位角色、117 幅看板立绘，支持竖屏与横屏立绘；沃雅妮莎的 15 张资源已全部收录
- 夜晚 / 白天双主题：默认夜晚，左上角品牌头像会随主题切换为小王子 / 彩特琳德
- 乐音页分成「歌单 / 本地曲库 / 在线寻音」三页，各自拖入播放器：播放模式跟着当前列表走，自定义歌单也能顺序 / 随机 / 单曲循环
- 歌单与本地曲库都支持搜索；在线曲目可一键「下载到本地曲库」
- 导入 B 站视频时，若链接是合集（多 P / UP 主合集），会先列出来让你勾选要下载哪几段或全选
- 窗口、以及所有弹出的功能弹窗都能用鼠标拖动边缘缩放
- 可选 AI 对话；不填 API Key 时使用离线陪伴模式
- 白天模式会同时切换主界面、立绘舞台、横屏功能区、卡片和页面的底色；白天不再使用黑色立绘底板。
- UI 音效（提示、点击、确认、升级等）可替换：`data/sounds/` 里的同名 WAV 会覆盖内置音效

## 系统要求

- Windows 10/11
- Python 3.10+（开发与测试环境为 3.13）
- 需要联网才能使用在线寻音、视频转 MP3 和 AI 对话
- 中文 TTS 可选，使用 Windows 自带语音

## 安装与启动

```powershell
git clone https://github.com/Regulus-Blac/genshin_assistant_Black.git
cd genshin_assistant_Black
python -m pip install -r requirements.txt
```

安装完成后双击 `启动Black.bat`，或运行：

```powershell
python app.py
```

如果缺少依赖，也可以双击 `安装依赖.bat`。`launch_black.vbs` 是不弹出控制台的启动方式。

## 第一次使用

1. 启动后会看到「修习、手札、乐音、交谈」四个页面。
2. 点考试卡片可以改名称、日期和备注；默认的算法考试日期只是示例。
3. 点某个修习方向右侧的播放按钮开始计时，关闭窗口默认收进托盘，计时继续。
4. 左下角「角色」可以切换看板角色和立绘；「摸摸头」和「角色」之间的「横屏」按钮会切到横屏立绘，此时整个主界面从左右结构变为「上方横屏功能区 + 下方全宽页面」，横屏功能区左侧是完整宽幅立绘，右侧是播放器、三个快捷按钮和台词卡；再点「竖屏」可以切回。
5. 「乐音」页有三个标签：
   - **歌单**：上方才会出现歌单选择框和「+ 新建 / 重命名 / 删除」。歌单需要自己创建、再往里加歌；下方按钮是「排序 / 添加歌曲 / 移除歌曲」，还可以在歌单内搜索。
   - **本地曲库**：跟着音乐文件夹走，支持搜索、拖动排序；右键可以「加入歌单」或「重命名文件」。
   - **在线寻音**：网易云完整音源 + iTunes 试听，即点即听并自动缓存；选中后可以「加入歌单」或「下载到本地曲库」（下载会真正落一个 MP3 进曲库）。
6. 上方播放器的播放键、上一首/下一首和三种播放模式，作用在**当前标签页的列表**上：在歌单页按播放，队列就是这个歌单；切到本地曲库再按播放，队列换成整个曲库。播放器右侧会显示「顺序播放 · 歌单「xxx」」这样的当前队列提示。点击进度条任意位置可跳转，右侧「倍率」可选 0.5x、0.75x、1.0x、1.5x、2.0x。
7. 导航栏右侧的太阳/月亮按钮可以在夜晚和白天之间切换；也可以在「设置 → 外观」里选择。选择会保存到本地 `data/black.json`。
8. 窗口四边和四角都可以拖动调整大小，最小可缩到 **560×260**；窗口变窄时立绘舞台自动收起、修习页变单列、音乐页进入紧凑模式，内容仍可滚动。所有弹出的功能弹窗（修习方向、考试、导入音乐、选歌、合集选择等）同样可以拖动边缘或右下角缩放。
9. 「设置 → 陪伴与低语」可以选择悄悄话头像、弹出间隔，或关闭自动弹出；长台词会自动换行并增高卡片，不再截断；再听一句时卡片保持原位，不会向上跳。

## AI 对话与 API Key

不填 Key 时，Black 会使用本地规则回应。要启用 AI：

1. 打开「设置 → AI 对话」；
2. 填写兼容 OpenAI `/chat/completions` 的接口地址、模型名和**你自己的 API Key**；
3. 点「测试连接」。

API Key 只保存在本机的 `data/black.json`。这个目录已在 `.gitignore` 中排除，不会被提交或分享。**请不要把 API Key 写进 README、代码或任何提交文件。**

## 音乐导入

乐音页的「导入音乐」支持：

- 关键词搜索 B 站公开视频；
- 直接粘贴 Bilibili、YouTube 等 yt-dlp 支持的视频链接；
- 选择本地 `mp4 / mkv / m4a / wav` 转换为 MP3。

如果粘贴的链接是**合集**（B 站多 P 视频、UP 主合集，或其他站点的播放列表），会先弹出「选择要下载的片段」：默认只有少量时全选、超过 25 段时默认不选，可以逐条勾选，也可以「全选」一次性下载整部合集；进度条会显示第几首、共几首。搜索到的单个视频如果本身属于合集，同样会先让你选。

导入的 MP3 保存到当前本地曲库，默认是 `assets/music/`；可以在乐音页更换曲库目录。转换后的文件不是 MP4，原始音频/视频临时文件会在转换后删除。

也可以使用命令行：

```powershell
python tools/fetch_music.py --query "原神 钢琴" --limit 10
python tools/fetch_music.py --query "原神 钢琴" --pick 1
python tools/fetch_music.py --url "https://www.bilibili.com/video/BV..."
python tools/fetch_music.py --convert "D:\Videos\video.mp4"
```

B 站部分视频需要登录或大会员权限；下载内容请仅用于个人合法用途。

## 数据与隐私

以下内容默认不进入 Git：

- `data/`：设置、考试、聊天记录、API Key、`data/sounds/` 里的个人音效
- `journal/`：每日手札
- `cache/`、`build/`：缓存与构建产物
- `model/`、`Vodyanitsa_image/`、`除了沃雅妮莎之外/`：原始模型和素材
- `docs/screenshots/`：可能包含个人学习状态的截图
- `dsh-history/`：找回的旧对话记录
- `.mp3` 等本地音乐、日志、锁文件和密钥

`assets/audio/` 里的内置音效是原创合成或 CC0 素材，可以随仓库分发；如果你把自己收集的游戏内录音效放进 `data/sounds/`，它们不会被提交。

如果你要提交 PR，请先确认没有把 `data/`、`journal/`、API Key 或个人截图加入提交。

## 开发与 PR

```powershell
python -m pip install -r requirements.txt
python tools/test_core.py
python tools/test_flows.py
python tools/test_characters.py
python tools/test_theme.py
python tools/test_landscape.py
python tools/test_playlists.py
python tools/test_playlist_actions.py
python tools/test_local_playlist.py
python tools/test_music_v15.py
python tools/test_whisper_size.py
python tools/test_levels.py
python tools/test_responsive.py
python tools/test_resize.py
```

主要目录：

```text
app.py                 启动入口
black/                 应用源码
  mainwindow.py        主窗口
  pages/               修习、手札、乐音、交谈、设置
  theme.py             颜色、字体、图标和全局样式
  stage.py             左侧角色舞台
  paimon_popup.py      派蒙主题弹窗
assets/                图片、头像、字体、音频
tools/                 素材生成、音乐导入、测试和截图脚本
```

欢迎提交 Issue 或 PR。提交前请先跑过至少 `tools/test_core.py` 和 `tools/test_characters.py`；涉及界面的改动请附截图，但截图不要包含个人考试、手札或曲库信息。

## 素材与致谢

- 角色立绘来自 [ScobbleQ/HoYo-Assets](https://github.com/ScobbleQ/HoYo-Assets)，角色中文信息来自 [Project Amber](https://gi.yatta.moe/)，仅供个人本地使用。
- 元素徽记使用工作区 `assets/images/elements/` 中提供的图标；左上角品牌头像使用工作区补充的「小王子」与「彩特琳德-卡牌」素材，夜晚显示黑猫，白天显示彩特琳德。
- 派蒙头像来自 [Enka Network](https://enka.network/) 的公开静态资源。
- 内置 UI 音效：`chime / levelup / interact / click / confirm / open / cancel` 由脚本合成（原创，可自由使用），`error.wav` 来自 [Kenney UI Audio](https://kenney.nl/assets/ui-audio)（CC0）。想换成其他音效时，把同名 WAV 放进 `data/sounds/` 即可，见 `tools/install_genshin_sfx.py`。
- 字体 Cinzel 来自 Google Fonts，遵循 SIL Open Font License，见 `assets/fonts/OFL.txt`。
- 《原神》及相关角色、图片权利归 HoYoverse 所有；本项目与米哈游/HoYoverse 无关联。游戏内录音效不随仓库分发。

本项目用于个人本地学习陪伴，不包含、不分发第三方歌曲。
