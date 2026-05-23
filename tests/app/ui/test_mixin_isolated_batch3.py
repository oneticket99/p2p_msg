# SPDX-License-Identifier: GPL-3.0-or-later
"""mixin batch 3 isolated unit — cycle 169.709 신설.

MenuActionsMixin + ChatHeaderMixin + ChatHelperMixin + DialogCenterMixin.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


pytest.importorskip("PyQt6")


class TestMenuActionsMixin:
    def test_on_open_direct_chat_sets_stacked_index(self) -> None:
        from app.ui._menu_actions_mixin import MenuActionsMixin

        self_mock = MagicMock()
        self_mock._STACK_DIRECT_CHAT = 0
        MenuActionsMixin._on_open_direct_chat(self_mock)
        self_mock._stacked.setCurrentIndex.assert_called_once_with(0)
        self_mock._input_container.setVisible.assert_called_once_with(True)

    def test_on_open_friend_list_sets_stacked_index(self) -> None:
        from app.ui._menu_actions_mixin import MenuActionsMixin

        self_mock = MagicMock()
        self_mock._current_user_id = 10
        self_mock._STACK_FRIENDS = 2
        self_mock._friend_list._friends = []
        MenuActionsMixin._on_open_friend_list(self_mock)
        self_mock._stacked.setCurrentIndex.assert_called_once_with(2)
        self_mock._refresh_chat_list_panel.assert_called_once()

    def test_on_open_friend_list_zero_viewer_fallback(self) -> None:
        # 한글 주석 — _current_user_id None → 0 fallback
        from app.ui._menu_actions_mixin import MenuActionsMixin

        self_mock = MagicMock()
        self_mock._current_user_id = None
        self_mock._STACK_FRIENDS = 2
        self_mock._friend_list._friends = []
        MenuActionsMixin._on_open_friend_list(self_mock)
        # 한글 주석 — set_friends 의 viewer_id=0
        call_kwargs = self_mock._friend_list.set_friends.call_args.kwargs
        assert call_kwargs["viewer_id"] == 0


class TestChatHeaderMixin:
    def test_on_header_sidebar_toggle_hides_when_visible(self) -> None:
        from app.ui._chat_header_mixin import ChatHeaderMixin

        self_mock = MagicMock()
        self_mock._room_list.isVisible.return_value = True
        ChatHeaderMixin._on_header_sidebar_toggle(self_mock)
        self_mock._room_list.setVisible.assert_called_once_with(False)

    def test_on_header_sidebar_toggle_shows_when_hidden(self) -> None:
        from app.ui._chat_header_mixin import ChatHeaderMixin

        self_mock = MagicMock()
        self_mock._room_list.isVisible.return_value = False
        ChatHeaderMixin._on_header_sidebar_toggle(self_mock)
        self_mock._room_list.setVisible.assert_called_once_with(True)

    def test_on_header_search_focuses_chat_list_panel(self) -> None:
        from app.ui._chat_header_mixin import ChatHeaderMixin

        self_mock = MagicMock()
        ChatHeaderMixin._on_header_search(self_mock)
        self_mock._chat_list_panel._search_edit.setFocus.assert_called_once()
        self_mock._chat_list_panel._search_edit.selectAll.assert_called_once()


class TestChatHelperMixin:
    def test_kind_room_local_saved(self) -> None:
        from app.ui._chat_helper_mixin import ChatHelperMixin

        self_mock = MagicMock()
        self_mock._current_user_id = 5
        # 한글 주석 — saved = self_id * 100 + 1 → 5*100 + 1 = 501
        result = ChatHelperMixin._kind_room_local(self_mock, "saved", 0)
        assert result == 501

    def test_kind_room_local_bot(self) -> None:
        from app.ui._chat_helper_mixin import ChatHelperMixin

        self_mock = MagicMock()
        self_mock._current_user_id = 5
        # 한글 주석 — bot = self_id * 10 + 2 → 52
        result = ChatHelperMixin._kind_room_local(self_mock, "bot", 0)
        assert result == 52

    def test_kind_room_local_friend(self) -> None:
        from app.ui._chat_helper_mixin import ChatHelperMixin

        self_mock = MagicMock()
        self_mock._current_user_id = 5
        # 한글 주석 — friend = target_id * 100 + 3 → 20*100 + 3 = 2003
        result = ChatHelperMixin._kind_room_local(self_mock, "friend", 20)
        assert result == 2003

    def test_kind_room_local_other_fallback(self) -> None:
        from app.ui._chat_helper_mixin import ChatHelperMixin

        self_mock = MagicMock()
        self_mock._current_user_id = 5
        # 한글 주석 — unknown kind = target_id * 100 + 9
        result = ChatHelperMixin._kind_room_local(self_mock, "unknown", 30)
        assert result == 3009

    def test_kind_room_local_none_user_id_fallback_1(self) -> None:
        # 한글 주석 — _current_user_id None → 1 fallback
        from app.ui._chat_helper_mixin import ChatHelperMixin

        self_mock = MagicMock()
        self_mock._current_user_id = None
        # saved = 1 * 100 + 1
        result = ChatHelperMixin._kind_room_local(self_mock, "saved", 0)
        assert result == 101


class TestDialogCenterMixin:
    def test_module_imports(self) -> None:
        # 한글 주석 — DialogCenterMixin actual instantiation = PyQt6 widget 필수
        # 단 module import + class existence verify 만 isolated path
        from app.ui._dialog_center_mixin import DialogCenterMixin

        assert hasattr(DialogCenterMixin, "_exec_dialog_centered")
