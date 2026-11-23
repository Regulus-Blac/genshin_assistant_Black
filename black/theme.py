"""Visual language for Black: midnight ink, pale gold and Teyvat glass."""
from __future__ import annotations

import re
from pathlib import Path

from PyQt5.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtWidgets import QApplication, QWidget

from .paths import FONTS, IMAGES

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------
_DARK = {
    "INK": "#070b11",
    "BG": "#0a1019",
    "BG2": "#0e1722",
    "PANEL": "#121c28",
    "PANEL2": "#172333",
    "PANEL3": "#1c2a3b",
    "GOLD": "#d9bc7d",
    "GOLD_BRIGHT": "#f3ddaa",
    "GOLD_SOFT": "#a98e5c",
    "GOLD_DARK": "#6f5a36",
    "TEXT": "#eee7da",
    "TEXT_SOFT": "#d7cdbb",
    "MUTED": "#a89d8b",
    "FAINT": "#6f746f",
    "TEAL": "#72d3ce",
    "HYDRO": "#6fc7e8",
    "GREEN": "#9aca84",
    "PURPLE": "#bda0e8",
    "ROSE": "#e39a91",
    "RED": "#d87373",
    "WHITE": "#fbf7ee",
}

# A warm, sunlit atelier.  Gold becomes a little deeper so it remains legible
# on parchment; the character stage and Paimon popup intentionally stay as
# dark "night glass" islands, which keeps the portraits dramatic in daylight.
_LIGHT = {
    "INK": "#f8f2e6",
    "BG": "#f0e8d9",
    "BG2": "#e8ddca",
    "PANEL": "#fcf7ed",
    "PANEL2": "#f4ecde",
    "PANEL3": "#eadfca",
    "GOLD": "#987536",
    "GOLD_BRIGHT": "#b1873e",
    "GOLD_SOFT": "#80612b",
    "GOLD_DARK": "#c9b58d",
    "TEXT": "#352c20",
    "TEXT_SOFT": "#4a3d2d",
    "MUTED": "#5b4d3a",
    "FAINT": "#786853",
    "TEAL": "#2f817d",
    "HYDRO": "#2d7f9f",
    "GREEN": "#5f8f4e",
    "PURPLE": "#7658a8",
    "ROSE": "#b05d59",
    "RED": "#b24c4c",
    "WHITE": "#fffaf0",
}

MODE = "dark"
INK = _DARK["INK"]
BG = _DARK["BG"]
BG2 = _DARK["BG2"]
PANEL = _DARK["PANEL"]
PANEL2 = _DARK["PANEL2"]
PANEL3 = _DARK["PANEL3"]
GOLD = _DARK["GOLD"]
GOLD_BRIGHT = _DARK["GOLD_BRIGHT"]
GOLD_SOFT = _DARK["GOLD_SOFT"]
GOLD_DARK = _DARK["GOLD_DARK"]
TEXT = _DARK["TEXT"]
TEXT_SOFT = _DARK["TEXT_SOFT"]
MUTED = _DARK["MUTED"]
FAINT = _DARK["FAINT"]
TEAL = _DARK["TEAL"]
HYDRO = _DARK["HYDRO"]
GREEN = _DARK["GREEN"]
PURPLE = _DARK["PURPLE"]
ROSE = _DARK["ROSE"]
RED = _DARK["RED"]
WHITE = _DARK["WHITE"]


def normalize_mode(mode: str | None) -> str:
    return "light" if str(mode or "").lower() in ("light", "day", "白", "白天") else "dark"


def set_mode(mode: str | None) -> str:
    """Switch the palette used by new widgets and all custom painters."""
    global MODE, INK, BG, BG2, PANEL, PANEL2, PANEL3
    global GOLD, GOLD_BRIGHT, GOLD_SOFT, GOLD_DARK
    global TEXT, TEXT_SOFT, MUTED, FAINT
    global TEAL, HYDRO, GREEN, PURPLE, ROSE, RED, WHITE
    MODE = normalize_mode(mode)
    palette = _LIGHT if MODE == "light" else _DARK
    for key, value in palette.items():
        globals()[key] = value
    return MODE


def is_light() -> bool:
    return MODE == "light"


def mode_label() -> str:
    return "白天" if MODE == "light" else "夜晚"


SERIF = "Noto Serif SC"
SANS = "Noto Sans SC"
MONO = "Cascadia Mono"
DISPLAY = "Cinzel"

