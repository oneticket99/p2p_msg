# SPDX-License-Identifier: GPL-3.0-or-later
"""mixin isolated batch unit test — cycle 169.705 신설.

ChatSendMixin + ChatNavigationMixin + FriendStatusMixin method 직접 호출 (MagicMock self).
MainWindow instantiation 부재 — cumulative window leak 회피.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("PyQt6")


class TestChatSendMixinInputSlots:
    def test_on_input_message_sent_calls_send_clicked(self) -> None:
        from app.ui._chat_send_mixin import ChatSendMixin

        self_mock = MagicMock()
        self_mock._input_edit = MagicMock()

        ChatSendMixin._on_input_message_sent(self_mock, "hello")

        # 한글 주석 — _input_edit.setPlainText + _on_send_clicked + clear chain
        self_mock._input_edit.setPlainText.assert_called_once_with("hello")
        self_mock._on_send_clicked.assert_called_once()
        self_mock._input_edit.clear.assert_called_once()

    def test_on_input_file_attached_graceful_when_no_sender(self) -> None:
        # 한글 주석 — _file_sender 부재 → ChatView add_message system path
        from datetime import datetime as _dt

        from app.ui._chat_send_mixin import ChatSendMixin

        self_mock = MagicMock(spec=["_chat_view"])
        self_mock._chat_view = MagicMock()

        with patch.object(ChatSendMixin, "_on_input_file_attached",
                          ChatSendMixin._on_input_file_attached):
            ChatSendMixin._on_input_file_attached(
                self_mock, ["/tmp/file1.txt", "/tmp/file2.png"],
            )

        # 한글 주석 — 2 file 의 system message 2회 호출
        assert self_mock._chat_view.add_message.call_count == 2

    def test_on_chat_reply_requested_sets_input_bar(self) -> None:
        from app.ui._chat_send_mixin import ChatSendMixin

        self_mock = MagicMock()
        ChatSendMixin._on_chat_reply_requested(self_mock, "alice", "hi there")
        self_mock._input_bar.set_reply_to.assert_called_once_with("alice", "hi there")


class TestChatSendMixinSendClicked:
    def test_group_mode_blocks(self) -> None:
        # 한글 주석 — _STACK_DIRECT_CHAT != currentIndex → 차단
        from app.ui._chat_send_mixin import ChatSendMixin

        self_mock = MagicMock()
        self_mock._stacked.currentIndex.return_value = 99
        self_mock._STACK_DIRECT_CHAT = 0

        result = ChatSendMixin._on_send_clicked(self_mock)
        assert result is None
        # 한글 주석 — _input_edit.toPlainText 호출 부재 (early return)
        self_mock._input_edit.toPlainText.assert_not_called()

    def test_empty_text_returns(self) -> None:
        from app.ui._chat_send_mixin import ChatSendMixin

        self_mock = MagicMock()
        self_mock._stacked.currentIndex.return_value = 0
        self_mock._STACK_DIRECT_CHAT = 0
        self_mock._input_edit.toPlainText.return_value = "   "

        result = ChatSendMixin._on_send_clicked(self_mock)
        assert result is None


class TestFriendStatusMixin:
    @pytest.mark.asyncio
    async def test_fetch_user_status_no_token_returns(self) -> None:
        # 한글 주석 — token 부재 → early return + REST 호출 부재
        from app.ui._friend_status_mixin import FriendStatusMixin

        self_mock = MagicMock()
        self_mock._config.api_base = "https://example.com"
        self_mock._session_token = ""

        # 한글 주석 — early return verify (예외 부재)
        result = await FriendStatusMixin._fetch_user_status(self_mock, user_id=10)
        assert result is None
