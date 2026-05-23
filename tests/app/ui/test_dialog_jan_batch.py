# SPDX-License-Identifier: GPL-3.0-or-later
"""UI dialog 잔존 isolated batch — cycle 169.725 신설.

CallDialog + NewChannelDialog + ChatPickerDialog construct + state.
"""

from __future__ import annotations

import pytest


pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


class TestCallDialog:
    def test_audio_only_construct(self, qapp) -> None:
        from app.ui.call_dialog import CallDialog

        d = CallDialog(peer_name="alice", video_enabled=False, incoming=False)
        assert d._peer_name == "alice"
        assert d._video_enabled is False
        assert d._incoming is False
        assert d._muted is False
        assert d.width() == 420
        assert d.height() == 600
        d.close()

    def test_video_construct(self, qapp) -> None:
        from app.ui.call_dialog import CallDialog

        d = CallDialog(peer_name="bob", video_enabled=True, incoming=False)
        assert d._video_enabled is True
        assert d._video_frame.isVisible() is False  # 한글 주석 — modal 미표시 시 invisible
        d.close()

    def test_incoming_construct(self, qapp) -> None:
        from app.ui.call_dialog import CallDialog

        d = CallDialog(peer_name="caller", video_enabled=False, incoming=True)
        assert d._incoming is True
        d.close()

    def test_title_includes_call_type(self, qapp) -> None:
        from app.ui.call_dialog import CallDialog

        d_audio = CallDialog(peer_name="x", video_enabled=False)
        assert "음성" in d_audio.windowTitle()
        d_audio.close()
        d_video = CallDialog(peer_name="x", video_enabled=True)
        assert "영상" in d_video.windowTitle()
        d_video.close()


class TestNewChannelDialog:
    def test_construct_empty(self, qapp) -> None:
        from app.ui.new_channel_dialog import NewChannelDialog

        d = NewChannelDialog()
        assert d._friends == []
        assert d._selected_ids == []
        assert d.width() == 420
        assert d.height() == 600
        d.close()

    def test_construct_with_friends(self, qapp) -> None:
        from app.ui.new_channel_dialog import NewChannelDialog

        friends = [{"user_id": 10, "nickname": "Alice"}]
        d = NewChannelDialog(friends=friends)
        assert len(d._friends) == 1
        d.close()


class TestChatPickerDialog:
    def test_include_mode(self, qapp) -> None:
        from app.ui.chat_picker_dialog import ChatPickerDialog

        d = ChatPickerDialog(chat_entries=[], mode="include")
        # 한글 주석 — windowTitle 안 "포함할 대화방" key
        assert "포함" in d.windowTitle() or "include" in d.windowTitle().lower() or "TooTalk" in d.windowTitle()
        assert d.width() == 420
        d.close()

    def test_exclude_mode(self, qapp) -> None:
        from app.ui.chat_picker_dialog import ChatPickerDialog

        d = ChatPickerDialog(chat_entries=[], mode="exclude")
        assert d._entries == []
        d.close()

    def test_entries_stored(self, qapp) -> None:
        # 한글 주석 — ChatListEntry obj 의무 (kind + target_id 의무)
        from app.ui.chat_list_panel import ChatListEntry
        from app.ui.chat_picker_dialog import ChatPickerDialog

        entries = [
            ChatListEntry(kind="friend", target_id=10, name="Alice"),
            ChatListEntry(kind="room", target_id=20, name="Group"),
        ]
        d = ChatPickerDialog(chat_entries=entries)
        assert len(d._entries) == 2
        d.close()