ELEMENTS = {
    "dendro": {"label": "草", "color": "#96cc8e", "dark": "#3f6547"},
    "hydro": {"label": "水", "color": "#72cfe4", "dark": "#315e72"},
    "electro": {"label": "雷", "color": "#bda0e8", "dark": "#53416f"},
    "anemo": {"label": "风", "color": "#82d6c6", "dark": "#38665e"},
    "geo": {"label": "岩", "color": "#e0bd78", "dark": "#6d5732"},
    "pyro": {"label": "火", "color": "#ec9b7b", "dark": "#733f32"},
    "cryo": {"label": "冰", "color": "#a9dfe8", "dark": "#456b73"},
    "default": {"label": "星", "color": "#d9bc7d", "dark": "#65512f"},
}


def element_color(name: str) -> str:
    return ELEMENTS.get(name, ELEMENTS["default"])["color"]


def qcolor(value: str, alpha: int | None = None) -> QColor:
    c = QColor(value)
    if alpha is not None:
        c.setAlpha(alpha)
    return c


def mix(c1: str | QColor, c2: str | QColor, t: float) -> QColor:
    a = QColor(c1) if isinstance(c1, str) else c1
    b = QColor(c2) if isinstance(c2, str) else c2
    t = max(0.0, min(1.0, t))
    return QColor(
        round(a.red() + (b.red() - a.red()) * t),
        round(a.green() + (b.green() - a.green()) * t),
        round(a.blue() + (b.blue() - a.blue()) * t),
        round(a.alpha() + (b.alpha() - a.alpha()) * t),
    )


def init_fonts() -> None:
    path = FONTS / "Cinzel.ttf"
    if path.exists():
        QFontDatabase.addApplicationFont(str(path))


def font(size: int, family: str = SANS, weight: int = 400, letter_spacing: float = 0) -> QFont:
    f = QFont(family, -1, weight)
    f.setPixelSize(size)
    if letter_spacing:
        f.setLetterSpacing(QFont.AbsoluteSpacing, letter_spacing)
    return f


def set_prop(widget: QWidget, name: str, value) -> None:
    widget.setProperty(name, value)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
    widget.update()


