# 素材说明

这个目录里的文件分为几类：

- `images/app_icon.png`、`app.ico`：由工作区补充的「小王子」插画裁切出的圆形应用图标（`tools/make_brand_icon.py`）。
- `images/brand_night.png`、`images/brand_day.png`：由工作区补充的「小王子」横屏图和「彩特琳德-卡牌」裁切出的方形品牌头像；夜晚显示黑猫，白天显示彩特琳德。`avatars/brand_*.png` 是同一张图，供悄悄话头像库使用。
- `images/elements/`：元素图标 PNG/SVG 原素材；界面中的元素徽记通过 `theme.element_pixmap()` 使用其白色 SVG 版本。
- `images/art_*.jpg`：早期工作区立绘，现保留作为兼容素材；当前沃雅妮莎的看板使用 `gallery/vody_*`。
- `images/gallery/*.jpg`：由 `tools/build_gallery.py` 批量下载、裁切并合成的 34 位原神角色官方立绘；每位角色有「全景」「全身」「横屏」三幅，加上沃雅妮莎从 `Vodyanitsa_image/` 全部导入的 15 幅（竖屏/横屏），共 117 幅。来源为 GitHub 的 [ScobbleQ/HoYo-Assets](https://github.com/ScobbleQ/HoYo-Assets) 官方美术资源镜像与 [Enka Network](https://enka.network/)；中文角色信息来自 [Project Amber](https://gi.yatta.moe/)。
- `images/gallery/thumbs/`：角色选择面板使用的 300×400 缩略图。
- `images/chevron_down.png`：界面下拉箭头，随资源脚本生成。
- `gallery.json`：角色、立绘、缩略图、横竖屏方向与来源清单。
- `images/gallery/vody_*`：由 `tools/import_vody_assets.py` 从 `Vodyanitsa_image/` 导入的 15 幅沃雅妮莎插画（7 竖屏 + 8 横屏），角色选择面板可横向滚动浏览。
- `avatars/`：Black 的头像、工作区自带 Q 版头像、从 Enka Network 下载的官方角色头像，以及派蒙弹窗用的 `paimon_official.png`、品牌头像 `brand_*.png`。角色与《原神》相关内容权利归 HoYoverse 所有。
- `fonts/Cinzel.ttf`：Google Fonts 的 Cinzel 字体，SIL Open Font License 1.1，完整许可见 `fonts/OFL.txt`。
- `music/`：`tools/prepare_assets.py` 用 numpy 生成的两首原创环境乐，可自由用于这个本地项目。
- `audio/`：同样由脚本生成的提示音与互动音效。

本应用只做本地个人学习陪伴，不分发第三方歌曲。在线寻音/视频转 MP3 得到的缓存文件位于 `cache/music/` 或本地曲库，请遵守音源平台的服务条款。
