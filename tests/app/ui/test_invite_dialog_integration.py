# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 147 — InviteDialog ↔ FriendList ↔ rooms_client.invite_user 통합 6 PASS.

cycle 135 (rooms REST 7 endpoint — invite 포함) + cycle 144 (friends REST 6 +
FriendListWidget) + cycle 136 (InviteDialog skeleton) chain 통합 검증.

본 test 의 커버 영역
-------------------
- TestInviteDialogFriendsPopulate : friends 리스트 → dropdown populate
- TestInviteRequestedSignal      : invite_requested payload (room_id, friend_user_id)
- TestRoomsInviteCall            : rooms_client.invite_user mock 호출 검증
- TestFriendsClientGraceful      : httpx 부재 graceful (FriendsClient 인스턴스화 시 RuntimeError)
- TestInviteForbidden403         : owner 만 invite — 403 회수 chain
- TestMemberListRefresh          : invite 성공 후 MemberList 갱신

PyQt6 graceful — headless QT_QPA_PLATFORM=offscreen + QApplication fixture.
실 REST 호출 차단 — friends_client + rooms_client = MagicMock (AsyncMock).
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 한글 주석: headless 환경 강제 — Qt offscreen platform
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석: PyQt6 부재 시 본 module 전체 skip — graceful collection
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
    """AppState singleton 의 테스트 격리 — clear_identity."""

    state = AppState.instance()
    state.clear_identity()
    yield state
    state.clear_identity()


def _make_friend_payload(
    *,
    friend_id: int,
    friend_user_id: int,
    friend_username: str,
    status: str = "accepted",
    nickname=None,
):
    """FriendProfilePayload 인스턴스 — fixture 재사용."""

    from app.net.friends_client import FriendProfilePayload

    return FriendProfilePayload(
        id=friend_id,
        user_id=7,  # viewer
        friend_user_id=friend_user_id,
        friend_username=friend_username,
        status=status,
        nickname=nickname,
        friend_email_verified=True,
    )


def _make_member_payload(*, user_id: int, role: str = "member"):
    """RoomMemberPayload 의 lite stub — duck typing 호환."""

    member = MagicMock(name=f"member_{user_id}")
    member.user_id = user_id
    member.role = role
    member.id = user_id * 10
    member.room_id = 42
    return member


@pytest.fixture
def fake_friends_client():
    """FriendsClient mock — list_friends async 의 accepted 응답."""

    mock = MagicMock(name="FriendsClient")
    mock.list_friends = AsyncMock(
        return_value=[
            _make_friend_payload(
                friend_id=1,
                friend_user_id=99,
                friend_username="alice",
                status="accepted",
                nickname=None,
            ),
            _make_friend_payload(
                friend_id=2,
                friend_user_id=100,
                friend_username="bob",
                status="accepted",
                nickname="bobby",
            ),
        ]
    )
    return mock


@pytest.fixture
def fake_rooms_client():
    """RoomsClient mock — invite_user + get_room async."""

    mock = MagicMock(name="RoomsClient")
    mock.invite_user = AsyncMock(return_value=500)  # 신규 peer_id
    # 한글 주석: get_room 응답 — (room, members) tuple
    fake_room = MagicMock(name="room", id=42, owner_id=7, kind="group")
    mock.get_room = AsyncMock(
        return_value=(
            fake_room,
            [
                _make_member_payload(user_id=7, role="owner"),
                _make_member_payload(user_id=99, role="member"),
            ],
        )
    )
    return mock


@pytest.fixture
def main_window(
    qapp, config, app_state_reset, fake_friends_client, fake_rooms_client
):
    """MainWindow 인스턴스 — friends_client + rooms_client 주입.

    init 단계 의 asyncio.get_running_loop RuntimeError 폴백 → auto-update task
    skip (테스트 격리). invite REST chain 도 동일 폴백 시 graceful skip.
    """

    from app.ui.main_window import MainWindow

    auth_mock = MagicMock(name="AuthClient")

    # 한글 주석: get_running_loop 부재 폴백 → init 단계 update task skip
    with patch(
        "app.ui.main_window.asyncio.get_running_loop",
        side_effect=RuntimeError("no running loop"),
    ):
        window = MainWindow(
            config=config,
            auth_client=auth_mock,
            rooms_client=fake_rooms_client,
            friends_client=fake_friends_client,
        )
    # 한글 주석: 로그인 simulation — viewer PK
    window._current_user_id = 7
    yield window
    window.close()
    window.deleteLater()


# ----------------------------------------------------------------------
# TestInviteDialogFriendsPopulate — set_friends 의 dropdown populate
# ----------------------------------------------------------------------


class TestInviteDialogFriendsPopulate:
    """FriendProfilePayload list → InviteDialog dropdown populate 검증."""

    def test_set_friends_populates_dropdown(self, qapp) -> None:
        """set_friends 의 list 갱신 + dropdown item count + data role."""

        from app.ui.invite_dialog import InviteDialog

        dialog = InviteDialog(room_id=42)
        friends = [
            _make_friend_payload(
                friend_id=1,
                friend_user_id=99,
                friend_username="alice",
            ),
            _make_friend_payload(
                friend_id=2,
                friend_user_id=100,
                friend_username="bob",
                nickname="bobby",
            ),
        ]
        dialog.set_friends(friends)

        # 한글 주석: dropdown 2 항목 + data role 의 user_id 보관 검증.
        assert dialog._combo.count() == 2
        assert dialog._combo.itemData(0) == 99
        assert dialog._combo.itemData(1) == 100
        # 한글 주석: nickname 가용 시 label prefix "bobby (bob)" 표기.
        assert "bobby" in dialog._combo.itemText(1)
        assert "bob" in dialog._combo.itemText(1)
        # 한글 주석: 초대 버튼 활성 + dropdown 활성.
        assert dialog._invite_btn.isEnabled()
        assert dialog._combo.isEnabled()