# ---------------------------------------------------------------------------
# line icons
# ---------------------------------------------------------------------------
_ICONS = {
    "close": '<path d="M6 6 L18 18 M18 6 L6 18"/>',
    "minus": '<path d="M6 12 H18"/>',
    "maximize": '<rect x="5" y="5" width="14" height="14" rx="1"/>',
    "restore": '<rect x="8" y="8" width="11" height="11" rx="1"/><path d="M8 5 H19 V16"/>',
    "pin": '<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3z"/><path d="M12 14v6"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "play": '<path d="M8 4.8 19 12 8 19.2Z" fill="{c}" stroke="none"/>',
    "pause": '<rect x="6.7" y="5" width="3.4" height="14" rx="1" fill="{c}" stroke="none"/><rect x="13.9" y="5" width="3.4" height="14" rx="1" fill="{c}" stroke="none"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "more": '<circle cx="5" cy="12" r="1.4" fill="{c}" stroke="none"/><circle cx="12" cy="12" r="1.4" fill="{c}" stroke="none"/><circle cx="19" cy="12" r="1.4" fill="{c}" stroke="none"/>',
    "edit": '<path d="M14.5 4.5 19.5 9.5 8 21H3v-5z"/><path d="M12.5 6.5 17.5 11.5"/>',
    "trash": '<path d="M4 7h16M9 7V4h6v3M6.5 7l1 14h9l1-14M10 11v6M14 11v6"/>',
    "chevron-left": '<path d="M14.5 5 7.5 12l7 7"/>',
    "chevron-right": '<path d="M9.5 5l7 7-7 7"/>',
    "chevron-down": '<path d="M5 9l7 7 7-7"/>',
    "music": '<path d="M9 18V6l10-2v12"/><circle cx="6" cy="18" r="3"/><circle cx="16" cy="16" r="3"/>',
    "book": '<path d="M4 5.5c3-1.5 5.5-1 8 1.2v13c-2.5-2.2-5-2.7-8-1.2zM20 5.5c-3-1.5-5.5-1-8 1.2v13c2.5-2.2 5-2.7 8-1.2z"/>',
    "chat": '<path d="M4 5h16v11H9l-5 4z"/><path d="M8 9h8M8 12h5"/>',
    "sparkle": '<path d="M12 2.8l1.8 6.4L20 12l-6.2 2.8L12 21.2l-1.8-6.4L4 12l6.2-2.8z"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.2"/><path d="M15.3 15.3 21 21"/>',
    "refresh": '<path d="M20 8.5A8.2 8.2 0 1 0 20 15"/><path d="M20 3v5.5h-5.5"/>',
    "folder": '<path d="M3 6.5h7l2 2h9v11H3z"/><path d="M3 10.5h18"/>',
    "send": '<path d="M3 11.5 21 4l-7 17-3-7z"/><path d="M11 14l10-10"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5.2l3.4 2"/>',
    "volume": '<path d="M4 9.5h4L13 5v14l-5-4.5H4z"/><path d="M16 9a4 4 0 0 1 0 6M18.5 6.5a7.5 7.5 0 0 1 0 11"/>',
    "mute": '<path d="M4 9.5h4L13 5v14l-5-4.5H4z"/><path d="M16.5 9.5l5 5M21.5 9.5l-5 5"/>',
    "next": '<path d="M5 5l9 7-9 7zM18 5v14"/>',
    "prev": '<path d="M19 5l-9 7 9 7zM6 5v14"/>',
    "heart": '<path d="M12 20s-8-4.7-8-10.3C4 6.8 6.2 5 8.6 5c1.6 0 2.8.8 3.4 1.7C12.6 5.8 13.8 5 15.4 5 17.8 5 20 6.8 20 9.7 20 15.3 12 20 12 20z"/>',
    "cup": '<path d="M5 8h11v6a5 5 0 0 1-5 5H10a5 5 0 0 1-5-5z"/><path d="M16 9h2.5a2.5 2.5 0 0 1 0 5H16M7 3.5c0 1.5 1 1.5 1 3M11 3.5c0 1.5 1 1.5 1 3"/>',
    "shuffle": '<path d="M3 6h4l10 12h4M3 18h4L17 6h4"/><path d="M18 3l3 3-3 3M18 15l3 3-3 3"/>',
    "repeat": '<path d="M5 7h13l-3-3M19 17H6l3 3"/><path d="M18 7a3 3 0 0 1 0 5M6 17a3 3 0 0 1 0-5"/>',
    "repeat-one": '<path d="M5 7h13l-3-3M19 17H6l3 3"/><path d="M18 7a3 3 0 0 1 0 5M11 11v5M10 12l1-1"/>',
    "order": '<path d="M4 6h16M4 12h11M4 18h16"/><path d="M17 10l3 2-3 2"/>',
    "check": '<path d="M4.5 12.5 9.5 17.5 20 6.5"/>',
    "arrow-up-right": '<path d="M6 18 18 6M8 6h10v10"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.6 0 2-1.2 1.2-2.2-.9-1.1 0-2.8 1.5-2.8H17A4 4 0 0 0 21 12c0-5-4-9-9-9z"/><circle cx="8" cy="10" r="1" fill="{c}" stroke="none"/><circle cx="11" cy="7" r="1" fill="{c}" stroke="none"/><circle cx="15" cy="8" r="1" fill="{c}" stroke="none"/><circle cx="7" cy="14" r="1" fill="{c}" stroke="none"/>',
    "landscape": '<rect x="2.5" y="6" width="19" height="12" rx="2"/><path d="M6.5 10h11M6.5 14h7"/>',
    "portrait": '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M10 7h4M10 11h4"/>',
    "cat": '<path d="M5 9 4 3l5 3h6l5-3-1 6v5a7 7 0 0 1-14 0z"/><path d="M9 12h.01M15 12h.01M10.5 15.5c1 .8 2 .8 3 0"/>',
    "lock": '<rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.1"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
    "external": '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5H5V6h5"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="1.5" fill="{c}" stroke="none"/>',
    "sun": '<circle cx="12" cy="12" r="4.2"/><path d="M12 2.2v2.2M12 19.6v2.2M2.2 12h2.2M19.6 12h2.2M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6"/>',
    "moon": '<path d="M20.2 15.2A8.3 8.3 0 0 1 8.8 3.8 8.5 8.5 0 1 0 20.2 15.2z"/>',
}

_icon_cache: dict[tuple, QIcon] = {}


def icon(name: str, color: str = GOLD, size: int = 20) -> QIcon:
    key = (name, color, size)
    if key in _icon_cache:
        return _icon_cache[key]
    path = _ICONS.get(name)
    if not path:
        path = _ICONS["sparkle"]
    body = path.replace("{c}", color)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    dpr = 2
    pix = QPixmap(size * dpr, size * dpr)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p)
    p.end()
    pix.setDevicePixelRatio(dpr)
    ico = QIcon(pix)
    _icon_cache[key] = ico
    return ico


