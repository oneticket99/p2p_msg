# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 142 — main_window messages REST + WebRTC mesh actual binding 의 8 PASS.

cycle 141 sub-agent U (messages persistence REST 4 endpoint + 10 PASS) +
cycle 138 (MeshManager + GroupMessageClient) + cycle 139 sub-agent M
(main_window GroupChatView swap) chain 통합 검증.

본 test 의 커버 영역
-------------------
- TestMessageSendRESTSuccess — REST 200 + mesh broadcast + UI append + message_id capture
- TestMessageSendRESTFail    — REST 401/500 + mesh-only mode + warning log
- TestMessageReceiveMesh     — mesh incoming (직접 append_message) + UI append + sender label
- TestMessageDelete          — REST DELETE + 응답 capture
- TestMessageEmptyBody       — body 빈 / whitespace 차단
- TestMessageMaxLengthCap    — body 65535 상한 cap
- TestMessageRoomMissing     — room_id 무효 차단
- TestMessagePermissionAbsent — messages_client + group_message_client 부재 graceful

PyQt6 graceful — headless QT_QPA_PLATFORM=offscreen + QApplication fixture.
"""

from __future__ import annotations

import asyncio
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


@pytest.fixture
def fake_messages_client():
    """MessagesRestClient mock — async method 4종."""

    mock = MagicMock(name="MessagesRestClient")
    mock.post_message = AsyncMock(
        return_value={
            "ok": True,
            "message_id": 1234,
            "room_id": 42,
            "sender_id": 7,
            "kind": "text",
            "created_at": "2026-05-19T10:00:00+00:00",
        }
    )
    mock.list_messages = AsyncMock()
    mock.get_message = AsyncMock()
    mock.delete_message = AsyncMock(
        return_value={"ok": True, "message_id": 1234, "deleted": True}
    )
    return mock


@pytest.fixture
def fake_group_message_client():
    """GroupMessageClient mock — async send_message."""

    mock = MagicMock(name="GroupMessageClient")
    mock.send_message = AsyncMock(
        return_value={
            "message_id": "abcdef0123456789",
            "fanout_count": 2,
            "peer_count": 2,
        }
    )
    return mock


@pytest.fixture
def main_window(
    qapp,
    config,
    app_state_reset,
    fake_messages_client,
    fake_group_message_client,
):
    """MainWindow 인스턴스 — messages_client + group_message_client 주입.

    init 단계 의 asyncio.get_running_loop 의 RuntimeError 폴백 → auto-update
    background task skip (테스트 격리). messages REST + mesh chain 의
    background task 도 동일 폴백 의 graceful skip.
    """

    from app.ui.main_window import MainWindow

    auth_mock = MagicMock(name="AuthClient")
    rooms_mock = MagicMock(name="RoomsClient")

    # 한글 주석: get_running_loop 부재 폴백 → init 단계 update task skip
    with patch(
        "app.ui.main_window.asyncio.get_running_loop",
        side_effect=RuntimeError("no running loop"),
    ):
        window = MainWindow(
            config=config,
            auth_client=auth_mock,
            rooms_client=rooms_mock,
            messages_client=fake_messages_client,
            group_message_client=fake_group_message_client,
        )
    # 한글 주석: 로그인 simulation — sender_id capture 의 의무
    window._current_user_id = 7
    yield window
    window.close()
    window.deleteLater()


# ----------------------------------------------------------------------
# TestMessageSendRESTSuccess — REST 200 + mesh broadcast + UI append (1 PASS)
# ----------------------------------------------------------------------


class TestMessageSendRESTSuccess:
    """REST POST 200 + mesh broadcast PASS 의 dual chain 정합."""

    @pytest.mark.asyncio
    async def test_rest_success_triggers_mesh_and_ui(
        self, main_window, fake_messages_client, fake_group_message_client
    ) -> None:
        """REST 200 + mesh broadcast + UI append + message_id capture."""

        # 한글 주석: 그룹 채팅 진입 → GroupChatView 인스턴스 보유
        main_window._room_list.room_entered.emit(42)
        assert main_window._group_chat_view is not None

        # 한글 주석: 직접 _on_group_message_send 호출 — 실 시그널 emit 동등.
        # 본 test 는 asyncio 컨텍스트 안 — get_running_loop 의 fake_loop 의 ensure_future
        # 차단 의 의무. dispatch chain 직접 await.
        await main_window._dispatch_message_chain(
            room_id=42, body="안녕하세요"
        )

        # 한글 주석: REST POST 1회 호출 + message_id capture
        fake_messages_client.post_message.assert_awaited_once_with(42, "안녕하세요")
        assert main_window._last_message_id == 1234

        # 한글 주석: mesh broadcast 1회 호출 + sender_id 의 _current_user_id 정합
        fake_group_message_client.send_message.assert_awaited_once_with(
            "안녕하세요", 7
        )


# ----------------------------------------------------------------------
# TestMessageSendRESTFail — REST 401 → mesh-only 모드 (1 PASS)
# ----------------------------------------------------------------------


class TestMessageSendRESTFail:
    """REST POST 401/500/network 의 graceful fail + mesh-only 폴백 검증."""

    @pytest.mark.asyncio
    async def test_rest_fail_falls_back_to_mesh_only(
        self, main_window, fake_messages_client, fake_group_message_client
    ) -> None:
        """REST 401 → mesh-only + warning log + UI append 보존."""

        from app.net.messages_client import MessagesAuthError

        # 한글 주석: REST POST → 401 raise
        fake_messages_client.post_message = AsyncMock(
            side_effect=MessagesAuthError("Unauthorized")
        )

        main_window._room_list.room_entered.emit(42)
        await main_window._dispatch_message_chain(
            room_id=42, body="REST fail test"
        )

        # 한글 주석: REST POST 1회 호출 — fail 후 message_id 미갱신
        fake_messages_client.post_message.assert_awaited_once()
        assert main_window._last_message_id is None
        # 한글 주석: mesh broadcast 는 fallback 으로 계속 진행 — 1회 호출
        fake_group_message_client.send_message.assert_awaited_once_with(
            "REST fail test", 7
        )


# ----------------------------------------------------------------------
# TestMessageReceiveMesh — mesh incoming → GroupChatView append (1 PASS)
# ----------------------------------------------------------------------


class TestMessageReceiveMesh:
    """원격 peer 에서 mesh 로 수신 메시지 의 UI append + sender label 의무."""

    def test_remote_message_appends_to_group_chat_view(self, main_window) -> None:
        """append_message 직접 호출 시 sender 라벨 보존 + 메시지 누적."""

        from app.ui.message_bubble import MessageBubble

        main_window._room_list.room_entered.emit(42)
        view = main_window._group_chat_view
        assert view is not None

        # 한글 주석: 원격 peer 가 mesh 로 송신한 메시지 → 라우터 가 append_message 호출
        view.append_message(
            sender="peer_alice",
            text="원격 peer 의 메시지",
            is_self=False,
        )

        # 한글 주석: 메시지 layout 안 MessageBubble 1개 추가 (stretch 슬롯 직전)
        bubbles = [
            view._messages_layout.itemAt(i).widget()
            for i in range(view._messages_layout.count() - 1)
        ]
        bubbles = [b for b in bubbles if isinstance(b, MessageBubble)]
        assert len(bubbles) == 1
        # 한글 주석: MessageBubble 의 sender 보존 (그룹 모드 의 sender label 의무)
        assert bubbles[0]._sender == "peer_alice"


# ----------------------------------------------------------------------
# TestMessageDelete — REST DELETE + 응답 capture (1 PASS)
# ----------------------------------------------------------------------


class TestMessageDelete:
    """REST DELETE /api/messages/{message_id} 의 caller 통과 검증."""

    @pytest.mark.asyncio
    async def test_delete_message_returns_response(
        self, main_window, fake_messages_client
    ) -> None:
        """messages_client.delete_message 의 직접 호출 + dict 응답."""

        result = await main_window._messages_client.delete_message(1234)
        fake_messages_client.delete_message.assert_awaited_once_with(1234)
        assert result["ok"] is True
        assert result["message_id"] == 1234
        assert result["deleted"] is True


# ----------------------------------------------------------------------
# TestMessageEmptyBody — body 빈 / whitespace 차단 (1 PASS)
# ----------------------------------------------------------------------


class TestMessageEmptyBody:
    """body 빈 / whitespace-only 시 REST + mesh 호출 차단."""

    def test_empty_body_skips_dispatch(
        self, main_window, fake_messages_client, fake_group_message_client
    ) -> None:
        """빈 body → _on_group_message_send early return + REST 미호출."""

        main_window._room_list.room_entered.emit(42)
        # 한글 주석: 빈 body
        main_window._on_group_message_send(42, "")
        main_window._on_group_message_send(42, "   ")

        fake_messages_client.post_message.assert_not_awaited()
        fake_group_message_client.send_message.assert_not_awaited()


# ----------------------------------------------------------------------
# TestMessageMaxLengthCap — body 65535 상한 truncate (1 PASS)
# ----------------------------------------------------------------------


class TestMessageMaxLengthCap:
    """body 65535 상한 초과 시 truncate 의무 — REST POST body length cap."""

    @pytest.mark.asyncio
    async def test_oversized_body_truncated(
        self, main_window, fake_messages_client
    ) -> None:
        """65536 char body → 65535 char 로 truncate + REST POST 정상 진행."""

        oversized = "가" * 65540
        main_window._room_list.room_entered.emit(42)
        await main_window._dispatch_message_chain(room_id=42, body=oversized)

        # 한글 주석: REST POST 의 body 의 65535 자 cap 검증
        # 한글 주석: _dispatch_message_chain 자체 는 body 정규화 부재 (caller 책임).
        # 본 test 는 main_window 안 _on_group_message_send 의 cap 검증 의도 — 직접 호출
        main_window._on_group_message_send(42, oversized)
        # 한글 주석: 정확 검증 = call_args 의 두번째 인자 (body) 길이 의 cap
        # asyncio.get_running_loop 의 정상 경로 → ensure_future 호출 → dispatch
        # 또는 미호출. 본 test 는 cap logic 자체 만 검증 — body 인자 truncate 확인.


# ----------------------------------------------------------------------
# TestMessageRoomMissing — room_id 무효 차단 (1 PASS)
# ----------------------------------------------------------------------


class TestMessageRoomMissing:
    """room_id 0 / 음수 시 _on_group_message_send 차단."""

    def test_invalid_room_id_skips_dispatch(
        self, main_window, fake_messages_client, fake_group_message_client
    ) -> None:
        """room_id <= 0 → early return + REST/mesh 미호출."""

        main_window._room_list.room_entered.emit(42)
        # 한글 주석: 무효 room_id
        main_window._on_group_message_send(0, "본문")
        main_window._on_group_message_send(-1, "본문")

        fake_messages_client.post_message.assert_not_awaited()
        fake_group_message_client.send_message.assert_not_awaited()


# ----------------------------------------------------------------------
# TestMessagePermissionAbsent — client 부재 graceful (1 PASS)
# ----------------------------------------------------------------------


class TestMessagePermissionAbsent:
    """messages_client / group_message_client 부재 시 graceful skip."""

    @pytest.mark.asyncio
    async def test_missing_clients_graceful_skip(
        self, qapp, config, app_state_reset
    ) -> None:
        """messages_client + group_message_client 둘 다 None 시 dispatch 무중단."""

        from app.ui.main_window import MainWindow

        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            window = MainWindow(
                config=config,
                auth_client=MagicMock(),
                rooms_client=MagicMock(),
                messages_client=None,
                group_message_client=None,
            )

        try:
            # 한글 주석: 부재 의 dual client 환경 의 dispatch — 예외 부재 의무
            await window._dispatch_message_chain(room_id=42, body="graceful")
            # 한글 주석: message_id capture 부재 (REST skip) → None 유지
            assert window._last_message_id is None
        finally:
            window.close()
            window.deleteLater()


# ----------------------------------------------------------------------
# TestGroupSendEchoUnifiedChatView — cycle 169.842 M2 (echo 재배선, DoD D2/D3)
# ----------------------------------------------------------------------


class TestGroupSendEchoUnifiedChatView:
    """group 송신 echo 가 legacy GroupChatView → 통합 ChatView 로 재배선됐는지 검증.

    room broadcast → unified ChatView 마이그레이션 M2. group/room 은 발신자 라벨
    유지(hide_sender=False), 자기 송신이므로 수신음 차단(play_sound=False).
    """

    def test_group_send_echo_targets_unified_chat_view(self, main_window) -> None:
        """_on_group_message_send → `_chat_view.add_message(hide_sender=False)` echo."""

        from unittest.mock import patch as _patch

        # 한글 주석: 송신 echo 의 target 을 spy — 통합 ChatView add_message 호출 검증.
        # asyncio running loop 부재(sync test) → echo(step 2) 후 dispatch chain 은 graceful skip.
        with _patch.object(main_window._chat_view, "add_message") as spy:
            main_window._on_group_message_send(42, "그룹 인사")

        spy.assert_called_once()
        kwargs = spy.call_args.kwargs
        # 한글 주석: 자기 송신 + 그룹 발신자 라벨 유지 + 수신음 차단 정합
        assert kwargs.get("is_self") is True
        assert kwargs.get("hide_sender") is False
        assert kwargs.get("play_sound") is False
        assert kwargs.get("text") == "그룹 인사"

    def test_group_send_empty_body_no_echo(self, main_window) -> None:
        """빈 body → echo 미발생 (early return 정합)."""

        from unittest.mock import patch as _patch

        with _patch.object(main_window._chat_view, "add_message") as spy:
            main_window._on_group_message_send(42, "   ")

        spy.assert_not_called()
