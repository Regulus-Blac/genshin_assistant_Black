"""A tiny global switch for "the user is dragging the window edge right now".

While a resize gesture is running, heavy decorations (gradients, drop shadows,
big blurred backdrops) are skipped so a full window repaint fits into one frame.
The quality comes back as soon as the mouse is released.
"""
from __future__ import annotations

_fast = False


def set_fast(value: bool) -> None:
    global _fast
    _fast = bool(value)


def is_fast() -> bool:
    return _fast