# ---------------------------------------------------------------------------
# small painting helpers
# ---------------------------------------------------------------------------
def draw_star(p: QPainter, center: QPointF, radius: float, color: QColor, points: int = 4) -> None:
    path = QPainterPath()
    for i in range(points * 2):
        angle = -3.1415926535 / 2 + i * 3.1415926535 / points
        r = radius if i % 2 == 0 else radius * 0.28
        pt = QPointF(center.x() + r * __import__("math").cos(angle), center.y() + r * __import__("math").sin(angle))
        if i == 0:
            path.moveTo(pt)
        else:
            path.lineTo(pt)
    path.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    p.drawPath(path)


def draw_diamond(p: QPainter, rect: QRectF, color: QColor, filled: bool = True) -> None:
    path = QPainterPath()
    cx, cy = rect.center().x(), rect.center().y()
    path.moveTo(cx, rect.top())
    path.lineTo(rect.right(), cy)
    path.lineTo(cx, rect.bottom())
    path.lineTo(rect.left(), cy)
    path.closeSubpath()
    p.setPen(QPen(color, 1.0))
    p.setBrush(color if filled else Qt.NoBrush)
    p.drawPath(path)


_element_cache: dict[tuple[str, str, int], QPixmap] = {}


def element_pixmap(element: str, size: int = 128, variant: str = "white") -> QPixmap | None:
    """Official-looking elemental glyphs supplied in assets/images/elements.

    SVGs are preferred because they stay crisp in the orb, titlebar and
    watermarks.  ``default`` falls back to the geo glyph.
    """
    element = str(element or "default").lower()
    if element not in ELEMENTS:
        element = "default"
    if element == "default":
        element = "geo"
    key = (element, variant, int(size))
    if key in _element_cache:
        return _element_cache[key]
    path = IMAGES / "elements" / f"{element}_{variant}.svg"
    if not path.exists():
        path = IMAGES / "elements" / f"{element}.svg"
    if not path.exists():
        return None
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        return None
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    renderer.render(p)
    p.end()
    pix.setDevicePixelRatio(2.0)
    _element_cache[key] = pix
    return pix


def draw_orb(p: QPainter, rect: QRectF, element: str, *, glow: bool = True, alpha: int = 255) -> None:
    info = ELEMENTS.get(element, ELEMENTS["default"])
    color = QColor(info["color"])
    color.setAlpha(alpha)
    dark = QColor(info["dark"])
    dark.setAlpha(alpha)
    cx, cy = rect.center().x(), rect.center().y()
    r = min(rect.width(), rect.height()) / 2

    p.save()
    p.setRenderHint(QPainter.Antialiasing, True)
    if glow:
        halo = QRadialGradient(cx, cy, r * 1.4)
        hc = QColor(color)
        hc.setAlpha(55 if alpha > 150 else 25)
        halo.setColorAt(0.0, hc)
        hc2 = QColor(color)
        hc2.setAlpha(0)
        halo.setColorAt(1.0, hc2)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), r * 1.4, r * 1.4)

    gradient = QRadialGradient(cx - r * 0.3, cy - r * 0.4, r * 1.4)
    gradient.setColorAt(0.0, mix(color, "#ffffff", 0.34))
    gradient.setColorAt(0.45, color)
    gradient.setColorAt(0.82, dark)
    gradient.setColorAt(1.0, mix(dark, "#000000", 0.35))
    p.setBrush(gradient)
    p.setPen(QPen(QColor(250, 238, 206, int(alpha * 0.68)), max(1.0, r * 0.045)))
    p.drawEllipse(rect)
    # inner rim
    p.setPen(QPen(QColor(255, 250, 235, int(alpha * 0.28)), 1))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(rect.adjusted(r * 0.12, r * 0.12, -r * 0.12, -r * 0.12))

    pix = element_pixmap(element, 128, "white")
    if pix is not None:
        side = r * 1.18
        p.setOpacity(max(0.0, min(1.0, alpha / 255.0)))
        p.drawPixmap(
            QRectF(cx - side / 2, cy - side / 2, side, side),
            pix,
            QRectF(pix.rect()),
        )
        p.setOpacity(1.0)
    p.restore()


