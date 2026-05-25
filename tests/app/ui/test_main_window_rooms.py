# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 169.839 — 그룹 생성 flow 재구성 의 pytest 6 PASS.

cycle 169.838 의 "방 입장"(room_id 직접 입력) 전수 제거 정합. 그룹방 진입은
방번호 입력(`room_entered.emit`)이 아니라 "그룹 만들기" wizard + 멤버 초대
chain 으로만 이뤄진다. 통합 ChatView (StackedWidget idx 0) 가 canonical 위젯이며
구 GroupChatView(idx 1) + `room_entered` 경로는 legacy 폐기.

본 test 의 커버 영역:

- 좌측 ChatListPanel 존재 + 초기 direct ChatView (idx 0) default
- NewGroupDialog Step1 그룹명 필수 → Step2 참가자 추가 전환
- NewGroupDialog 친구 select toggle + group_created(name, ids) emit payload
- `_on_group_created` → ChatListEntry kind=group 상단 insert + direct view 진입
- `_on_drawer_new_group` → NewGroupDialog open (offscreen non-blocking 가드)
- 전 wizard chain — 그룹 만들기 → 참가자 선택 → 생성 → direct view 진입

RoomsClient mock 의 의무 — 실 HTTP 호출 차단. PyQt6 graceful 의 headless
QApplication fixture 의 의무.
"""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

import pytest

# headless 환경 강제 — QT_QPA_PLATFORM offscreen
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# PyQt6 부재 시 본 module 전체 skip — graceful collection
pytest.importorskip("PyQt6")

from PyQt6.QtWidgets import QApplication  # noqa: E402

from app.core.app_state import AppState  # noqa: E402
from app.core.config import load_config  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication 인스턴스 — headless 정합."""

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def config():
    """``.env`` 기반 Config 인스턴스 — sound_signature_path 등 의무 필드 채움."""

    return load_config()


@pytest.fixture
def app_state_reset():
    """AppState singleton 의 테스트 격리 — room_id/peer_id 의 clear_identity."""

    state = AppState.instance()
    state.clear_identity()
    yield state
    state.clear_identity()


@pytest.fixture
def main_window(qapp, config, app_state_reset):
    """RoomsClient mock 주입 의 MainWindow 인스턴스.

    실 HTTP 호출 차단 의무 — rooms_client = MagicMock 의 graceful dummy.
    """

    # 한글 주석 — 본 fixture 안 lazy import 로 PyQt6 graceful 정합.
    from app.ui.main_window import MainWindow

    auth_mock = MagicMock(name="AuthClient")
    rooms_mock = MagicMock(name="RoomsClient")

    window = MainWindow(
        config=config,
        auth_client=auth_mock,
        rooms_client=rooms_mock,
    )
    yield window
    window.close()
    window.deleteLater()


def _seed_friends(main_window, friends: list[tuple[int, str]]) -> None:
    """ChatListPanel 에 friend kind entry 주입 — wizard 친구 list 의 source."""

    from datetime import datetime

    from app.ui.chat_list_panel import ChatListEntry

    entries = [
        ChatListEntry(
            kind="friend",
            target_id=uid,
            name=name,
            last_message="",
            last_ts=datetime.now(),
            unread_count=0,
            is_pinned=False,
            is_online=True,
        )
        for uid, name in friends
    ]
    main_window._chat_list_panel.set_entries(entries)


# ----------------------------------------------------------------------
# TestGroupCreationFlow — 6 PASS
# ----------------------------------------------------------------------


