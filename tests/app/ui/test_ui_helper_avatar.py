# SPDX-License-Identifier: GPL-3.0-or-later
"""UI helper avatar + close_button unit — cycle 169.736 신설."""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestGetInitials:
    def test_empty_returns_question(self) -> None:
        from app.ui._avatar_helper import get_initials

        assert get_initials("") == "?"
        assert get_initials("   ") == "?"

    def test_korean_2_chars(self) -> None:
        from app.ui._avatar_helper import get_initials

        # 한글 주석 — 한글 2자 retain
        assert get_initials("홍길동") == "홍길"

    def test_english_2_upper(self) -> None:
        from app.ui._avatar_helper import get_initials

        assert get_initials("alice") == "AL"

    def test_single_char_english_upper(self) -> None:
        from app.ui._avatar_helper import get_initials

        assert get_initials("a") == "A"

    def test_single_char_korean_retain(self) -> None:
        from app.ui._avatar_helper import get_initials

        assert get_initials("가") == "가"


class TestMakeInitialPixmap:
    def test_returns_pixmap(self, qapp) -> None:
        from PyQt6.QtGui import QPixmap

        from app.ui._avatar_helper import make_initial_pixmap

        pix = make_initial_pixmap("Alice", size=48)
        assert isinstance(pix, QPixmap)
        assert pix.width() == 48
        assert pix.height() == 48

    def test_custom_size(self, qapp) -> None:
        from app.ui._avatar_helper import make_initial_pixmap

        pix = make_initial_pixmap("Bob", size=160)
        assert pix.width() == 160


class TestMakeCloseButton:
    def test_returns_button(self, qapp) -> None:
        from PyQt6.QtWidgets import QPushButton

        from app.ui._close_button import make_close_button

        btn = make_close_button(lambda: None)
        assert isinstance(btn, QPushButton)

    def test_on_close_fires(self, qapp) -> None:
        from app.ui._close_button import make_close_button

        clicked = []
        btn = make_close_button(lambda: clicked.append(True))
        # 한글 주석 — click signal → on_close 호출
        btn.click()
        assert clicked == [True]