# ---------------------------------------------------------------------------
# stylesheet
# ---------------------------------------------------------------------------
_QSS = r"""
* {
    color: __TEXT__;
    font-family: "Noto Sans SC", "Microsoft YaHei UI";
    font-size: 13px;
    outline: none;
}
QWidget#RootCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #0d1622, stop:0.42 #0b131d, stop:1 #0a1018);
    border: 1px solid rgba(217, 188, 125, 92);
    border-radius: 20px;
}
QWidget#RootCard[maximized="true"] {
    border-radius: 0px;
    border: none;
}
QWidget#TitleBar { background: transparent; }
QWidget#Body { background: transparent; }
QFrame#GlassCard, QFrame[glass="true"] {
    background: rgba(20, 31, 45, 215);
    border: 1px solid rgba(217, 188, 125, 35);
    border-radius: 14px;
}
QFrame#InnerCard {
    background: rgba(8, 14, 22, 118);
    border: 1px solid rgba(225, 205, 160, 22);
    border-radius: 10px;
}
QLabel { background: transparent; }
QLabel#Brand { font-family: "Cinzel"; font-size: 24px; font-weight: 600; color: __GOLD__; letter-spacing: 5px; }
QLabel#BrandSub { font-family: "Noto Serif SC"; font-size: 10px; color: __MUTED__; letter-spacing: 2px; }
QLabel#PageTitle { font-family: "Noto Serif SC"; font-size: 26px; font-weight: 600; color: __TEXT__; letter-spacing: 2px; }
QLabel#SectionTitle { font-family: "Noto Serif SC"; font-size: 17px; font-weight: 600; color: __TEXT__; letter-spacing: 1px; }
QLabel#Serif { font-family: "Noto Serif SC"; }
QLabel#Muted { color: __MUTED__; font-size: 12px; }
QLabel#Faint { color: __FAINT__; font-size: 11px; }
QLabel#Gold { color: __GOLD__; }
QLabel#Timer { font-family: "Cascadia Mono"; color: __TEXT__; letter-spacing: 1px; }
QLabel#Micro { color: __MUTED__; font-size: 10px; letter-spacing: 1px; }
QLabel#Pill {
    background: rgba(217,188,125,26);
    border: 1px solid rgba(217,188,125,55);
    border-radius: 9px;
    padding: 2px 8px;
    color: __GOLD__;
    font-size: 11px;
}
QLabel#StreakPill {
    background: rgba(227,154,145,20);
    border: 1px solid rgba(227,154,145,50);
    border-radius: 9px;
    padding: 2px 8px;
    color: #e7b1a8;
    font-size: 11px;
}
QPushButton {
    border: none;
    background: transparent;
    color: __TEXT__;
}
QPushButton#Primary {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #efdfb4, stop:0.5 #d9bc7d, stop:1 #bfa063);
    color: #201b12;
    border: 1px solid #f4e2b6;
    border-radius: 9px;
    padding: 9px 18px;
    font-weight: 600;
    letter-spacing: 1px;
}
QPushButton#Primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fff0c9, stop:1 #dcc18b);
}
QPushButton#Primary:pressed { background: #bda061; padding-top: 10px; }
QPushButton#Primary:disabled { background: rgba(217,188,125,45); color: rgba(30,25,18,120); border-color: rgba(240,220,170,30); }
QPushButton#Ghost {
    background: rgba(255,255,255,8);
    border: 1px solid rgba(217,188,125,55);
    border-radius: 9px;
    padding: 8px 16px;
    color: __TEXT_SOFT__;
}
QPushButton#Ghost:hover { background: rgba(217,188,125,26); border-color: rgba(217,188,125,105); color: __GOLD_BRIGHT__; }
QPushButton#Ghost:pressed { background: rgba(217,188,125,15); }
QPushButton#TextButton {
    color: __GOLD__;
    padding: 4px 2px;
    border-bottom: 1px solid transparent;
}
QPushButton#TextButton:hover { color: __GOLD_BRIGHT__; border-bottom-color: rgba(217,188,125,80); }
QPushButton#Danger {
    background: rgba(216,115,115,18);
    border: 1px solid rgba(216,115,115,65);
    border-radius: 9px;
    padding: 8px 16px;
    color: #e5a19a;
}
QPushButton#Danger:hover { background: rgba(216,115,115,36); }
QToolButton {
    border: none;
    background: transparent;
    border-radius: 8px;
    padding: 5px;
}
QToolButton:hover { background: rgba(217,188,125,30); }
QToolButton:pressed { background: rgba(217,188,125,15); }
QToolButton#CloseBtn:hover { background: rgba(216,115,115,85); }
QToolButton#Play {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f6e5bb, stop:0.55 #d8bb7a, stop:1 #b59658);
    border: 1px solid #f8e8c2;
    border-radius: 25px;
    color: #1c1810;
}
QToolButton#Play:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fff4d6, stop:1 #d8bb7a);
}
QToolButton#Play:pressed { background: #b4955b; }
QToolButton#SmallPlay {
    background: rgba(217,188,125,20);
    border: 1px solid rgba(217,188,125,55);
    border-radius: 18px;
}
QToolButton#SmallPlay:hover { background: rgba(217,188,125,45); }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit {
    background: rgba(7, 12, 18, 170);
    border: 1px solid rgba(217,188,125,42);
    border-radius: 8px;
    padding: 8px 10px;
    color: __TEXT__;
    selection-background-color: #75613a;
    selection-color: #fff8e8;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {
    border: 1px solid rgba(217,188,125,130);
    background: rgba(10, 17, 26, 210);
}
QLineEdit::placeholder { color: #78766c; }
QComboBox::drop-down, QDateEdit::drop-down, QTimeEdit::drop-down {
    border: none;
    width: 25px;
}
QComboBox::down-arrow, QDateEdit::down-arrow, QTimeEdit::down-arrow {
    image: url("__ARROW__");
    width: 10px;
    height: 6px;
    margin-right: 7px;
}
QComboBox QAbstractItemView {
    background: #121b27;
    border: 1px solid rgba(217,188,125,70);
    selection-background-color: #342f24;
    selection-color: __GOLD_BRIGHT__;
    outline: none;
}
QComboBox QAbstractItemView::item {
    min-height: 26px;
    padding: 2px 6px;
}
QSpinBox::up-button, QSpinBox::down-button { width: 16px; border: none; background: transparent; }
QCheckBox { spacing: 8px; color: __TEXT_SOFT__; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid rgba(217,188,125,90);
    border-radius: 4px;
    background: rgba(8,13,20,180);
}
QCheckBox::indicator:checked {
    background: __GOLD__;
    border-color: __GOLD_BRIGHT__;
}
QSlider::groove:horizontal { height: 4px; background: rgba(255,255,255,35); border-radius: 2px; }
QSlider::sub-page:horizontal { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #907741, stop:1 __GOLD__); border-radius: 2px; }
QSlider::handle:horizontal {
    width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
    background: #f2dca9; border: 1px solid #fff1c9;
}
QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 9px; margin: 2px; }
QScrollBar::handle:vertical { background: rgba(217,188,125,58); border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: rgba(217,188,125,100); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle:horizontal { background: rgba(217,188,125,55); border-radius: 4px; min-width: 30px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QMenu {
    background: #111a25;
    border: 1px solid rgba(217,188,125,75);
    border-radius: 9px;
    padding: 5px;
    color: __TEXT__;
}
QMenu::item { padding: 7px 26px 7px 12px; border-radius: 5px; }
QMenu::item:selected { background: rgba(217,188,125,32); color: __GOLD_BRIGHT__; }
QMenu::separator { height: 1px; background: rgba(217,188,125,30); margin: 5px 8px; }
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget::item {
    color: __TEXT_SOFT__;
    padding: 9px 10px;
    border-radius: 7px;
    margin: 1px 2px;
}
QListWidget::item:hover { background: rgba(255,255,255,9); }
QListWidget::item:selected { background: rgba(217,188,125,30); color: __GOLD_BRIGHT__; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab {
    background: transparent;
    color: __MUTED__;
    padding: 8px 16px;
    border-bottom: 1px solid transparent;
}
QTabBar::tab:selected { color: __GOLD__; border-bottom: 1px solid __GOLD__; }
QToolTip {
    background: #16202d;
    color: __TEXT__;
    border: 1px solid rgba(217,188,125,80);
    padding: 5px 8px;
    border-radius: 5px;
}
QDialog { background: transparent; }
QWidget#DialogCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111c29, stop:1 #0b121b);
    border: 1px solid rgba(217,188,125,100);
    border-radius: 16px;
}
QDialog QLabel { color: __TEXT__; }
QCalendarWidget QWidget { background: #0e1722; color: __TEXT__; }
QCalendarWidget QAbstractItemView:enabled {
    background: #0e1722; color: __TEXT_SOFT__;
    selection-background-color: #74603a; selection-color: #fff7e6;
}
QCalendarWidget QToolButton { color: __TEXT__; background: transparent; }
QSplitter::handle { background: rgba(217,188,125,25); }
"""


