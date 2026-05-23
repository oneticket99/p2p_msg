# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 144 — friend_list + add_friend_dialog 의 pytest 5 PASS.

본 test 의 2 widget 커버:

- TestFriendList : 3 (empty placeholder + pending incoming 수락 버튼 +
  accepted 채팅+삭제 버튼)
- TestAddFriendDialog : 2 (검색 결과 목록 표시 + friend_requested 시그널 emit)

PyQt6 graceful — headless 환경 의 QApplication fixture 의무.
"""

from __future__ import annotations

import os
import sys

import pytest

# headless 환경 변수 설정 — Qt offscreen platform 강제 (macOS/Linux CI 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — headless 정합."""

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


# ─── TestFriendList ─────────────────────────────────────────────────────────


class TestFriendList:
    """FriendListWidget 의 empty + pending incoming + accepted 행 표기."""

    def test_empty_shows_placeholder(self, qapp) -> None:
        """친구 목록 비어있을 때 row count 0 (cycle 169.100 회수 — placeholder 폐기)."""

        from app.ui.friend_list import FriendListWidget

        widget = FriendListWidget()
        widget.set_friends([], viewer_id=42)

        # 한글 주석 — cycle 169.603: cycle 169.100 안 placeholder 폐기 정합 (사용자 directive — 플레이스홀더 없이 전부 구현).
        assert widget.count() == 0
        assert widget.friend_count() == 0

    def test_pending_incoming_shows_accept_reject(self, qapp) -> None:
        """수신 pending 행 = 수락 + 거절 버튼 활성."""

        from app.ui.friend_list import FriendItem, FriendListWidget

        widget = FriendListWidget()
        widget.set_friends(
            [
                FriendItem(
                    user_id=99,
                    friend_user_id=42,
                    friend_username="alice",
                    status="pending",
                    is_incoming=True,
                )
            ],
            viewer_id=42,
        )

        assert widget.count() == 1
        # 한글 주석: setItemWidget 으로 주입된 _FriendRow 안 의 버튼 검증.
        item = widget.item(0)
        row_widget = widget.itemWidget(item)
        assert row_widget.accept_button is not None
        assert row_widget.reject_button is not None
        assert row_widget.chat_button is None

    def test_accepted_shows_chat_and_remove(self, qapp) -> None:
        """accepted 행 = 채팅 + 삭제 버튼 활성."""

        from app.ui.friend_list import FriendItem, FriendListWidget

        widget = FriendListWidget()
        widget.set_friends(
            [
                FriendItem(
                    user_id=42,
                    friend_user_id=99,
                    friend_username="bob",
                    status="accepted",
                    is_incoming=False,
                )
            ],
            viewer_id=42,
        )

        item = widget.item(0)
        row_widget = widget.itemWidget(item)
        assert row_widget.chat_button is not None
        assert row_widget.remove_button is not None
        assert row_widget.accept_button is None


# ─── TestAddFriendDialog ────────────────────────────────────────────────────


class TestAddFriendDialog:
    """AddFriendDialog 의 검색 결과 + 친구 요청 시그널 emit."""

    def test_set_search_results_populates_list(self, qapp) -> None:
        """set_search_results 의 list 갱신 + ChatListEntry delegate paint payload."""

        from app.ui.add_friend_dialog import AddFriendDialog, SearchResult
        from PyQt6.QtCore import Qt

        dlg = AddFriendDialog()
        dlg.set_search_results(
            [
                SearchResult(user_id=99, username="alice", email_verified=True),
                SearchResult(user_id=100, username="bob", email_verified=False),
            ]
        )

        # 한글 주석 — cycle 169.603: cycle 169.495 ChatListEntry delegate paint pattern 정합.
        # item.text() 자체는 빈 string — UserRole+2 안 ChatListEntry stash.
        assert dlg._result_list.count() == 2
        entry_alice = dlg._result_list.item(0).data(Qt.ItemDataRole.UserRole + 2)
        entry_bob = dlg._result_list.item(1).data(Qt.ItemDataRole.UserRole + 2)
        assert entry_alice.name == "alice"
        assert "✓" in entry_alice.last_message
        assert entry_bob.name == "bob"
        assert "✓" not in entry_bob.last_message

    def test_friend_requested_signal_emit(self, qapp) -> None:
        """결과 선택 + 친구 추가 버튼 — friend_requested 시그널 emit."""

        from app.ui.add_friend_dialog import AddFriendDialog, SearchResult

        dlg = AddFriendDialog()
        dlg.set_search_results(
            [SearchResult(user_id=99, username="alice", email_verified=True)]
        )
        dlg._result_list.setCurrentRow(0)
        dlg._nickname_edit.setText("앨리스")

        captured: list[tuple[int, str]] = []
        dlg.friend_requested.connect(
            lambda uid, nick: captured.append((uid, nick))
        )

        dlg._on_request_clicked()

        assert captured == [(99, "앨리스")]
