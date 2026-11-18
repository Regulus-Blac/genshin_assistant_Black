"""Level-curve regression test (60-level, increasing difficulty)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from black.levels import MAX_LEVEL, THRESHOLDS, level_from_seconds, level_info  # noqa: E402


def main() -> int:
    assert MAX_LEVEL == 60
    assert len(THRESHOLDS) == 60
    assert THRESHOLDS[0] == 0
    increments = [THRESHOLDS[i + 1] - THRESHOLDS[i] for i in range(len(THRESHOLDS) - 1)]
    assert all(increments[i] <= increments[i + 1] for i in range(len(increments) - 1))
    assert increments[-1] > increments[0] * 100
    assert level_from_seconds(0) == 1
    assert level_from_seconds(THRESHOLDS[1] - 1) == 1
    assert level_from_seconds(THRESHOLDS[1]) == 2
    assert level_from_seconds(THRESHOLDS[-1]) == 60
    info = level_info(THRESHOLDS[-1], 0)
    assert info.is_max and info.level == 60
    assert info.progress == 1.0 and info.to_next_seconds == 0
    print("levels", MAX_LEVEL, "hours", round(THRESHOLDS[-1] / 3600), "last increment", round(increments[-1] / 3600, 1))
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
