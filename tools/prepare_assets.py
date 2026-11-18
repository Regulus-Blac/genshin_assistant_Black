"""Prepare Black's local assets: art, avatars, font, icon and original ambient audio.

Run from the project root:  python tools/prepare_assets.py
Only uses files already present in the workspace plus a few publicly hosted
character icons (downloaded once, cached under assets/avatars).
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import requests
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGES = ASSETS / "images"
AVATARS = ASSETS / "avatars"
FONTS = ASSETS / "fonts"
AUDIO = ASSETS / "audio"
MUSIC = ASSETS / "music"
CACHE = ROOT / ".asset_cache"

for d in (IMAGES, AVATARS, FONTS, AUDIO, MUSIC, CACHE):
    d.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) BlackAssistant/1.0"}


def save_jpg(src: Path, dst: Path, max_w: int = 1100, quality: int = 90) -> None:
    im = Image.open(src).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(dst, quality=quality, optimize=True)
    print("art", dst.name, im.size)


def center_square(im: Image.Image, size: int = 320) -> Image.Image:
    im = im.convert("RGB")
    side = min(im.size)
    left = (im.width - side) // 2
    top = (im.height - side) // 2
    im = im.crop((left, top, left + side, top + side))
    return im.resize((size, size), Image.LANCZOS)


def prepare_art() -> None:
    arts = {
        "窗边练歌全身.jpg": "art_snow.jpg",
        "旗袍团扇.jpg": "art_wisteria.jpg",
        "饮料草地全身.jpg": "art_picnic.jpg",
        "饮料半身.jpg": "art_tea.jpg",
    }
    for src_name, dst_name in arts.items():
        src = ROOT / "Vodyanitsa_image" / src_name
        if src.exists():
            save_jpg(src, IMAGES / dst_name)

    # A face crop for Black's small avatar in dialogue / bubbles.
    snow = Image.open(ROOT / "Vodyanitsa_image" / "窗边练歌全身.jpg").convert("RGB")
    # original 822x1200; the face is roughly at x 330..690, y 60..430
    face = snow.crop((300, 35, 710, 445)).resize((320, 320), Image.LANCZOS)
    face.save(AVATARS / "black.png", optimize=True)
    print("art black avatar")

    # Local chibi portraits supplied in the workspace.
    lips = {
        "babala.jpg": "barbara.jpg",
        "feixieer.jpg": "fischl.jpg",
        "hutao.jpg": "hutao.jpg",
        "keli.jpg": "klee.jpg",
        "keqing.jpg": "keqing.jpg",
        "kong.png": "aether.png",
        "leidianjiangjun.jpg": "raiden.jpg",
        "naxida.jpg": "nahida.jpg",
        "ningguang.jpg": "ningguang.jpg",
        "nuoaier.jpg": "noelle.jpg",
        "paimeng.jpeg": "paimon.png",
        "sangduonie.jpg": "sandrone.jpg",
        "shanhu.jpg": "kokomi.jpg",
        "shenzi.jpg": "yae.jpg",
        "xiangling.jpg": "xiangling.jpg",
        "xiaogong.jpg": "yoimiya.jpg",
        "ying.jpg": "lumine.jpg",
    }
    for src_name, dst_name in lips.items():
        src = ROOT / "除了沃雅妮莎之外" / src_name
        if not src.exists():
            continue
        im = center_square(Image.open(src), 300)
        if dst_name.endswith(".png"):
            im.save(AVATARS / dst_name, optimize=True)
        else:
            im.save(AVATARS / dst_name, quality=92, optimize=True)
    print("avatars local", len(list(AVATARS.glob("*"))))

    # Official Genshin avatar icons (for characters not in the local chibi set).
    icons = {
        "Furina": "furina.png",
        "Venti": "venti.png",
        "Zhongli": "zhongli.png",
        "Nahida": "nahida_official.png",
        "Klee": "klee_official.png",
    }
    for api_name, dst_name in icons.items():
        dst = AVATARS / dst_name
        if dst.exists() and dst.stat().st_size > 2000:
            continue
        url = f"https://enka.network/ui/UI_AvatarIcon_{api_name}.png"
        try:
            r = requests.get(url, headers=UA, timeout=30)
            r.raise_for_status()
            dst.write_bytes(r.content)
            print("avatar", dst_name, len(r.content))
        except Exception as e:
            print("avatar failed", api_name, e)


def prepare_font() -> None:
    dst = FONTS / "Cinzel.ttf"
    if dst.exists() and dst.stat().st_size > 10000:
        return
    cache = CACHE / "Cinzel.ttf"
    if not cache.exists():
        url = "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cinzel/Cinzel%5Bwght%5D.ttf"
        r = requests.get(url, headers=UA, timeout=40)
        r.raise_for_status()
        cache.write_bytes(r.content)
    shutil.copyfile(cache, dst)
    license_path = FONTS / "OFL.txt"
    if not license_path.exists() or license_path.stat().st_size < 2000:
        try:
            r = requests.get(
                "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/cinzel/OFL.txt",
                headers=UA,
                timeout=30,
            )
            r.raise_for_status()
            license_path.write_text(r.text, encoding="utf-8")
        except Exception:
            license_path.write_text(
                "Cinzel is licensed under the SIL Open Font License 1.1.\n"
                "https://github.com/google/fonts/tree/main/ofl/cinzel\n",
                encoding="utf-8",
            )
    print("font", dst.name, dst.stat().st_size)


def make_chevron() -> None:
    """Small gold chevron used by QComboBox / QDateEdit."""
    S = 96
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(20, 32), (48, 62), (76, 32)], fill=(217, 188, 125, 255), width=9, joint="curve")
    im.resize((24, 24), Image.LANCZOS).save(IMAGES / "chevron_down.png")
    print("chevron")


def make_icon() -> None:
    S = 1024
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    px = np.zeros((S, S, 3), dtype=np.float32)
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    cx = cy = S / 2
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / (S * 0.5)
    for c in range(3):
        px[..., c] = np.clip(18 + (1 - dist) * 16, 0, 255)
    # teal glow at the lower left, gold warmth upper right
    px[..., 1] += np.clip((1 - np.sqrt((xx - S * 0.28) ** 2 + (yy - S * 0.72) ** 2) / (S * 0.45)) * 22, 0, 24)
    px[..., 2] += np.clip((1 - np.sqrt((xx - S * 0.3) ** 2 + (yy - S * 0.7) ** 2) / (S * 0.45)) * 30, 0, 32)
    px[..., 0] += np.clip((1 - np.sqrt((xx - S * 0.75) ** 2 + (yy - S * 0.2) ** 2) / (S * 0.5)) * 22, 0, 24)
    bg = Image.fromarray(px.astype(np.uint8), "RGB").convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((40, 40, S - 40, S - 40), fill=255)
    bg.putalpha(mask)
    im.alpha_composite(bg)

    d = ImageDraw.Draw(im, "RGBA")
    d.ellipse((42, 42, S - 42, S - 42), outline=(201, 168, 100, 255), width=6)
    d.ellipse((64, 64, S - 64, S - 64), outline=(226, 204, 150, 110), width=2)
    # four-point stars at the cardinal points
    def star(cx0, cy0, r, color):
        pts = []
        for i in range(8):
            a = -math.pi / 2 + i * math.pi / 4
            rr = r if i % 2 == 0 else r * 0.28
            pts.append((cx0 + rr * math.cos(a), cy0 + rr * math.sin(a)))
        d.polygon(pts, fill=color)

    for ang in range(0, 360, 90):
        a = math.radians(ang - 90)
        star(cx + math.cos(a) * 430, cy + math.sin(a) * 430, 22, (232, 207, 146, 230))

    # black cat silhouette
    cat = (7, 10, 15, 255)
    # ears
    d.polygon([(315, 405), (285, 205), (445, 320)], fill=cat)
    d.polygon([(709, 405), (739, 205), (579, 320)], fill=cat)
    d.polygon([(330, 390), (320, 272), (416, 340)], fill=(31, 48, 58, 255))
    d.polygon([(694, 390), (704, 272), (608, 340)], fill=(31, 48, 58, 255))
    # head
    d.ellipse((270, 300, 754, 734), fill=cat)
    # subtle inner rim
    d.arc((275, 305, 749, 729), 200, 340, fill=(77, 107, 110, 140), width=3)
    # eyes (slanted gold diamonds)
    for ex in (412, 612):
        d.polygon([(ex - 64, 512), (ex, 484), (ex + 64, 512), (ex, 540)],
                  fill=(225, 188, 103, 255))
        d.polygon([(ex - 26, 511), (ex, 500), (ex + 26, 511), (ex, 523)],
                  fill=(16, 22, 24, 255))
        d.ellipse((ex - 9, 501, ex + 9, 511), fill=(246, 230, 184, 220))
    # nose + forehead star
    d.polygon([(500, 585), (524, 585), (512, 603)], fill=(197, 158, 94, 255))
    star(512, 405, 36, (234, 210, 150, 255))
    d.arc((435, 610, 589, 680), 20, 160, fill=(188, 153, 100, 170), width=3)

    # tiny gold specks
    rng = np.random.default_rng(4)
    for _ in range(40):
        x = rng.uniform(150, 880)
        y = rng.uniform(120, 900)
        if (x - 512) ** 2 + (y - 512) ** 2 < 400 ** 2:
            continue
        r = rng.uniform(1, 3)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(230, 204, 146, int(rng.uniform(50, 160))))
    im = im.filter(ImageFilter.GaussianBlur(0.35))
    icon = im.resize((256, 256), Image.LANCZOS)
    icon.save(IMAGES / "app_icon.png")
    icon.save(ASSETS / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("icon")


# ---------------------------------------------------------------------------
# original ambient music, generated locally (no external music copyright)
# ---------------------------------------------------------------------------

SR = 32000
NOTE = {
    "D2": 73.42, "A2": 110.00, "B2": 123.47, "G2": 98.00, "F#2": 92.50,
    "D3": 146.83, "A3": 220.00, "B3": 246.94, "G3": 196.00, "F#3": 185.00,
    "D4": 293.66, "E4": 329.63, "F#4": 369.99, "A4": 440.00, "B4": 493.88,
    "D5": 587.33, "E5": 659.26, "F#5": 739.99, "A5": 880.00, "B5": 987.77,
    "D6": 1174.66,
}


def adsr(n: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    a = max(1, int(attack * SR))
    d = max(1, int(decay * SR))
    r = max(1, int(release * SR))
    s = n - a - d - r
    if s < 0:
        s = 0
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False),
        np.linspace(1, sustain, d, endpoint=False),
        np.full(s, sustain),
        np.linspace(sustain, 0, r),
    ])
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    return env[:n]


def pluck(freq: float, dur: float, amp: float = 0.12) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    env = np.exp(-t * 2.8) * (1 - np.exp(-t * 90))
    sig = np.zeros(n)
    for k, w in ((1, 1.0), (2, 0.32), (3, 0.16), (4, 0.08), (5, 0.035)):
        sig += w * np.sin(2 * np.pi * freq * k * t + 0.2 * k)
    return (sig * env * amp).astype(np.float32)


def pad_chord(freqs, dur: float, amp: float = 0.035) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    sig = np.zeros(n, dtype=np.float32)
    for i, f in enumerate(freqs):
        lfo = 0.7 + 0.3 * np.sin(2 * np.pi * (0.035 + i * 0.007) * t + i)
        for det in (-0.0022, 0.0, 0.0022):
            sig += (0.6 if det == 0 else 0.3) * np.sin(2 * np.pi * f * (1 + det) * t + i * 0.7) * lfo
    env = adsr(n, 4.0, 2.0, 0.8, 4.0)
    return sig * env * amp / max(1, len(freqs))


def reverb(sig: np.ndarray, seconds: float = 2.2, wet: float = 0.28) -> np.ndarray:
    n = int(seconds * SR)
    rng = np.random.default_rng(7)
    imp = rng.normal(0, 1, n).astype(np.float32)
    imp *= np.exp(-np.arange(n) / (SR * 0.55))
    # cheap low-pass to make the tail soft
    kernel = np.ones(28, dtype=np.float32) / 28
    imp = np.convolve(imp, kernel, mode="same")
    imp[:200] = 0
    imp /= np.max(np.abs(imp)) + 1e-9
    wet_sig = np.convolve(sig, imp, mode="full")[: len(sig)]
    wet_sig /= np.max(np.abs(wet_sig)) + 1e-9
    out = sig * (1 - wet) + wet_sig * wet * np.max(np.abs(sig)) + 1e-9
    return out


def write_wav(path: Path, data: np.ndarray) -> None:
    data = np.asarray(data, dtype=np.float32)
    peak = float(np.max(np.abs(data))) or 1.0
    data = data / peak * 0.72
    pcm = (data * 32767).clip(-32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("audio", path.name, path.stat().st_size // 1024, "KB")


def ambient_track(name: str, duration: float, chords, melody_notes, seed: int) -> None:
    n = int(duration * SR)
    mix = np.zeros(n, dtype=np.float32)
    # chord bed, 8 second blocks
    block = 8.0
    for idx, start in enumerate(np.arange(0, duration, block)):
        chord = chords[idx % len(chords)]
        seg = pad_chord([NOTE[x] for x in chord], min(block + 3.0, duration - start))
        a = int(start * SR)
        b = min(n, a + len(seg))
        mix[a:b] += seg[: b - a]
    # sparse plucked melody
    rng = np.random.default_rng(seed)
    t = 2.0
    while t < duration - 2.0:
        note = melody_notes[rng.integers(0, len(melody_notes))]
        dur = float(rng.choice([2.5, 3.2, 4.0]))
        seg = pluck(NOTE[note], dur, amp=0.085 if rng.random() > 0.3 else 0.11)
        a = int(t * SR)
        b = min(n, a + len(seg))
        mix[a:b] += seg[: b - a]
        # occasional soft high sparkle
        if rng.random() < 0.3:
            shimmer = pluck(NOTE[rng.choice(["D5", "E5", "A5", "B5"])], 2.0, amp=0.025)
            aa = min(n, a + int(1.1 * SR))
            bb = min(n, aa + len(shimmer))
            mix[aa:bb] += shimmer[: bb - aa]
        t += float(rng.choice([3.5, 4.0, 4.5, 5.5]))
    # airy noise
    noise = rng.normal(0, 1, n).astype(np.float32)
    k = np.ones(220, dtype=np.float32) / 220
    noise = np.convolve(noise, k, mode="same") * 0.008
    mix += noise
    mix = reverb(mix, 2.4, 0.25)
    # fade in/out
    fade = int(2.0 * SR)
    mix[:fade] *= np.linspace(0, 1, fade) ** 1.4
    mix[-fade:] *= np.linspace(1, 0, fade) ** 1.4
    write_wav(MUSIC / name, mix)


def sound_effects() -> None:
    def bell(freq, dur=2.8, amp=0.12):
        t = np.arange(int(dur * SR)) / SR
        env = np.exp(-t * 1.9) * (1 - np.exp(-t * 80))
        s = sum(w * np.sin(2 * np.pi * freq * k * t) for k, w in [(1, 1), (2.01, 0.35), (3.99, 0.15), (6.2, 0.06)])
        return (s * env * amp).astype(np.float32)

    chime = np.zeros(int(3.4 * SR), dtype=np.float32)
    for note, at, amp in (("D5", 0.0, 0.12), ("A5", 0.28, 0.10), ("F#5", 0.56, 0.08), ("D6", 0.9, 0.055)):
        seg = bell(NOTE[note], 2.6, amp)
        a = int(at * SR)
        b = min(len(chime), a + len(seg))
        chime[a:b] += seg[: b - a]
    chime = reverb(chime, 1.5, 0.35)
    write_wav(AUDIO / "chime.wav", chime)

    level = np.zeros(int(4.3 * SR), dtype=np.float32)
    for i, note in enumerate(["D4", "A4", "D5", "F#5", "A5", "B5", "D6"]):
        seg = bell(NOTE[note], 3.0, 0.10 - i * 0.004)
        a = int(i * 0.19 * SR)
        b = min(len(level), a + len(seg))
        level[a:b] += seg[: b - a]
    level = reverb(level, 2.0, 0.4)
    write_wav(AUDIO / "levelup.wav", level)

    t = np.arange(int(0.55 * SR)) / SR
    tap = (np.sin(2 * np.pi * NOTE["D6"] * t) * np.exp(-t * 16) * 0.08).astype(np.float32)
    write_wav(AUDIO / "interact.wav", tap)


def main() -> None:
    prepare_art()
    prepare_font()
    subprocess.run([sys.executable, str(Path(__file__).with_name("make_brand_icon.py"))], check=True)
    make_chevron()
    if not (MUSIC / "星落之庭.wav").exists():
        ambient_track(
            "星落之庭.wav", 52.0,
            chords=[["D2", "A3", "D4", "F#4"], ["A2", "E4", "A4"], ["B2", "F#4", "B4"], ["G2", "D4", "G3", "B3"]],
            melody_notes=["D4", "E4", "F#4", "A4", "B4", "D5", "E5", "F#5"],
            seed=12,
        )
    if not (MUSIC / "风起之时.wav").exists():
        ambient_track(
            "风起之时.wav", 48.0,
            chords=[["G2", "D4", "G3", "B3"], ["D2", "A3", "D4", "F#4"], ["B2", "F#4", "B4"], ["A2", "E4", "A4"]],
            melody_notes=["G3", "A4", "B4", "D5", "E5", "F#5", "A5"],
            seed=27,
        )
    if not (AUDIO / "chime.wav").exists() or not (AUDIO / "levelup.wav").exists():
        sound_effects()
    else:
        # small files should exist; generate missing ones only
        sound_effects()
    print("done")


if __name__ == "__main__":
    main()