def stylesheet() -> str:
    replacements = {
        "__INK__": INK,
        "__BG__": BG,
        "__BG2__": BG2,
        "__PANEL__": PANEL,
        "__PANEL2__": PANEL2,
        "__PANEL3__": PANEL3,
        "__GOLD__": GOLD,
        "__GOLD_BRIGHT__": GOLD_BRIGHT,
        "__GOLD_SOFT__": GOLD_SOFT,
        "__GOLD_DARK__": GOLD_DARK,
        "__TEXT__": TEXT,
        "__TEXT_SOFT__": TEXT_SOFT,
        "__MUTED__": MUTED,
        "__FAINT__": FAINT,
        "__TEAL__": TEAL,
        "__ARROW__": str(IMAGES / "chevron_down.png").replace("\\", "/"),
    }
    out = _QSS
    for key, value in replacements.items():
        out = out.replace(key, value)
    if MODE == "light":
        out = lighten_qss(out) + _light_overrides()
    return out


def _light_overrides() -> str:
    """A few hand-tuned surfaces that benefit from more than a colour remap."""
    return f"""
QWidget#RootCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fcf7ec, stop:0.46 #f4ead9, stop:1 #eadcc5);
    border: 1px solid rgba(152, 117, 54, 115);
    border-radius: 20px;
}}
QWidget#RootCard[maximized="true"] {{ border: none; border-radius: 0px; }}
QFrame#GlassCard, QFrame[glass="true"] {{
    background: rgba(255, 249, 238, 232);
    border: 1px solid rgba(152, 117, 54, 62);
}}
QFrame#InnerCard {{
    background: rgba(255, 251, 243, 190);
    border: 1px solid rgba(152, 117, 54, 42);
}}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit {{
    background: rgba(255, 252, 247, 242);
    color: {TEXT};
    border: 1px solid rgba(152, 117, 54, 58);
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus,
QComboBox:focus, QDateEdit:focus, QTimeEdit:focus {{
    background: #fffdf8;
    border: 1px solid rgba(152, 117, 54, 135);
}}
QPushButton#Ghost {{
    background: rgba(255, 250, 240, 135);
    border: 1px solid rgba(152, 117, 54, 78);
    color: {TEXT_SOFT};
}}
QMenu, QComboBox QAbstractItemView {{
    background: #fbf5e9;
    border: 1px solid rgba(152, 117, 54, 85);
    color: {TEXT};
}}
QToolTip {{
    background: #fffaf0;
    color: {TEXT};
    border: 1px solid rgba(152, 117, 54, 95);
}}
QWidget#DialogCard {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #fdf8ef, stop:1 #f0e5d3);
    border: 1px solid rgba(152, 117, 54, 105);
}}
QCalendarWidget QWidget {{ background: #fbf5e9; color: {TEXT}; }}
QCalendarWidget QAbstractItemView:enabled {{
    background: #fbf5e9;
    color: {TEXT_SOFT};
    selection-background-color: rgba(152, 117, 54, 35);
    selection-color: {TEXT};
}}
"""


