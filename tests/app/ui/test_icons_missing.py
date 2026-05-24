# SPDX-License-Identifier: GPL-3.0-or-later
"""_icons 미존재 file fallback unit — cycle 169.765 신설.

load_icon / load_pixmap 의 svg_path 부재 시 empty QIcon/QPixmap 반환 분기(L28/L45) 회수.
QIcon/QPixmap = 경량 (QWidget 아님 — cumulative retain hang 무관).
"""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


class TestLoadIconMissing:
    def test_load_icon_missing_returns_empty(self, qapp) -> None:
        from app.ui._icons import load_icon

        # 한글 주석 — 부재 name → 빈 QIcon (null) 반환
        icon = load_icon("nonexistent_icon_xyz")
        assert icon.isNull()

    def test_load_pixmap_missing_returns_empty(self, qapp) -> None:
        from app.ui._icons import load_pixmap

        pix = load_pixmap("nonexistent_icon_xyz")
        assert pix.isNull()
