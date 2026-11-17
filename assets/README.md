# 素材说明

这个目录里的文件分为几类：

- `images/app_icon.png`、`app.ico`：`tools/make_icon.py` 重新绘制的「小王子」黑猫图标（猫尾酒馆的黑猫）。
- `images/art_*.jpg`：从工作区 `Vodyanitsa_image/` 中挑选并压缩的立绘，供左侧「今日看板」使用。
- `images/gallery/*.jpg`：由 `tools/build_gallery.py` 批量下载、裁切并合成的 34 位原神角色官方立绘；每位角色有「全景」「全身」两幅，加上沃雅妮莎的 4 幅，共 72 幅。来源为 GitHub 的 [ScobbleQ/HoYo-Assets](https://github.com/ScobbleQ/HoYo-Assets) 官方美术资源镜像与 [Enka Network](https://enka.network/)；中文角色信息来自 [Project Amber](https://gi.yatta.moe/)。
- `images/gallery/thumbs/`：角色选择面板使用的 300×400 缩略图。
- `images/chevron_down.png`：界面下拉箭头，随资源脚本生成。
- `gallery.json`：角色、立绘、缩略图路径与来源清单。
- `avatars/`：Black 的头像、工作区自带 Q 版头像、从 Enka Network 下载的官方角色头像，以及派蒙弹窗用的 `paimon_official.png`。角色与《原神》相关内容权利归 HoYoverse 所有。
- `fonts/Cinzel.ttf`：Google Fonts 的 Cinzel 字体，SIL Open Font License 1.1，完整许可见 `fonts/OFL.txt`。
- `music/`：`tools/prepare_assets.py` 用 numpy 生成的两首原创环境乐，可自由用于这个本地项目。
- `audio/`：同样由脚本生成的提示音与互动音效。

本应用只做本地个人学习陪伴，不分发第三方歌曲。在线寻音/视频转 MP3 得到的缓存文件位于 `cache/music/` 或本地曲库，请遵守音源平台的服务条款。