# A few surfaces and text colours are still literal in the original dark QSS.
# For daylight mode we remap them instead of duplicating the entire stylesheet.
_HEX_MAP = {
    "#070b11": "#f6efe2",
    "#0a1019": "#f3ebdd",
    "#0a1018": "#f6efe2",
    "#0d1622": "#fcf8ef",
    "#0b131d": "#f3ecde",
    "#0a111a": "#f7f0e3",
    "#0b1119": "#f1e7d5",
    "#0b121b": "#f0e6d3",
    "#0e1722": "#faf4e8",
    "#101e2d": "#f3efe6",
    "#111a24": "#fbf6ed",
    "#111a25": "#fbf6ed",
    "#111b26": "#f7f0e3",
    "#111c29": "#fbf6ed",
    "#121b27": "#fbf6ed",
    "#121c28": "#fbf6ed",
    "#141f2b": "#f4ebdc",
    "#141f2d": "#f4ebdc",
    "#152333": "#f3eadb",
    "#16202d": "#f7f0e3",
    "#172333": "#f1e8d8",
    "#1b2838": "#f4e9d6",
    "#1c2a3b": "#eadfca",
    "#20344f": "#eef4ee",
    "#14253c": "#f3eee4",
    "#0b1628": "#f0e8da",
    "#eee7da": "#3b3125",
    "#d7cdbb": "#4a3d2d",
    "#a89d8b": "#5b4d3a",
    "#e9f2ee": "#352c20",
    "#f0d9a5": "#87652c",
    "#e6d49b": "#87652c",
    "#f3ddaa": "#9b7838",
    "#e8ddbd": "#6b583c",
    "#fbf7ee": "#3a3024",
    "#a98e5c": "#80612b",
    "#e7b1a8": "#a75a56",
    "#e5a19a": "#a75a56",
    "#6f5a36": "#b9a37d",
}