# ----------------------------------------------------------------------
# TestInviteRequestedSignal — 시그널 payload 검증
# ----------------------------------------------------------------------


class TestInviteRequestedSignal:
    """선택 + 초대 클릭 시 invite_requested(room_id, friend_user_id) emit."""

    def test_invite_requested_emit_payload(self, qapp) -> None:
        """dropdown 선택 + 초대 버튼 → signal emit payload 검증."""

        from app.ui.invite_dialog import InviteDialog

        dialog = InviteDialog(room_id=42)
        dialog.set_friends(
            [
                _make_friend_payload(
                    friend_id=1,
                    friend_user_id=99,
                    friend_username="alice",
                )
            ]
        )

        captured: list = []
        dialog.invite_requested.connect(
            lambda rid, fid: captured.append((rid, fid))
        )

        dialog._combo.setCurrentIndex(0)
        dialog._on_invite_clicked()

        # 한글 주석: 시그널 payload — (room_id=42, friend_user_id=99) 정합.
        assert captured == [(42, 99)]


# ----------------------------------------------------------------------
# TestRoomsInviteCall — rooms_client.invite_user mock 호출 검증
# ----------------------------------------------------------------------


class TestRoomsInviteCall:
    """invite_requested 시그널 → rooms_client.invite_user REST 호출 chain."""

    @pytest.mark.asyncio
    async def test_dispatch_invite_chain_calls_rooms_client(
        self, main_window, fake_rooms_client
    ) -> None:
        """_dispatch_invite_chain → invite_user(42, 99) 의 await 검증."""

        await main_window._dispatch_invite_chain(
            room_id=42, friend_user_id=99
        )

        # 한글 주석: invite_user 1회 호출 + 정확한 인자 정합.
        fake_rooms_client.invite_user.assert_awaited_once_with(42, 99)


# ----------------------------------------------------------------------
# TestFriendsClientGraceful — httpx 부재 graceful
# ----------------------------------------------------------------------


class TestFriendsClientGraceful:
    """httpx 미설치 환경 의 FriendsClient 인스턴스화 → RuntimeError."""

    def test_friends_client_raises_when_httpx_absent(self) -> None:
        """``_HTTPX_AVAILABLE=False`` 시 인스턴스화 단계 RuntimeError."""

        import app.net.friends_client as fc_module

        # 한글 주석: httpx 가용 flag 의 monkeypatch — 인스턴스화 시 raise 검증.
        original = fc_module._HTTPX_AVAILABLE
        fc_module._HTTPX_AVAILABLE = False
        try:
            with pytest.raises(RuntimeError, match="httpx 미설치"):
                fc_module.FriendsClient(
                    base_url="http://demo:8765", token="tok"
                )
        finally:
            fc_module._HTTPX_AVAILABLE = original


# ----------------------------------------------------------------------
# TestInviteForbidden403 — owner 만 invite — 403 회수 chain
# ----------------------------------------------------------------------


class TestInviteForbidden403:
    """owner 만 invite 가능 — 403 응답 시 status bar 안내 + MemberList 갱신 차단."""

    @pytest.mark.asyncio
    async def test_invite_forbidden_skips_member_refresh(
        self, main_window, fake_rooms_client
    ) -> None:
        """invite_user → 403 raise 시 graceful catch + get_room 미호출."""

        from app.net.rooms_client import RoomsForbiddenError

        fake_rooms_client.invite_user = AsyncMock(
            side_effect=RoomsForbiddenError("owner only")
        )

        await main_window._dispatch_invite_chain(
            room_id=42, friend_user_id=99
        )

        # 한글 주석: invite_user 1회 호출 + 403 → get_room 미호출 (graceful skip).
        fake_rooms_client.invite_user.assert_awaited_once_with(42, 99)
        fake_rooms_client.get_room.assert_not_awaited()


# ----------------------------------------------------------------------
# TestMemberListRefresh — invite 성공 후 MemberList 갱신
# ----------------------------------------------------------------------


class TestMemberListRefresh:
    """invite_user 성공 → get_room 재호출 + MemberList.set_members."""

    @pytest.mark.asyncio
    async def test_invite_success_refreshes_member_list(
        self, main_window, fake_rooms_client
    ) -> None:
        """invite_user PASS → get_room 호출 + member_count 갱신."""

        # 한글 주석: 사전 - MemberList 의 초기 빈 상태.
        main_window._member_list.set_members([], viewer_role="member")
        assert main_window._member_list.member_count() == 0

        await main_window._dispatch_invite_chain(
            room_id=42, friend_user_id=99
        )

        # 한글 주석: invite_user + get_room 의 sequence 호출.
        fake_rooms_client.invite_user.assert_awaited_once_with(42, 99)
        fake_rooms_client.get_room.assert_awaited_once_with(42)

        # 한글 주석: MemberList 의 2 행 갱신 — fake_rooms_client.get_room 응답 정합.
        assert main_window._member_list.member_count() == 2
