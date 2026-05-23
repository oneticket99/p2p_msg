# SPDX-License-Identifier: GPL-3.0-or-later
"""mixin batch 2 isolated unit test — cycle 169.707 신설.

InviteMixin + TrayMixin + FriendSearchMixin method 직접 호출 (MagicMock self).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("PyQt6")


class TestInviteMixin:
    def test_on_invite_failed_status_bar(self) -> None:
        from app.ui._invite_mixin import InviteMixin

        self_mock = MagicMock()
        InviteMixin._on_invite_failed(self_mock, "friends fetch fail")
        self_mock._status_bar.showMessage.assert_called_once_with(
            "friends fetch fail", 4000,
        )


class TestTrayMixin:
    def test_on_tray_show_calls_restore_chain(self) -> None:
        from app.ui._tray_mixin import TrayMixin

        self_mock = MagicMock()
        TrayMixin._on_tray_show(self_mock)
        # 한글 주석 — restore chain 3 method
        self_mock.showNormal.assert_called_once()
        self_mock.raise_.assert_called_once()
        self_mock.activateWindow.assert_called_once()

    def test_on_tray_show_graceful_exception(self) -> None:
        from app.ui._tray_mixin import TrayMixin

        # 한글 주석 — showNormal exception graceful (log + return)
        self_mock = MagicMock()
        self_mock.showNormal.side_effect = RuntimeError("Qt error")
        TrayMixin._on_tray_show(self_mock)
        # 한글 주석 — 예외 전파 차단 verify (exception 부재 = PASS)

    def test_on_tray_logout_dispatches(self) -> None:
        from app.ui._tray_mixin import TrayMixin

        self_mock = MagicMock()
        TrayMixin._on_tray_logout(self_mock)
        self_mock._perform_logout_and_relogin.assert_called_once()

    def test_on_tray_activated_doubleclick_calls_show(self) -> None:
        from PyQt6.QtWidgets import QSystemTrayIcon

        from app.ui._tray_mixin import TrayMixin

        self_mock = MagicMock()
        TrayMixin._on_tray_activated(
            self_mock, QSystemTrayIcon.ActivationReason.DoubleClick,
        )
        self_mock._on_tray_show.assert_called_once()

    def test_on_tray_activated_ignored_other(self) -> None:
        from PyQt6.QtWidgets import QSystemTrayIcon

        from app.ui._tray_mixin import TrayMixin

        self_mock = MagicMock()
        # 한글 주석 — Context (RMB) = show 차단
        TrayMixin._on_tray_activated(
            self_mock, QSystemTrayIcon.ActivationReason.Context,
        )
        self_mock._on_tray_show.assert_not_called()


class TestFriendSearchMixin:
    def test_pending_resolved_updates_badge(self) -> None:
        # 한글 주석 — pending_resolved signal handler — accept=True path
        from app.ui._friend_search_mixin import FriendSearchMixin

        self_mock = MagicMock()
        with patch("asyncio.ensure_future") as fake_ef:
            FriendSearchMixin._on_pending_resolved(
                self_mock, user_id=20, accepted=True,
            )
        # 한글 주석 — _refresh_pending_badge ensure_future 스케줄 verify
        assert fake_ef.called
