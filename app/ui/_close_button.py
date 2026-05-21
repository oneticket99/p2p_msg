# SPDX-License-Identifier: GPL-3.0-or-later
"""공통 dialog close button factory (cycle 169.324).

사용자 directive image #87 — telegram align circular close button.
모든 dialog 안 close button 의 외형 + size + 동작 통일 의무.
"""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QWidget


def make_close_button(on_close: Callable[[], None], parent: Optional[QWidget] = None) -> QPushButton:
    """telegram align circular close button — 모든 dialog 안 공통.

    - size: 36x36 (circular)
    - bg: subtle light overlay (rgba)
    - border: 1px subtle ring
    - glyph: ✕ small + muted color
    - hover: bg + glyph contrast 강화
    """
    # 한글 주석 — 사용자 directive image #87 회수 — telegram circular muted close
    btn = QPushButton("✕", parent)
    btn.setFixedSize(36, 36)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton {"
        " color: #6b7280;"
        " background-color: rgba(255, 255, 255, 0.04);"
        " border: 1px solid rgba(255, 255, 255, 0.10);"
        " border-radius: 18px;"
        " font-size: 12px;"
        " font-weight: 500;"
        "}"
        "QPushButton:hover {"
        " background-color: rgba(255, 255, 255, 0.08);"
        " color: #f3f4f6;"
        " border: 1px solid rgba(255, 255, 255, 0.18);"
        "}"
        "QPushButton:pressed {"
        " background-color: rgba(255, 255, 255, 0.12);"
        "}"
    )
    btn.clicked.connect(on_close)  # type: ignore[arg-type]
    return btn
