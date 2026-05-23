# SPDX-License-Identifier: GPL-3.0-or-later
"""MenuBarMixin admin chain isolated test — cycle 169.644 mock isolation refactor.

cycle 169.636 안 cumulative window leak hang 회수 path. MainWindow instantiation
부재 + mixin method 직접 호출 + MagicMock self instance pattern.

4 method skip 영역 회수:
- _on_open_emoji_moderation 안 non-admin guard (cycle 169.636 6th)
- _on_moderation_decision status bar update (cycle 169.636 7th)
- _on_open_emoji_moderation 안 missing token guard (cycle 169.636 8th)
- _on_open_emoji_moderation 안 empty token guard (cycle 169.636 9th)

MainWindow 부재 → cumulative leak 회피. mixin method = static-ish (self.attribute
의존 만) → MagicMock self 안 admin role/token 환경 직접 inject.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# 한글 주석: headless 의무 — Qt offscreen platform
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석: PyQt6 부재 시 module skip
pytest.importorskip("PyQt6")


class TestOnOpenEmojiModerationGuard:
    """_on_open_emoji_moderation 안 guard chain isolated (MainWindow 부재)."""

    def test_non_admin_role_blocks_dialog(self) -> None:
        """role=member 시 ConfirmDialog.show_warning 1회 + dialog 미생성."""

        from app.ui._menu_bar_mixin import MenuBarMixin

        # 한글 주석: MagicMock self — _is_admin_role False + _current_user_role "member"
        self_mock = MagicMock()
        self_mock._is_admin_role.return_value = False
        self_mock._current_user_role = "member"

        with patch("app.ui.confirm_dialog.ConfirmDialog.show_warning") as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            fake_warning.assert_called_once()
            fake_open.assert_not_called()

    def test_missing_admin_token_blocks_dialog(self) -> None:
        """admin role + EMOJI_MODERATION_ADMIN_TOKEN env 부재 → warning + 차단."""

        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        self_mock._is_admin_role.return_value = True

        env_clean = {k: v for k, v in os.environ.items() if k != "EMOJI_MODERATION_ADMIN_TOKEN"}
        with patch.dict(os.environ, env_clean, clear=True), patch(
            "app.ui.confirm_dialog.ConfirmDialog.show_warning"
        ) as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            fake_warning.assert_called_once()
            fake_open.assert_not_called()

    def test_empty_admin_token_blocks_dialog(self) -> None:
        """admin role + token=빈 string → strip 정합 → 차단."""

        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        self_mock._is_admin_role.return_value = True

        with patch.dict(
            os.environ, {"EMOJI_MODERATION_ADMIN_TOKEN": "   "}, clear=False
        ), patch(
            "app.ui.confirm_dialog.ConfirmDialog.show_warning"
        ) as fake_warning, patch(
            "app.ui.admin.open_emoji_moderation"
        ) as fake_open:
            MenuBarMixin._on_open_emoji_moderation(self_mock)

            fake_warning.assert_called_once()
            fake_open.assert_not_called()


class TestOnModerationDecisionStatusBar:
    """_on_moderation_decision 안 status bar showMessage isolated."""

    def test_decision_handler_updates_status_bar(self) -> None:
        """pack_id + decision = status bar showMessage 1회 + 본문 포함."""

        from app.ui._menu_bar_mixin import MenuBarMixin

        self_mock = MagicMock()
        # 한글 주석: status_bar.showMessage MagicMock (직접 attribute) — call count 검증
        status_bar = MagicMock()
        self_mock._status_bar = status_bar

        MenuBarMixin._on_moderation_decision(self_mock, pack_id=42, decision="approve")

        assert status_bar.showMessage.call_count == 1
        msg = status_bar.showMessage.call_args.args[0]
        assert "42" in msg
        assert "approve" in msg
