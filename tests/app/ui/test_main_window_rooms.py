# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 139 — main_window 의 그룹 채팅 통합 의 pytest 5 PASS.

본 test 의 커버 영역:

- RoomList sidebar 의 존재 + 빈 placeholder 의 초기 상태
- RoomList 의 room_entered 시그널 emit 시 GroupChatView swap + 1:1 입력 차단
- 그룹 채팅 모드 active 일 때 1:1 보내기 슬롯 의 차단 검증
- members_panel_requested 시그널 의 MemberList swap
- "직접 메시지" 액션 의 1:1 ChatView 회귀 (backward compat)

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

    실 HTTP 호출 차단 의무 — rooms_client = MagicMock 의 의 graceful 의 dummy.
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


# ----------------------------------------------------------------------
# TestMainWindowRoomsIntegration — 5 PASS
# ----------------------------------------------------------------------


class TestMainWindowRoomsIntegration:
    """cycle 139 의 그룹 채팅 통합 5 행위 검증."""

    def test_sidebar_room_list_present_with_empty_placeholder(
        self, main_window
    ) -> None:
        """좌측 sidebar RoomListWidget 의 존재 + 빈 placeholder 행 표기."""

        from app.ui.room_list import RoomListWidget

        # RoomListWidget 인스턴스 의 보유 — sidebar 의 의무
        assert isinstance(main_window._room_list, RoomListWidget)
        # 빈 목록 의 placeholder 행 1개
        assert main_window._room_list.count() == 1
        placeholder_item = main_window._room_list.item(0)
        assert "참여" in placeholder_item.text()
        # 초기 StackedWidget = 1:1 ChatView 페이지
        assert main_window._stacked.currentIndex() == 0
        # 1:1 입력 영역 visible (직접 메시지 default) — show 미호출 환경 의
        # isHidden() 검증 (QWidget.setVisible(False) 의 부재 = 기본 visible)
        assert not main_window._input_container.isHidden()

    def test_room_entered_signal_swaps_to_group_chat_view(
        self, main_window
    ) -> None:
        """RoomList 의 room_entered emit 시 GroupChatView swap + 1:1 입력 차단."""

        from app.ui.group_chat_view import GroupChatView

        # room_id=42 의 emit 직접 trigger
        main_window._room_list.room_entered.emit(42)

        # GroupChatView 인스턴스 의 생성 + 보관
        assert main_window._group_chat_view is not None
        assert isinstance(main_window._group_chat_view, GroupChatView)
        assert main_window._group_chat_view.room_id == 42
        # StackedWidget idx = 1 (그룹 채팅 페이지)
        assert main_window._stacked.currentIndex() == 1
        # 1:1 입력 영역 의 비활성 (그룹 모드 의무)
        assert not main_window._input_container.isVisible()
        # AppState 의 room_id 갱신 — str("42")
        assert main_window._state.room_id == "42"
        # _current_room_id getter
        assert main_window._current_room_id == 42

    def test_group_mode_blocks_1on1_send_slot(self, main_window) -> None:
        """그룹 모드 active 일 때 1:1 보내기 슬롯 의 echo 차단."""

        # 그룹 채팅 진입
        main_window._room_list.room_entered.emit(7)
        assert main_window._stacked.currentIndex() == 1
        # 1:1 입력 영역 의 hidden 상태 — 그룹 모드 의 의무
        assert main_window._input_container.isHidden()

        # 1:1 입력창 의 텍스트 주입 + 보내기 호출 — 그룹 모드 의 의무 차단
        # cycle 169.71 회수 — InputBar widget 안 _text_edit QTextEdit 의 의 정합
        main_window._input_bar._text_edit.setPlainText("이 메시지 는 차단 되어야 함")
        main_window._on_send_clicked()

        # ChatView (1:1) message_count 증가 부재 검증 — 초기 1 시스템 안내 만
        # 보존된 텍스트 (clear 호출 부재) 검증
        assert main_window._input_bar._text_edit.toPlainText() == "이 메시지 는 차단 되어야 함"

    def test_members_panel_opens_modal_member_list(self, main_window) -> None:
        """멤버 보기 → 모달 dialog 안 MemberListWidget populate (cycle 169.837)."""

        # cycle 169.837 — StackedWidget 패널 swap → 모달 dialog. 원형 아바타 행 MemberListWidget.
        from app.ui.member_list import MemberListWidget

        # 그룹 채팅 진입 → GroupChatView 인스턴스 보유
        main_window._room_list.room_entered.emit(10)
        view = main_window._group_chat_view
        assert view is not None

        # 멤버 보기 트리거 ("..." 드롭다운 "멤버 보기" 등가 — 동일 핸들러 직접 호출)
        main_window._on_open_members_panel()

        # cycle 169.838 — 멤버 보기 = in-app overlay 모달(_exec_dialog_centered). dialog 인스턴스
        # 보유(self._members_dialog) ref 검증. offscreen 가드가 setParent+show(setModal 아님)라
        # isModal 미검증.
        dlg = getattr(main_window, "_members_dialog", None)
        assert dlg is not None
        # 모달 안 MemberListWidget 의 멤버 수 = 1 (self_peer 방장, known_peers 부재)
        lst = dlg.findChild(MemberListWidget)
        assert lst is not None
        assert lst.member_count() == 1
        dlg.close()

    def test_direct_chat_action_restores_1on1_view(self, main_window) -> None:
        """1:1 ChatView 의 backward compat — "직접 메시지" 액션 의 회귀."""

        from app.ui.chat_view import ChatView

        # 그룹 채팅 진입 → idx=1
        main_window._room_list.room_entered.emit(5)
        assert main_window._stacked.currentIndex() == 1
        assert main_window._input_container.isHidden()

        # 직접 메시지 액션 의 직접 호출
        main_window._on_open_direct_chat()

        # idx = 0 (1:1) + 입력 영역 hidden 해제 회귀
        assert main_window._stacked.currentIndex() == 0
        assert not main_window._input_container.isHidden()
        # 1:1 ChatView 의 instance 보존
        assert isinstance(main_window._chat_view, ChatView)
        # rooms_client mock 의 주입 보존 (backward compat 검증)
        assert main_window._rooms_client is not None