class TestGroupCreationFlow:
    """cycle 169.839 의 그룹 생성 wizard chain 6 행위 검증."""

    def test_chat_list_panel_present_with_direct_view_default(
        self, main_window
    ) -> None:
        """좌측 ChatListPanel 존재 + 초기 direct ChatView (idx 0) default."""

        from app.ui.chat_list_panel import ChatListPanel
        from app.ui.chat_view import ChatView

        # 좌측 sidebar = ChatListPanel (방번호 입력 RoomList 폐기)
        assert isinstance(main_window._chat_list_panel, ChatListPanel)
        # 초기 StackedWidget = direct ChatView 페이지 (idx 0)
        assert main_window._stacked.currentIndex() == main_window._STACK_DIRECT_CHAT
        assert isinstance(main_window._chat_view, ChatView)
        # 입력 영역 visible (direct chat default)
        assert not main_window._input_container.isHidden()

    def test_new_group_dialog_step1_requires_name(self, qapp) -> None:
        """NewGroupDialog Step1 그룹명 필수 → 입력 후 Step2 참가자 추가 전환."""

        from app.ui.new_group_dialog import NewGroupDialog

        dialog = NewGroupDialog(friends=[{"target_id": 1, "name": "민지"}])
        # 초기 Step1 (idx 0)
        assert dialog._stack.currentIndex() == 0
        # 그룹명 공백 시 다음 차단 — Step1 잔존
        dialog._name_edit.setText("   ")
        dialog._on_next()
        assert dialog._stack.currentIndex() == 0
        # 그룹명 입력 후 Step2 (idx 1) 전환
        dialog._name_edit.setText("주말 등산팀")
        dialog._on_next()
        assert dialog._stack.currentIndex() == 1
        dialog.deleteLater()

    def test_new_group_dialog_friend_select_and_emit(self, qapp) -> None:
        """친구 select toggle + group_created(name, ids) emit payload 검증."""

        from app.ui.new_group_dialog import NewGroupDialog

        friends = [
            {"target_id": 101, "name": "민지"},
            {"target_id": 102, "name": "현우"},
        ]
        dialog = NewGroupDialog(friends=friends)

        captured: list[tuple[str, list]] = []
        dialog.group_created.connect(
            lambda name, ids: captured.append((name, list(ids)))
        )

        # 친구 2명 select (item 0, 1)
        dialog._on_friend_click(dialog._friend_list.item(0))
        dialog._on_friend_click(dialog._friend_list.item(1))
        assert dialog._selected_ids == [101, 102]
        # 1명 재클릭 = toggle off
        dialog._on_friend_click(dialog._friend_list.item(1))
        assert dialog._selected_ids == [101]

        # 그룹명 + 만들기 → group_created emit
        dialog._name_edit.setText("점심팟")
        dialog._on_create()
        assert captured == [("점심팟", [101])]
        dialog.deleteLater()

    def test_on_group_created_inserts_entry_and_enters_direct_view(
        self, main_window
    ) -> None:
        """`_on_group_created` → ChatListEntry kind=group 상단 insert + direct view 진입."""

        # 사전 친구 entry 1건 주입 (insert 후 상단 정렬 검증용)
        _seed_friends(main_window, [(101, "민지")])

        main_window._on_group_created("팀 회의방", [101])

        entries = main_window._chat_list_panel._entries
        # 신규 group entry 보유 + kind=group + 음수 gid
        group_entries = [e for e in entries if e.kind == "group"]
        assert len(group_entries) == 1
        assert group_entries[0].name == "팀 회의방"
        assert group_entries[0].target_id < 0
        # 생성 직후 direct ChatView (idx 0) 진입 + 입력 영역 visible
        # (window 미표시 offscreen 환경 — isVisible 대신 isHidden 부정 검증)
        assert main_window._stacked.currentIndex() == main_window._STACK_DIRECT_CHAT
        assert not main_window._input_container.isHidden()

    def test_drawer_new_group_opens_dialog_offscreen_safe(
        self, main_window
    ) -> None:
        """`_on_drawer_new_group` → NewGroupDialog open (offscreen non-blocking 가드)."""

        from app.ui.new_group_dialog import NewGroupDialog

        # 친구 2건 주입 → wizard 친구 list source
        _seed_friends(main_window, [(101, "민지"), (102, "현우")])

        # 그룹 만들기 trigger — offscreen 가드로 즉시 반환 (hang 부재)
        main_window._on_drawer_new_group()

        # child NewGroupDialog 인스턴스 생성 + 친구 2명 populate
        dialog = main_window.findChild(NewGroupDialog)
        assert dialog is not None
        assert dialog._friend_list.count() == 2
        dialog.deleteLater()

    def test_full_wizard_chain_create_to_entry(self, main_window) -> None:
        """전 wizard chain — 그룹 만들기 → 참가자 선택 → 생성 → direct view 진입."""

        from app.ui.new_group_dialog import NewGroupDialog

        _seed_friends(main_window, [(101, "민지"), (102, "현우")])

        # 1) 그룹 만들기 wizard open
        main_window._on_drawer_new_group()
        dialog = main_window.findChild(NewGroupDialog)
        assert dialog is not None

        # 2) 그룹명 입력 + 참가자 선택
        dialog._name_edit.setText("동아리방")
        dialog._on_friend_click(dialog._friend_list.item(0))
        dialog._on_friend_click(dialog._friend_list.item(1))

        # 3) 만들기 → group_created → _on_group_created chain
        dialog._on_create()

        # 4) ChatListEntry kind=group insert + direct view (idx 0) 진입
        group_entries = [
            e for e in main_window._chat_list_panel._entries if e.kind == "group"
        ]
        assert len(group_entries) == 1
        assert group_entries[0].name == "동아리방"
        assert main_window._stacked.currentIndex() == main_window._STACK_DIRECT_CHAT
        assert not main_window._input_container.isHidden()


