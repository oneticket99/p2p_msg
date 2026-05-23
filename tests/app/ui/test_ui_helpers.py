# SPDX-License-Identifier: GPL-3.0-or-later
"""UI helper 4 isolated unit — cycle 169.720 신설.

HttpJsonWorker + ChatListEntry + FileProgressWidget + ChatListItemDelegate.
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


class TestHttpJsonWorker:
    def test_url_composition(self, qapp) -> None:
        from app.ui._http_worker import HttpJsonWorker

        w = HttpJsonWorker("https://api.local/", "/api/x", {"k": "v"})
        assert w._url == "https://api.local/api/x"
        assert w._payload == {"k": "v"}

    def test_multi_slash_normalized(self, qapp) -> None:
        from app.ui._http_worker import HttpJsonWorker

        w = HttpJsonWorker("https://api.local//", "/api/x", {})
        assert w._url == "https://api.local/api/x"


class TestChatListEntry:
    def test_default_fields(self) -> None:
        from app.ui.chat_list_panel import ChatListEntry

        e = ChatListEntry(kind="friend", target_id=10, name="Alice")
        assert e.kind == "friend"
        assert e.target_id == 10
        assert e.last_message == ""
        assert e.unread_count == 0
        assert e.is_pinned is False

    def test_mutable_unread_count(self) -> None:
        # 한글 주석 — cycle 169.437 frozen 폐기 → mutation 허용
        from app.ui.chat_list_panel import ChatListEntry

        e = ChatListEntry(kind="friend", target_id=10, name="Alice")
        e.unread_count = 5
        assert e.unread_count == 5

    def test_folder_color_default_empty(self) -> None:
        from app.ui.chat_list_panel import ChatListEntry

        e = ChatListEntry(kind="bot", target_id=20, name="Helper")
        assert e.folder_color == ""

    def test_three_kinds(self) -> None:
        from app.ui.chat_list_panel import ChatListEntry

        for kind in ("friend", "room", "bot"):
            e = ChatListEntry(kind=kind, target_id=1, name="X")
            assert e.kind == kind


class TestChatListItemDelegate:
    def test_constants(self) -> None:
        from app.ui.chat_list_panel import ChatListItemDelegate

        assert ChatListItemDelegate.AVATAR_SIZE == 54
        assert ChatListItemDelegate.ROW_HEIGHT == 72
        assert ChatListItemDelegate.PADDING == 14


class TestFileProgressWidget:
    def test_valid_construct_send(self, qapp) -> None:
        from app.ui.file_progress_widget import FileProgressWidget

        w = FileProgressWidget(
            file_id="abc", name="x.txt", size=1024, role="send",
        )
        assert w is not None
        w.close()

    def test_valid_construct_recv(self, qapp) -> None:
        from app.ui.file_progress_widget import FileProgressWidget

        w = FileProgressWidget(
            file_id="abc", name="x.txt", size=1024, role="recv",
        )
        assert w is not None
        w.close()

    def test_invalid_role_raises(self, qapp) -> None:
        from app.ui.file_progress_widget import FileProgressWidget

        with pytest.raises(ValueError, match="role"):
            FileProgressWidget(
                file_id="abc", name="x.txt", size=1024, role="bogus",
            )

    def test_zero_size_raises(self, qapp) -> None:
        from app.ui.file_progress_widget import FileProgressWidget

        with pytest.raises(ValueError, match="size"):
            FileProgressWidget(
                file_id="abc", name="x.txt", size=0, role="send",
            )

    def test_negative_size_raises(self, qapp) -> None:
        from app.ui.file_progress_widget import FileProgressWidget

        with pytest.raises(ValueError, match="size"):
            FileProgressWidget(
                file_id="abc", name="x.txt", size=-1, role="send",
            )