_RGBA_MAP = {
    (20, 31, 45, 190): (255, 250, 240, 235),
    (20, 31, 45, 215): (255, 250, 240, 238),
    (18, 28, 40, 175): (255, 250, 240, 228),
    (27, 42, 59, 235): (255, 250, 240, 242),
    (13, 21, 31, 235): (248, 240, 226, 242),
    (24, 38, 53, 230): (255, 250, 240, 242),
    (24, 38, 53, 220): (255, 250, 240, 240),
    (33, 60, 64, 215): (226, 242, 237, 235),
    (7, 12, 18, 210): (255, 250, 240, 242),
    (7, 12, 18, 198): (255, 250, 240, 240),
    (7, 12, 18, 170): (255, 250, 240, 235),
    (10, 17, 26, 210): (255, 252, 246, 245),
    (18, 28, 40, 175): (255, 250, 240, 228),
    (8, 14, 22, 118): (255, 252, 246, 170),
    (8, 14, 21, 75): (80, 65, 45, 10),
    (8, 14, 21, 88): (80, 65, 45, 12),
    (8, 14, 21, 100): (80, 65, 45, 14),
    (8, 13, 20, 120): (255, 250, 240, 210),
    (8, 13, 20, 130): (255, 250, 240, 215),
    (8, 13, 20, 140): (255, 250, 240, 220),
    (8, 14, 21, 165): (255, 250, 240, 228),
    (8, 14, 21, 185): (255, 250, 240, 236),
    (8, 13, 20, 180): (255, 252, 246, 235),
    (255, 255, 255, 4): (70, 55, 35, 10),
    (255, 255, 255, 5): (70, 55, 35, 12),
    (255, 255, 255, 7): (70, 55, 35, 14),
    (255, 255, 255, 8): (70, 55, 35, 16),
    (255, 255, 255, 9): (70, 55, 35, 18),
    (255, 255, 255, 22): (70, 55, 35, 34),
    (255, 255, 255, 35): (70, 55, 35, 48),
}

_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
_RGBA_RE = re.compile(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


def lighten_qss(text: str) -> str:
    """Turn a dark QSS snippet into its parchment equivalent.

    Dark islands (the character stage, Paimon note and level-up veil) opt out
    via the ``darkIsland`` widget property, so their night-sky look survives.
    """
    if not text or MODE != "light":
        return text

    def hex_sub(match: re.Match) -> str:
        return _HEX_MAP.get(match.group(0).lower(), match.group(0))

    def rgba_sub(match: re.Match) -> str:
        key = tuple(int(x) for x in match.groups())
        out = _RGBA_MAP.get(key)
        if out is None:
            return match.group(0)
        return f"rgba({out[0]},{out[1]},{out[2]},{out[3]})"

    return _RGBA_RE.sub(rgba_sub, _HEX_RE.sub(hex_sub, text))


_DARK_BUILD_DEPTH = 0


def begin_dark_island() -> None:
    global _DARK_BUILD_DEPTH
    _DARK_BUILD_DEPTH += 1


def end_dark_island() -> None:
    global _DARK_BUILD_DEPTH
    _DARK_BUILD_DEPTH = max(0, _DARK_BUILD_DEPTH - 1)


def _is_dark_island(widget: QWidget) -> bool:
    if _DARK_BUILD_DEPTH:
        return True
    cur = widget
    while cur is not None:
        try:
            if bool(cur.property("darkIsland")):
                return True
        except Exception:
            pass
        cur = cur.parentWidget()
    return False


def install_qss_hook() -> None:
    if getattr(QWidget, "_black_light_qss_hook", False):
        return
    original = QWidget.setStyleSheet

    def set_style_sheet(self, sheet):
        if MODE == "light" and sheet and not _is_dark_island(self):
            sheet = lighten_qss(str(sheet))
        original(self, sheet)

    QWidget.setStyleSheet = set_style_sheet
    QWidget._black_light_qss_hook = True


install_qss_hook()



def apply_theme(app: QApplication) -> None:
    init_fonts()
    app.setFont(font(13, SANS))
    app.setStyleSheet(stylesheet())
    app.setStyle("Fusion")
    app.setStyleSheet(stylesheet())