# ----------------------------------------------------------------------
# TestRoomCacheMigration — cycle 169.843 M3 (room 적재 source-of-truth 이전)
# ----------------------------------------------------------------------


class TestRoomCacheMigration:
    """로그인 시 room 적재의 source-of-truth 가 `_room_list._rooms` → `_rooms_cache` 로
    이전됐는지 검증. `_refresh_chat_list_panel` 가 `_rooms_cache` 를 읽어 kind=room
    ChatListEntry 를 만든다 (RoomListWidget 비참조 정합, DoD D4).
    """

    def test_refresh_reads_rooms_from_cache_not_room_list(self, main_window) -> None:
        """`_refresh_chat_list_panel` 가 `_room_list._rooms` 가 아닌 `_rooms_cache` 를 읽는다."""

        from types import SimpleNamespace

        # 한글 주석: _room_list._rooms 는 비우고 _rooms_cache 에만 room 주입 →
        # ChatListPanel 에 kind=room entry 가 나타나면 reader 가 cache 를 읽는 증거.
        main_window._room_list.set_rooms([])
        main_window._rooms_cache = [
            SimpleNamespace(room_id=501, name="개발팀 공지방"),
        ]

        main_window._refresh_chat_list_panel()

        room_entries = [
            e for e in main_window._chat_list_panel._entries if e.kind == "room"
        ]
        assert len(room_entries) == 1
        assert room_entries[0].target_id == 501
        assert room_entries[0].name == "개발팀 공지방"

    def test_empty_cache_yields_no_room_entry(self, main_window) -> None:
        """`_rooms_cache` 가 비면 kind=room entry 미생성 (회귀 안전망)."""

        main_window._rooms_cache = []
        main_window._refresh_chat_list_panel()

        room_entries = [
            e for e in main_window._chat_list_panel._entries if e.kind == "room"
        ]
        assert room_entries == []


# ----------------------------------------------------------------------
# TestRoomUnifiedEntry — cycle 169.844 M4 (kind=room 통합 ChatView 진입)
# ----------------------------------------------------------------------


class TestRoomUnifiedEntry:
    """서버 room (kind=room) 진입이 legacy GroupChatView(idx 1) → 통합 ChatView(idx 0)
    로 통일됐는지 검증. `_on_chat_selected("room")` 가 `_on_room_entered` 를 호출하지
    않고 통합 진입 분기를 타며, 통합 송신/멤버 보기에 필요한 room context 를 설정한다
    (DoD D5/D6).
    """

    def test_room_enters_unified_chat_view_not_group_chat_view(
        self, main_window
    ) -> None:
        """`_on_chat_selected("room")` → idx 0 진입 + `_on_room_entered` 미호출."""

        from unittest.mock import patch as _patch

        # 한글 주석: legacy GroupChatView 진입 핸들러가 호출되지 않아야 함 (통합 진입)
        with _patch.object(main_window, "_on_room_entered") as spy:
            main_window._on_chat_selected("room", 42)

        spy.assert_not_called()
        # 통합 ChatView (idx 0) 진입 + room context 설정 + 입력 영역 visible
        assert main_window._stacked.currentIndex() == main_window._STACK_DIRECT_CHAT
        assert main_window._current_room_id == 42
        assert main_window._active_chat_kind == "room"
        assert not main_window._input_container.isHidden()

    def test_room_member_view_functional_after_unified_entry(
        self, main_window
    ) -> None:
        """room 통합 진입 후 멤버 보기가 동작한다 (`_current_room_id` None 가드 통과)."""

        # 한글 주석: room 진입 → _current_room_id 설정 → _on_open_members_panel 이
        # early return 하지 않고 in-app 모달(_members_dialog) 생성.
        main_window._on_chat_selected("room", 42)
        main_window._on_open_members_panel()

        dlg = getattr(main_window, "_members_dialog", None)
        assert dlg is not None
        from app.ui.member_list import MemberListWidget
        lst = dlg.findChild(MemberListWidget)
        assert lst is not None
        # self peer (방장) 최소 1명
        assert lst.member_count() >= 1
        dlg.close()
