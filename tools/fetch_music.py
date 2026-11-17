"""Download music from Bilibili / other yt-dlp sites and convert to MP3.

Examples
--------
    python tools/fetch_music.py --query "原神 钢琴" --limit 8
    python tools/fetch_music.py --query "原神 钢琴" --pick 1
    python tools/fetch_music.py --url "https://www.bilibili.com/video/BV1..."
    python tools/fetch_music.py --convert "D:\\Music\\video.mp4"

The output defaults to assets/music.  This is a personal-use local tool: no
Snapany/FreeConvert web automation, no upload of your files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black.media_import import (  # noqa: E402
    bilibili_search,
    convert_local_media,
    download_audio,
    dependencies_ready,
)


def _progress(pct: int, text: str) -> None:
    print(f"\r[{pct:3d}%] {text:<50}", end="", flush=True)
    if pct >= 100:
        print()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="Black 音乐获取与转 MP3 工具")
    parser.add_argument("--query", help="在 Bilibili 搜索关键词")
    parser.add_argument("--limit", type=int, default=10, help="搜索结果数量")
    parser.add_argument("--pick", type=int, help="下载第几条搜索结果（从 1 开始）")
    parser.add_argument("--url", help="直接视频链接（Bilibili 或其他 yt-dlp 支持的站点）")
    parser.add_argument("--convert", help="把本地 mp4/mkv/m4a 等转换为 mp3")
    parser.add_argument("--output", default=str(ROOT / "assets" / "music"), help="输出文件夹")
    parser.add_argument("--search-only", action="store_true", help="只搜索，不下载")
    args = parser.parse_args()

    ok, detail = dependencies_ready()
    if not ok:
        print(detail)
        return 1

    output = Path(args.output)
    if args.convert:
        try:
            print(f"正在转换：{args.convert}")
            path = convert_local_media(args.convert, output)
            print(f"已保存：{path}")
            return 0
        except Exception as e:
            print(f"转换失败：{e}")
            return 1

    if args.url:
        try:
            print(f"正在获取：{args.url}")
            path = download_audio(args.url, output, progress=_progress)
            print(f"\n已保存：{path}")
            return 0
        except Exception as e:
            print(f"\n失败：{e}")
            return 1

    if not args.query:
        parser.print_help()
        return 0

    try:
        results = bilibili_search(args.query, max(1, min(30, args.limit)))
    except Exception as e:
        print(f"搜索失败：{e}")
        return 1
    if not results:
        print("没有找到结果。")
        return 1
    print(f"\n搜索结果（{len(results)} 条）：")
    for i, r in enumerate(results, 1):
        print(f"  {i:2d}. {r.title}")
        print(f"      {r.author}  ·  {r.duration}  ·  {r.url}")
    if args.search_only:
        return 0
    if not args.pick:
        print("\n用 --pick N 选择一条下载，例如：python tools/fetch_music.py --query \"...\" --pick 1")
        return 0
    if not 1 <= args.pick <= len(results):
        print("--pick 超出范围。")
        return 1
    item = results[args.pick - 1]
    try:
        print(f"\n正在获取：{item.title}")
        path = download_audio(item.url, output, progress=_progress)
        print(f"\n已保存：{path}")
        return 0
    except Exception as e:
        print(f"\n失败：{e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
