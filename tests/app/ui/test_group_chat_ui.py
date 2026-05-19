# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 136 — group chat UI 4 widget skeleton 의 pytest 8 PASS.

본 test 의 4 widget 커버:

- TestRoomList : 2 (empty placeholder + populated 행)
- TestGroupChatView : 2 (init member_count + message append)
- TestMemberList : 2 (owner viewer kick 버튼 / member viewer kick 부재)
- TestInviteDialog : 2 (dropdown 항목 + invite 시그널 emit)

PyQt6 graceful — headless 환경 의 QApplication fixture 의 의무. PyQt6
ImportError 시 본 test 의 module level skip.
"""

from __future__ import annotations

import os
import sys

import pytest

# headless 환경 변수 설정 — Qt 의 offscreen platform 강제 (macOS/Linux CI 정합)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# PyQt6 부재 환경 시 본 test 모듈 전체 skip — graceful collection
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402 — 위 importorskip 직후 의무


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — headless 정합.

    PyQt6 의 QApplication 은 프로세스 당 1 개 의무 — 본 fixture 가 기존
    인스턴스를 재사용 (테스트 병렬 / 다른 모듈 의 동시 사용 안전).
    """

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    # 명시 close 미수행 — 다른 module 의 인스턴스 재사용 허용


# ----------------------------------------------------------------------
# TestRoomList — 2 PASS
# ----------------------------------------------------------------------


class TestRoomList:
    """RoomListWidget 의 empty placeholder + populated 행 표기."""

    def test_empty_shows_placeholder_row(self, qapp) -> None:
        """방 목록 비어있을 때 placeholder 행 1개 표시 + 선택 불가."""

        from app.ui.room_list import RoomListWidget

        widget = RoomListWidget()
        widget.set_rooms([])

        # placeholder 행 1개 의무
        assert widget.count() == 1
        item = widget.item(0)
        assert "참여" in item.text()
        # current_room_id 는 None (선택 불가 행)
        assert widget.current_room_id() is None

    def test_populated_rooms_render_with_role_tag(self, qapp) -> None:
        """RoomItem 리스트 주입 시 owner/member role tag + member_count 표기."""

        from app.ui.room_list import RoomItem, RoomListWidget

        widget = RoomListWidget()
        rooms = [
            RoomItem(
                room_id=1,
                room_code="ABCDE",
                title="개발팀",
                role="owner",
                member_count=5,
                unread=3,
            ),
            RoomItem(
                room_id=2,
                room_code="FGHIJ",
                title="",
                role="member",
                member_count=2,
                unread=0,
            ),
        ]
        widget.set_rooms(rooms)

        assert widget.count() == 2
        # owner row 의 star tag + title + member_count + unread 표기
        text0 = widget.item(0).text()
        assert "★" in text0
        assert "개발팀" in text0
        assert "[5]" in text0
        assert "3 신규" in text0

        # member row 의 dot tag + title 폴백 (room_code) + unread 미표기
        text1 = widget.item(1).text()
        assert "·" in text1
        assert "FGHIJ" in text1
        assert "[2]" in text1
        assert "신규" not in text1


# ----------------------------------------------------------------------
# TestGroupChatView — 2 PASS
# ----------------------------------------------------------------------


class TestGroupChatView:
    """GroupChatView 의 init 헤더 + 메시지 append 동작."""

    def test_init_renders_header(self, qapp) -> None:
        """init 시 room_title + member_count 헤더 표기 + room_id getter."""

        from app.ui.group_chat_view import GroupChatView

        view = GroupChatView(
            room_id=42,
            room_title="QA 채널",
            member_count=8,
            self_username="alice",
        )

        assert view.room_id == 42
        assert "QA 채널" in view._title_label.text()
        assert "8" in view._member_count_label.text()

        # set_member_count 갱신 의무
        view.set_member_count(10)
        assert "10" in view._member_count_label.text()

    def test_append_message_inserts_bubble(self, qapp) -> None:
        """append_message 호출 시 stretch 슬롯 직전에 버블 누적."""

        from datetime import datetime

        from app.ui.group_chat_view import GroupChatView

        view = GroupChatView(room_id=1, member_count=2)

        # 초기 상태 = stretch 슬롯 1개 만 (count == 1)
        assert view._messages_layout.count() == 1

        view.append_message(
            sender="bob",
            text="hello",
            ts=datetime(2026, 5, 19, 17, 30),
            is_self=False,
        )
        view.append_message(
            sender="alice",
            text="hi",
            ts=datetime(2026, 5, 19, 17, 31),
            is_self=True,
        )

        # 2 bubble + 1 stretch = 3
        assert view._messages_layout.count() == 3


