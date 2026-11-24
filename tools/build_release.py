"""Build a self-contained Windows package for a GitHub release.

Usage
-----
    python tools/build_release.py            # build + zip
    python tools/build_release.py --no-zip   # only the folder

The build is done from a clean staging copy of the *committed* tree
(``git archive HEAD``), so personal files such as ``data/``, ``journal/`` or the
local music library never end up in the archive.  Outputs go to ``dist/``:

    dist/Black-<version>-Windows-x64/        (folder, double-click Black.exe)
    dist/Black-<version>-Windows-x64.zip     (to attach to the GitHub release)
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black import __version__  # noqa: E402

DIST = ROOT / "dist"
STAGE = ROOT / "build" / "release-src"
WORK = ROOT / "build" / "pyinstaller"
NAME = "Black"
BUNDLE = f"{NAME}-{__version__}-Windows-x64"
SPEC_ENTRY = "app.py"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def stage_tree() -> Path:
    """Extract only the committed files into build/release-src."""
    if STAGE.exists():
        shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True)
    tar_path = STAGE.parent / "release-src.tar"
    run(["git", "archive", "--format=tar", "-o", str(tar_path), "HEAD"])
    with tarfile.open(tar_path) as tar:
        tar.extractall(STAGE)
    tar_path.unlink(missing_ok=True)
    print("staged", sum(1 for _ in STAGE.rglob("*")), "entries")
    return STAGE


def write_version_file(target: Path) -> None:
    parts = (__version__.split(".") + ["0", "0", "0"])[:4]
    nums = ", ".join(str(int(p)) if p.isdigit() else "0" for p in parts)
    target.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({nums}), prodvers=({nums}), mask=0x3f, flags=0x0,
                    OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'Regulus-Blac'),
        StringStruct('FileDescription', 'Black · 提瓦特驻留终端'),
        StringStruct('FileVersion', '{__version__}'),
        StringStruct('InternalName', 'Black'),
        StringStruct('OriginalFilename', 'Black.exe'),
        StringStruct('ProductName', 'Black'),
        StringStruct('ProductVersion', '{__version__}'),
        StringStruct('LegalCopyright', 'Non-commercial personal project')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )


def build(stage: Path) -> Path:
    version_file = WORK / "version_info.txt"
    WORK.mkdir(parents=True, exist_ok=True)
    write_version_file(version_file)
    out = DIST / BUNDLE
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    DIST.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--noupx",
        "--name",
        NAME,
        "--icon",
        str(ROOT / "assets" / "app.ico"),
        "--version-file",
        str(version_file),
        "--distpath",
        str(DIST),
        "--workpath",
        str(WORK / "work"),
        "--specpath",
        str(WORK),
        "--add-data",
        f"{stage / 'assets'};assets",
        "--collect-submodules",
        "yt_dlp",
        "--collect-data",
        "imageio_ffmpeg",
        "--collect-binaries",
        "imageio_ffmpeg",
        "--collect-data",
        "certifi",
        "--exclude-module",
        "tkinter",
        "--exclude-module",
        "matplotlib",
        SPEC_ENTRY,
    ]
    run(cmd, cwd=stage)
    return out


def add_readme(out: Path) -> None:
    """Ship a short Chinese quick-start next to the exe."""
    text = f"""Black · 提瓦特驻留终端 {__version__}
=====================================

一、怎么用
1. 双击 Black.exe 即可启动，不需要安装 Python。
2. 第一次启动会在同目录生成 data/、journal/、cache/ 三个文件夹，请放在有写入权限的位置。
3. 如果 Windows 提示“已保护你的电脑”：点“更多信息 → 仍要运行”。这是没有代码签名证书时的正常提示。

二、数据在哪
- data/      设置、考试、聊天记录、API Key、语音与立绘
- journal/   每日手札（Markdown）
- cache/     在线音乐试听缓存
整个文件夹拷走就等于搬家，删除即彻底清除。

三、自己的语音与立绘（可选）
- 语音：data/voice/<角色名>/*.mp3；同名会覆盖内置语音。
- 立绘：data/art_extra/<角色 id>/ 放图片，并在 data/art_extra/manifest.json 登记
  （详细格式见 README 的「补充立绘」）。

四、常见问题
- 打不开：检查是否被杀毒软件拦截；也可以把整个文件夹放到 D: 盘再试。
- 没有声音：设置 → 音效音量、乐音页的音乐音量分别调整。
- 在线功能（B 站下载、AI 对话）需要联网。

五、版权
角色图片、语音版权归 HoYoverse 及各原作者，本项目为非商业个人学习工具。
"""
    (out / "使用说明.txt").write_text(text, encoding="utf-8")


def make_zip(out: Path) -> Path:
    zip_path = DIST / f"{BUNDLE}.zip"
    if zip_path.exists():
        zip_path.unlink()
    print("zipping", zip_path.name)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for item in sorted(out.rglob("*")):
            if item.is_file():
                zf.write(item, Path(BUNDLE) / item.relative_to(out))
    return zip_path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="构建 Windows 免安装版")
    parser.add_argument("--no-zip", action="store_true", help="只生成文件夹")
    args = parser.parse_args()

    stage = stage_tree()
    out = build(stage)
    add_readme(out)
    print("built", out)
    total = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    print(f"folder size {total / 1024 / 1024:.1f} MB")
    if args.no_zip:
        return 0
    zip_path = make_zip(out)
    size = zip_path.stat().st_size / 1024 / 1024
    print(f"zip {zip_path} ({size:.1f} MB)")
    print("sha256", sha256(zip_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
