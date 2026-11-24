# 如何发布一个 Release（含免安装包）

本文记录 Black 的发版流程，方便以后自己或别人接手时照做。

## 一、准备免安装包

```powershell
python -m pip install pyinstaller
python tools/build_release.py
```

脚本会：

1. 用 `git archive HEAD` 把**已提交**的文件取到 `build/release-src/`（不会带上 `data/`、`journal/`、本地曲库）；
2. 在该副本里用 PyInstaller 打成 `dist/Black-<版本>-Windows-x64/`，入口是 `app.py`，图标取 `assets/app.ico`；
3. 生成 `使用说明.txt`；
4. 压成 `dist/Black-<版本>-Windows-x64.zip`，并打印大小与 sha256。

构建产物约 200MB（压缩后 ~90MB），主要来自 PyQt5 运行时和 56 位角色的立绘。

## 二、提交并打标签

```powershell
git add -A
git commit -m "v1.8.0 打包：支持免安装版"
git tag -a v1.8.0 -m "Black 1.8.0"
git push origin main --tags
```

> 如果直连 GitHub 超时，本机有代理时可用：
> `git -c http.proxy=http://127.0.0.1:7897 push origin main --tags`

## 三、创建 Release

### 方式 A：网页

1. 打开仓库 → Releases → **Draft a new release**；
2. Choose a tag 选 `v1.8.0`，标题填 `Black v1.8.0 · 提瓦特驻留终端`；
3. 描述直接粘贴 `docs/release-v1.8.0.md` 的内容；
4. 把 `dist/Black-1.8.0-Windows-x64.zip` 拖进附件区；
5. 勾选 **Set as the latest release**，点 Publish release。

### 方式 B：GitHub CLI

```powershell
gh release create v1.8.0 "dist/Black-1.8.0-Windows-x64.zip" `
  --title "Black v1.8.0 · 提瓦特驻留终端" `
  --notes-file docs/release-v1.8.0.md `
  --latest
```

### 方式 C：API（没有 gh 时）

```powershell
$token = "ghp_xxx"   # 只需要 repo 权限
$body = @{
  tag_name = "v1.8.0"
  name     = "Black v1.8.0 · 提瓦特驻留终端"
  body     = (Get-Content docs/release-v1.8.0.md -Raw)
  draft    = $false
  prerelease = $false
} | ConvertTo-Json -Depth 4

$release = Invoke-RestMethod -Method Post `
  -Uri "https://api.github.com/repos/Regulus-Blac/genshin_assistant_Black/releases" `
  -Headers @{ Authorization = "token $token"; "User-Agent" = "Black" } `
  -ContentType "application/json" -Body $body

# 上传附件（注意用的是 uploads.github.com）
Invoke-RestMethod -Method Post `
  -Uri "https://uploads.github.com/repos/Regulus-Blac/genshin_assistant_Black/releases/$($release.id)/assets?name=Black-1.8.0-Windows-x64.zip" `
  -Headers @{ Authorization = "token $token"; "User-Agent" = "Black"; "Content-Type" = "application/zip" } `
  -InFile "dist/Black-1.8.0-Windows-x64.zip"
```

## 四、打不开 GitHub 的人怎么用

Release 页面本身在 github.com 上，直接分享 `releases/latest` 链接对无法访问 GitHub 的人无效。可选做法：

1. 把 zip 传到国内网盘（蓝奏云、百度网盘等），在 README 或群公告里给网盘链接；
2. 用 Cloudflare R2 / 阿里云 OSS 之类的对象存储放一份，配一个自己的短链；
3. 有条件的话给仓库做个国内镜像（Gitee 等），把 Release 附件也放一份。

无论哪种方式，都建议附上 sha256，方便对方校验下载是否完整：

```powershell
Get-FileHash dist\Black-1.8.0-Windows-x64.zip -Algorithm SHA256
```

## 五、版本号从哪来

- 代码里的版本：`black/__init__.py` 的 `__version__`；
- 打包脚本、文件名、窗口标题都读这个值，发版前只改这一处；
- 发布后再改 `__version__` 为下一个版本，避免两个版本共用一个号。