# ----------------------------------------------------------------------
# TestMemberList — 2 PASS
# ----------------------------------------------------------------------


class TestMemberList:
    """MemberListWidget 의 owner viewer kick 활성 / member viewer kick 부재."""

    def test_owner_viewer_shows_kick_buttons(self, qapp) -> None:
        """viewer_role=owner 시 member 행 의 kick 버튼 표시."""

        from app.ui.member_list import MemberItem, MemberListWidget

        widget = MemberListWidget()
        members = [
            MemberItem(user_id=1, username="alice", role="owner", is_online=True),
            MemberItem(user_id=2, username="bob", role="member", is_online=True),
            MemberItem(user_id=3, username="carol", role="member", is_online=False),
        ]
        widget.set_members(members, viewer_role="owner")

        assert widget.viewer_role() == "owner"
        assert widget.member_count() == 3
        assert widget.count() == 3

        # row 위젯 추출 — bob (idx 1) 의 kick_button 의무 존재
        bob_item = widget.item(1)
        bob_row = widget.itemWidget(bob_item)
        assert bob_row.kick_button is not None

        # alice (owner) 는 kick 버튼 부재 (방장 자신 추방 차단)
        alice_item = widget.item(0)
        alice_row = widget.itemWidget(alice_item)
        assert alice_row.kick_button is None

    def test_member_viewer_no_kick_buttons(self, qapp) -> None:
        """viewer_role=member 시 모든 행 의 kick 버튼 부재."""

        from app.ui.member_list import MemberItem, MemberListWidget

        widget = MemberListWidget()
        members = [
            MemberItem(user_id=1, username="alice", role="owner", is_online=True),
            MemberItem(user_id=2, username="bob", role="member", is_online=True),
        ]
        widget.set_members(members, viewer_role="member")

        assert widget.viewer_role() == "member"

        for idx in range(widget.count()):
            row = widget.itemWidget(widget.item(idx))
            assert row.kick_button is None


# ----------------------------------------------------------------------
# TestInviteDialog — 2 PASS
# ----------------------------------------------------------------------


class TestInviteDialog:
    """InviteDialog 의 dropdown 항목 + invite 시그널 emit."""

    def test_dropdown_populated_from_friends(self, qapp) -> None:
        """friends 리스트 의 username 항목 dropdown 표시 + user_id payload."""

        from app.ui.invite_dialog import FriendOption, InviteDialog

        friends = [
            FriendOption(user_id=10, username="dave"),
            FriendOption(user_id=11, username="eve"),
            FriendOption(user_id=12, username="frank"),
        ]
        dialog = InviteDialog(
            room_id=5, friends=friends, room_title="개발 채널"
        )

        assert dialog.room_id == 5
        assert dialog._combo.count() == 3
        assert dialog._combo.itemText(0) == "dave"
        assert dialog._combo.itemData(0) == 10
        # 초기 선택 = 첫 항목
        assert dialog.selected_friend_id() == 10

    def test_invite_signal_emits_payload(self, qapp) -> None:
        """초대 버튼 클릭 시 invite_requested(room_id, friend_id) emit."""

        from app.ui.invite_dialog import FriendOption, InviteDialog

        friends = [
            FriendOption(user_id=20, username="gina"),
            FriendOption(user_id=21, username="hank"),
        ]
        dialog = InviteDialog(room_id=7, friends=friends)

        # 두 번째 항목 선택
        dialog._combo.setCurrentIndex(1)
        assert dialog.selected_friend_id() == 21

        # signal payload 수집
        captured: list = []
        dialog.invite_requested.connect(
            lambda rid, fid: captured.append((rid, fid))
        )

        # 초대 버튼 직접 trigger (QTest 없이 슬롯 직접 호출 — 동등 효과)
        dialog._on_invite_clicked()

        assert captured == [(7, 21)]
