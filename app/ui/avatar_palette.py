# SPDX-License-Identifier: GPL-3.0-or-later
"""AvatarPalette — telegram desktop align per-user gradient color util.

hash(name) → 7 color palette index 균등 분포 — telegram desktop Win11 의 avatar fallback 정합.
chat_list_panel delegate + message_bubble sender label + chat_header avatar 의 단일 source of truth.
"""

from __future__ import annotations

import hashlib

# 한글 주석 — telegram desktop dark mode 7 gradient palette (top → bottom)
# 7 색상 (red/orange/violet/green/cyan/blue/pink) hex pair = light start + dark end
_PALETTE: list[tuple[str, str]] = [
    ("#E17076", "#A0464B"),  # red
    ("#F2A675", "#C0794A"),  # orange
    ("#A695E7", "#7060B0"),  # violet
    ("#7BC862", "#4A8C3F"),  # green
    ("#65AADD", "#3A7AB0"),  # cyan
    ("#6EC9CB", "#3F9395"),  # blue (teal)
    ("#EE7AAE", "#B05080"),  # pink
]


def palette_pair(name: str) -> tuple[str, str]:
    """name hash → telegram gradient pair (start, end) — 7 entry 균등 분포."""
    if not name:
        return _PALETTE[0]
    digest = hashlib.md5(name.encode("utf-8")).digest()
    idx = digest[0] % len(_PALETTE)
    return _PALETTE[idx]


def palette_solid(name: str) -> str:
    """name hash → solid hex (start color) — single bg fill 영역 sources."""
    return palette_pair(name)[0]
