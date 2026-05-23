# SPDX-License-Identifier: GPL-3.0-or-later
"""mixin batch 4 isolated unit — cycle 169.710 신설.

SignalingMixin + RoomGroupChatMixin + FriendProfileMixin + ChatNavigationMixin.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


pytest.importorskip("PyQt6")


class TestSignalingMixin:
    def test_on_signaling_answer_no_client_drop(self) -> None:
        from app.ui._signaling_mixin import SignalingMixin

        self_mock = MagicMock()
        self_mock._active_call_client = None
        # 한글 주석 — active_call_client 부재 → drop + 예외 부재
        SignalingMixin._on_signaling_answer(self_mock, "alice", "sdp-data")

    def test_on_signaling_ice_no_client_drop(self) -> None:
        from app.ui._signaling_mixin import SignalingMixin

        self_mock = MagicMock()
        self_mock._active_call_client = None
        SignalingMixin._on_signaling_ice(self_mock, "alice", {"candidate": "x"})

    def test_on_signaling_peer_joined_sets_active(self) -> None:
        from app.ui._signaling_mixin import SignalingMixin

        self_mock = MagicMock()
        SignalingMixin._on_signaling_peer_joined(self_mock, "bob")
        assert self_mock._active_peer_id == "bob"


class TestRoomGroupChatMixin:
    def test_on_chat_clear_calls_chat_view_clear(self) -> None:
        from app.ui._room_group_chat_mixin import RoomGroupChatMixin

        self_mock = MagicMock()
        self_mock._active_chat_kind = "friend"
        self_mock._active_chat_target_id = 10
        self_mock._dm_history = {("friend", 10): ["msg1"]}
        RoomGroupChatMixin._on_chat_clear(self_mock)
        self_mock._chat_view.clear_messages.assert_called_once()
        assert self_mock._dm_history[("friend", 10)] == []

    def test_on_chat_leave_filters_entries(self) -> None:
        from app.ui._room_group_chat_mixin import RoomGroupChatMixin

        # 한글 주석 — chat_list entries filter — active kind+target 의 entry 제거
        entry1 = MagicMock(kind="friend", target_id=10)
        entry2 = MagicMock(kind="friend", target_id=20)
        self_mock = MagicMock()
        self_mock._active_chat_kind = "friend"
        self_mock._active_chat_target_id = 10
        self_mock._chat_list_panel._entries = [entry1, entry2]

        RoomGroupChatMixin._on_chat_leave(self_mock)
        # entry1 제거 + entry2 유지
        call_args = self_mock._chat_list_panel.set_entries.call_args.args[0]
        assert len(call_args) == 1
        assert call_args[0].target_id == 20

    def test_on_chat_leave_no_panel_returns(self) -> None:
        from app.ui._room_group_chat_mixin import RoomGroupChatMixin

        self_mock = MagicMock()
        self_mock._active_chat_kind = "friend"
        self_mock._chat_list_panel = None
        RoomGroupChatMixin._on_chat_leave(self_mock)
        # 한글 주석 — early return verify (예외 부재 + chat_view.clear 미호출)
        self_mock._chat_view.clear_messages.assert_not_called()


class TestFriendProfileMixin:
    def test_profile_mute_toggles_set(self) -> None:
        from app.ui._friend_profile_mixin import FriendProfileMixin

        self_mock = MagicMock()
        self_mock._muted_friends = set()
        FriendProfileMixin._profile_mute_clicked(self_mock, 10)
        assert 10 in self_mock._muted_friends
        # 한글 주석 — 두번째 호출 = unmute
        FriendProfileMixin._profile_mute_clicked(self_mock, 10)
        assert 10 not in self_mock._muted_friends

    def test_profile_message_clicked_redirects(self) -> None:
        from app.ui._friend_profile_mixin import FriendProfileMixin

        self_mock = MagicMock()
        modal = MagicMock()
        FriendProfileMixin._profile_message_clicked(self_mock, modal, 20)
        modal.accept.assert_called_once()
        self_mock._on_chat_selected.assert_called_once_with("friend", 20)

    def test_lookup_friend_name_falls_back(self) -> None:
        from app.ui._friend_profile_mixin import FriendProfileMixin

        self_mock = MagicMock()
        # 한글 주석 — _friends empty → "friend #N" fallback
        self_mock._friend_list._friends = []
        result = FriendProfileMixin._lookup_friend_name(self_mock, 99)
        assert "friend" in result.lower()
        assert "99" in result


class TestChatNavigationMixin:
    def test_on_sidebar_tab_clicked_friends_sets_direct_chat(self) -> None:
        from app.ui._chat_navigation_mixin import ChatNavigationMixin

        self_mock = MagicMock()
        self_mock._STACK_DIRECT_CHAT = 0
        ChatNavigationMixin._on_sidebar_tab_clicked(self_mock, "friends")
        self_mock._stacked.setCurrentIndex.assert_called_with(0)
