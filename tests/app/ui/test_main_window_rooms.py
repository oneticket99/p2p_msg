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

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

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

    def test_on_channel_created_fallback_kind_channel(self, main_window) -> None:
        # 한글 주석 — cycle 169.852: auth 부재 main_window → channel placeholder fallback.
        # 서버 room 승격(kind="channel", 0019)은 auth+loop 시점, headless 는 kind=channel 음수 cid.
        _seed_friends(main_window, [(101, "민지")])
        main_window._on_channel_created("공지 채널", "설명", [101])
        entries = main_window._chat_list_panel._entries
        channel_entries = [e for e in entries if e.kind == "channel"]
        assert len(channel_entries) == 1
        assert channel_entries[0].name == "공지 채널"
        assert channel_entries[0].target_id < 0  # placeholder 음수 cid

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

        # 한글 주석: cycle 169.845 M5 — RoomListWidget(_room_list) 회수 완료. _rooms_cache 가
        # 유일 source-of-truth. cache 에 room 주입 시 ChatListPanel 에 kind=room entry 출현.
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

    def test_room_enters_unified_chat_view(self, main_window) -> None:
        """`_on_chat_selected("room")` → 통합 ChatView(idx 0) 진입 + room context 설정."""

        # 한글 주석: cycle 169.845 M5 — legacy GroupChatView 진입 핸들러(_on_room_entered)
        # 물리 회수 확인. room 은 통합 ChatView(idx 0) 단일 경로로만 진입.
        assert not hasattr(main_window, "_on_room_entered")

        main_window._on_chat_selected("room", 42)

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


# ----------------------------------------------------------------------
# TestUnifiedRoomSend — cycle 169.847 M6 (통합 room 송신 mesh + REST coverage)
# ----------------------------------------------------------------------


def _run_send(window, text: str) -> None:
    """running event loop 안 `_on_send_clicked` 구동 helper.

    `_on_send_clicked` 의 mesh `broadcast_payload` + REST `_post_and_resolve` 는
    `asyncio.ensure_future` 로 schedule 된다. running loop 부재 시 첫 ensure_future
    (mesh) 가 RuntimeError → except 점프로 뒤 REST 분기가 통째로 skip 되므로, 실
    event loop 안에서 구동 + `sleep(0)` drain 으로 scheduled task 를 await 완료한다.
    """

    async def _drive() -> None:
        window._input_edit.setPlainText(text)
        window._on_send_clicked()
        # 한글 주석 — ensure_future 로 schedule 된 mesh/REST task drain (다중 yield 안전망)
        for _ in range(3):
            await asyncio.sleep(0)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_drive())
    finally:
        loop.close()


class TestUnifiedRoomSend:
    """cycle 169.847 M6 — room 송신이 통합 `_on_send_clicked` 경로(mesh
    `broadcast_payload` + REST `_post_and_resolve`)로 수렴했는지 검증.

    M5 가 삭제한 obsolete legacy test(`test_main_window_messages.py` +
    `test_group_message_dual_chain.py` — removed `_dispatch_message_chain`/
    `_on_group_message_send` 전용)의 등가 coverage 를 통합 송신 경로로 재작성한다
    (Exec Plan M6, DoD D7). ACK chain 단위 검증은 `test_mesh_manager.py:181` 잔존.
    """

    def _inject_send_mocks(self, main_window):
        """mesh / messages_client / _post_and_resolve mock 주입 + mesh 반환."""

        mesh = MagicMock(name="MeshManager")
        # 한글 주석 — broadcast_payload 는 awaitable 의무 (ensure_future schedule)
        mesh.broadcast_payload = AsyncMock(name="broadcast_payload")
        main_window._mesh_manager = mesh
        main_window._messages_client = MagicMock(name="MessagesClient")
        # 한글 주석 — REST POST chain 은 bound coroutine method → AsyncMock 대체
        main_window._post_and_resolve = AsyncMock(name="post_and_resolve")
        return mesh

    def test_room_send_broadcasts_via_mesh(self, main_window) -> None:
        """room 진입 후 송신 → `mesh.broadcast_payload(payload)` 1회 await (payload 정합)."""

        mesh = self._inject_send_mocks(main_window)
        main_window._on_chat_selected("room", 42)

        _run_send(main_window, "안녕 단톡방")

        mesh.broadcast_payload.assert_awaited_once()
        payload = mesh.broadcast_payload.await_args.args[0]
        assert payload.text == "안녕 단톡방"
        assert payload.sender == main_window._config.user_nickname

    def test_room_send_posts_rest_with_room_id(self, main_window) -> None:
        """room 송신 → `_post_and_resolve(msg_client, _current_room_id=42, text, uuid)` REST."""

        self._inject_send_mocks(main_window)
        main_window._on_chat_selected("room", 42)

        _run_send(main_window, "REST 검증")

        main_window._post_and_resolve.assert_awaited_once()
        args = main_window._post_and_resolve.await_args.args
        # args = (msg_client, current_room, text, client_uuid)
        assert args[1] == 42  # current_room = _current_room_id (M4 설정)
        assert args[2] == "REST 검증"
        # client_uuid = mesh payload.id 와 동일 uuid (bubble mapping 계약)
        assert isinstance(args[3], str) and args[3]

    def test_room_send_renders_local_bubble_with_sender_label(
        self, main_window
    ) -> None:
        """room 송신 → 통합 ChatView `add_message` (room = `hide_sender=False`, sender 라벨 유지)."""

        self._inject_send_mocks(main_window)
        main_window._on_chat_selected("room", 42)
        # add_message spy (진입 직후 — 송신 echo 만 포착)
        main_window._chat_view.add_message = MagicMock(name="add_message")

        _run_send(main_window, "버블 렌더")

        main_window._chat_view.add_message.assert_called()
        kwargs = main_window._chat_view.add_message.call_args.kwargs
        # room = 1:1 아님 → sender label 유지 (friend/bot/saved 만 suppress)
        assert kwargs.get("hide_sender") is False
        assert kwargs.get("is_self") is True
        assert kwargs.get("text") == "버블 렌더"

    def test_empty_text_no_mesh_no_rest(self, main_window) -> None:
        """공백 입력 → mesh/REST 미호출 (early return 회귀 안전망)."""

        mesh = self._inject_send_mocks(main_window)
        main_window._on_chat_selected("room", 42)

        _run_send(main_window, "   ")

        mesh.broadcast_payload.assert_not_awaited()
        main_window._post_and_resolve.assert_not_awaited()
