# SPDX-License-Identifier: GPL-3.0-or-later
"""admin_menu chain isolated test — cycle 169.693 신설.

MainWindow instantiation 부재 (cumulative window leak hang 회수) + MagicMock self +
mixin method 직접 호출 pattern (cycle 169.644~647 정합).

cycle 169.636 의 4 skip method 의 본 file 안 isolated 재구성:
1. non-admin role → _on_open_emoji_moderation 차단
2. decision_made signal handler → status_bar.showMessage 1회
3. EMOJI_MODERATION_ADMIN_TOKEN env 부재 → 차단
4. EMOJI_MODERATION_ADMIN_TOKEN env 빈 string → strip 차단
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("PyQt6")


class TestNonAdminBlocks:
    """role=member → _on_open_emoji_moderation 직접 호출 차단."""

    def test_non_admin_role_blocks_dialog(self) -> None:
        from app.ui._menu_bar_mixin import MenuBarMixin

        # 한글 주석 — MagicMock self + _is_admin_role=False (member)
        self_mock = MagicMock()
        self_mock._is_admin_role = MagicMock(return_value=False)
        self_mock._current_user_role = "member"

        with patch(
            "app.ui.confirm_dialog.ConfirmDialog.show_warning"
        ) as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            # 한글 주석 — admin 차단 → open_emoji_moderation 미호출
            fake_open.assert_not_called()
            fake_warning.assert_called_once()


class TestAdminTokenAbsent:
    """EMOJI_MODERATION_ADMIN_TOKEN env 부재 → 차단."""

    def test_missing_token_blocks(self) -> None:
        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        self_mock._is_admin_role = MagicMock(return_value=True)
        self_mock._current_user_role = "admin"

        # 한글 주석 — env 제거 (clear=True + EMOJI_MODERATION_ADMIN_TOKEN 부재)
        env_clean = {k: v for k, v in os.environ.items() if k != "EMOJI_MODERATION_ADMIN_TOKEN"}
        with patch.dict(os.environ, env_clean, clear=True), patch(
            "app.ui.confirm_dialog.ConfirmDialog.show_warning"
        ) as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            fake_open.assert_not_called()
            fake_warning.assert_called_once()

    def test_empty_token_blocks(self) -> None:
        # 한글 주석 — 빈 string + 공백 만 token strip 차단
        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        self_mock._is_admin_role = MagicMock(return_value=True)
        self_mock._current_user_role = "admin"

        with patch.dict(os.environ, {"EMOJI_MODERATION_ADMIN_TOKEN": "   "}, clear=False), patch(
            "app.ui.confirm_dialog.ConfirmDialog.show_warning"
        ) as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            fake_open.assert_not_called()
            fake_warning.assert_called_once()


class TestDecisionFeedback:
    """_on_moderation_decision → status_bar.showMessage."""

    def test_status_bar_shows_decision(self) -> None:
        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        self_mock._status_bar = MagicMock()

        MenuBarMixin._on_moderation_decision(self_mock, pack_id=42, decision="approve")

        # 한글 주석 — showMessage 1회 호출 + pack_id + decision 포함
        self_mock._status_bar.showMessage.assert_called_once()
        msg = self_mock._status_bar.showMessage.call_args.args[0]
        assert "42" in msg
        assert "approve" in msg
