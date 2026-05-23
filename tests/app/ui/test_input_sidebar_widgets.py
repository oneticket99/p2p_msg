# SPDX-License-Identifier: GPL-3.0-or-later
"""InputBar + SidebarRail widget unit test — cycle 169.714 신설."""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestInputBar:
    def test_reply_context_set_and_get(self, qapp) -> None:
        from app.ui.input_bar import InputBar

        ib = InputBar()
        ib.set_reply_to("alice", "original text")
        ctx = ib.reply_context()
        assert ctx == ("alice", "original text")
        ib.close()

    def test_reply_context_clear(self, qapp) -> None:
        from app.ui.input_bar import InputBar

        ib = InputBar()
        ib.set_reply_to("bob", "hi")
        ib.clear_reply_to()
        assert ib.reply_context() is None
        ib.close()

    def test_default_no_reply_context(self, qapp) -> None:
        from app.ui.input_bar import InputBar

        ib = InputBar()
        assert ib.reply_context() is None
        ib.close()


class TestSidebarRail:
    def test_active_tab_default_friends(self, qapp) -> None:
        from app.ui.sidebar_rail import SidebarRail

        rail = SidebarRail()
        # 한글 주석 — default active tab = friends
        assert rail.active_tab() == "friends"
        rail.close()

    def test_set_active_tab_known(self, qapp) -> None:
        from app.ui.sidebar_rail import SidebarRail

        rail = SidebarRail()
        rail.set_active_tab("settings")
        assert rail.active_tab() == "settings"
        rail.close()

    def test_set_active_tab_unknown_ignored(self, qapp) -> None:
        # 한글 주석 — unknown key → 변경 차단
        from app.ui.sidebar_rail import SidebarRail

        rail = SidebarRail()
        initial = rail.active_tab()
        rail.set_active_tab("bogus-tab")
        # 한글 주석 — 부재 key 시점 set 차단 → 이전 retain
        assert rail.active_tab() == initial
        rail.close()
