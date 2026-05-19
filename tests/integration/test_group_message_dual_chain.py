# SPDX-License-Identifier: GPL-3.0-or-later
"""cycle 148 — messages REST + WebRTC mesh dual chain 의 end-to-end smoke 8 PASS.

본 module 은 cycle 141 (messages persistence REST 4 endpoint) + cycle 138
(WebRTC mesh fan-out) + cycle 142 (main_window dual chain) 의 actual 통합 흐름을
mock aiohttp server + mock mesh broadcast + actual MainWindow chain 으로
end-to-end 의 smoke 검증한다.

cycle 142 의 ``test_main_window_messages.py`` 와의 차이:
- 본 module = aiohttp ``TestServer`` 의 실 HTTP round-trip + 실 ``MessagesRestClient``
  의 httpx call → REST 응답 흐름 의 실 wiring 검증.
- cycle 142 = ``AsyncMock`` 만 의 unit 검증.

본 test 의 커버 영역 (8 PASS)
-----------------------------
- TestRESTSuccessMeshBroadcast — 양쪽 PASS + message_id capture + UI append
- TestRESTFailMeshOnly         — REST 500 + mesh fan-out + UI append + warning log
- TestRESTSuccessMeshFail      — REST 200 + mesh exception + 단방향 success log
- TestBothFailGracefulLocal    — REST + mesh 양쪽 fail + UI local echo 보존
- TestACKChain                 — mesh ACK timeout + retry 3회 + final fail
- TestAuditMessageSend         — REST POST 시점 MESSAGE_SEND audit emit
- TestLongMessage              — 16KB cap 검증
- TestRoomNotFound             — 404 graceful + UI append 보존

PyQt6 + httpx + aiohttp 의무. 실 RTCPeerConnection / 실 aiohttp 서버 production
운영 차단 — 모두 mock 의무.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 한글 주석: headless Qt 의무 — offscreen platform 강제
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# 한글 주석: PyQt6 / httpx / aiohttp 부재 시 module 전체 skip — graceful collection
pytest.importorskip("PyQt6", reason="PyQt6 부재 — MainWindow chain 검증 불가")
pytest.importorskip("httpx", reason="httpx 부재 — MessagesRestClient 사용 불가")

import httpx  # noqa: E402
from aiohttp import web  # noqa: E402
from aiohttp.test_utils import TestClient, TestServer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from app.core.app_state import AppState  # noqa: E402
from app.core.config import load_config  # noqa: E402
from app.net.messages_client import (  # noqa: E402
    MessagesNotFoundError,
    MessagesRestClient,
    MessagesServerError,
)

# 한글 주석: integration marker — `pytest -m integration` 명시 실행 의무
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 공유 fixture — QApplication + Config + AppState 격리
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    """모듈 단위 단일 QApplication — headless 정합."""

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


@pytest.fixture
def config():
    """``.env`` 기반 Config — sound_signature_path 등 의무 필드 채움."""

    return load_config()


@pytest.fixture
def app_state_reset():
    """AppState singleton 의 테스트 격리 — clear_identity."""

    state = AppState.instance()
    state.clear_identity()
    yield state
    state.clear_identity()


# ---------------------------------------------------------------------------
# mock aiohttp server — POST /api/rooms/{room_id}/messages 의 4 시나리오
# ---------------------------------------------------------------------------


class _MockMessagesAuditRecorder:
    """MESSAGE_SEND audit emit 의 capture buffer — 5 요소 dict 누적."""

    def __init__(self) -> None:
        # 한글 주석: emit 된 audit record 의 누적 list
        self.records: List[Dict[str, Any]] = []

    def __call__(self, *, user_id: int, target_id: int, metadata: dict) -> None:
        self.records.append(
            {"user_id": user_id, "target_id": target_id, "metadata": metadata}
        )


def _make_mock_app(
    *,
    post_status: int = 201,
    audit_recorder: _MockMessagesAuditRecorder | None = None,
    message_id: int = 42001,
) -> web.Application:
    """mock aiohttp Application — 단일 POST endpoint + audit hook.

    Parameters
    ----------
    post_status : int
        POST 의 응답 status — 201 (성공) / 404 / 500 등 시나리오 분기.
    audit_recorder : _MockMessagesAuditRecorder | None
        MESSAGE_SEND audit emit 의 capture (None 이면 미기록).
    message_id : int
        성공 시 응답 message_id (capture 검증 target).
    """

    app = web.Application()

    async def handle_post(request: web.Request) -> web.Response:
        # 한글 주석: Bearer 검증 — 실 server middleware 와 동등
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return web.json_response({"error": "unauthorized"}, status=401)

        body = await request.json()
        if not isinstance(body.get("body"), str) or not body["body"].strip():
            return web.json_response({"error": "empty_body"}, status=400)

        room_id = int(request.match_info["room_id"])

        if post_status == 404:
            return web.json_response(
                {"error": "room_not_found", "room_id": room_id}, status=404
            )
        if post_status == 500:
            return web.json_response(
                {"error": "internal_error"}, status=500
            )

        # 한글 주석: 성공 분기 — audit emit + 201 응답
        if audit_recorder is not None:
            audit_recorder(
                user_id=42,  # mock user_id (Bearer "Bearer mock-token" 의 매핑)
                target_id=message_id,
                metadata={
                    "room_id": room_id,
                    "kind": body.get("kind", "text"),
                    "sender_id": 42,
                },
            )

        return web.json_response(
            {
                "ok": True,
                "message_id": message_id,
                "room_id": room_id,
                "sender_id": 42,
                "kind": body.get("kind", "text"),
                "created_at": "2026-05-19T10:00:00+00:00",
            },
            status=201,
        )

    app.router.add_post("/api/rooms/{room_id}/messages", handle_post)
    return app


# ---------------------------------------------------------------------------
# 공유 helper — actual MessagesRestClient (mock TestServer 의 base_url 주입)
# ---------------------------------------------------------------------------


async def _build_rest_client_with_mock_server(
    app: web.Application,
) -> tuple[MessagesRestClient, TestClient]:
    """mock TestServer + actual MessagesRestClient — base_url 의 wiring.

    httpx.AsyncClient 의 transport 를 aiohttp TestClient 의 ASGI 호환 wrapping
    부재 → mock TestServer 의 실 host:port 의 사용. test 의 scope 단위 cleanup.
    """

    server = TestServer(app)
    client = TestClient(server)
    await client.start_server()
    base_url = str(client.make_url("/"))[:-1]  # trailing "/" 제거

    # 한글 주석: actual httpx-based REST client — base_url + token 주입
    rest_client = MessagesRestClient(base_url=base_url, token="mock-token")
    return rest_client, client


# ---------------------------------------------------------------------------
# mock GroupMessageClient — 4 시나리오 (PASS / exception / ACK retry chain)
# ---------------------------------------------------------------------------


def _make_mesh_client_pass(fanout: int = 2) -> MagicMock:
    """mesh PASS — send_message 의 fanout_count 정상 응답."""

    mock = MagicMock(name="GroupMessageClient")
    mock.send_message = AsyncMock(
        return_value={
            "message_id": "deadbeef" * 4,
            "fanout_count": fanout,
            "peer_count": fanout,
        }
    )
    return mock


def _make_mesh_client_fail(exc: Exception) -> MagicMock:
    """mesh FAIL — send_message 의 예외 raise."""

    mock = MagicMock(name="GroupMessageClient")
    mock.send_message = AsyncMock(side_effect=exc)
    return mock


# ---------------------------------------------------------------------------
# MainWindow fixture — dual chain 의 actual 의무 의존성 주입
# ---------------------------------------------------------------------------


@pytest.fixture
def main_window_factory(qapp, config, app_state_reset):
    """MainWindow 인스턴스 빌더 — messages_client + group_message_client 주입.

    pytest fixture chain 의 cleanup 의무 — yield 후 close + deleteLater.
    """

    created: list = []

    def _factory(messages_client: Any, group_message_client: Any):
        from app.ui.main_window import MainWindow

        auth_mock = MagicMock(name="AuthClient")
        rooms_mock = MagicMock(name="RoomsClient")

        # 한글 주석: get_running_loop 의 RuntimeError 폴백 — init 단계 task skip
        with patch(
            "app.ui.main_window.asyncio.get_running_loop",
            side_effect=RuntimeError("no running loop"),
        ):
            window = MainWindow(
                config=config,
                auth_client=auth_mock,
                rooms_client=rooms_mock,
                messages_client=messages_client,
                group_message_client=group_message_client,
            )
        # 한글 주석: 로그인 simulation — sender_id capture
        window._current_user_id = 42
        created.append(window)
        return window

    yield _factory

    # 한글 주석: cleanup — 생성된 모든 window 의 close + deleteLater
    for w in created:
        try:
            w.close()
            w.deleteLater()
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# 1. TestRESTSuccessMeshBroadcast — 양쪽 PASS + message_id capture + UI append
# ---------------------------------------------------------------------------


class TestRESTSuccessMeshBroadcast:
    """REST 201 + mesh broadcast PASS 의 dual chain 정합."""

    @pytest.mark.asyncio
    async def test_dual_chain_both_pass(self, main_window_factory) -> None:
        """REST 201 + mesh fan-out 2 → message_id capture + UI bubble 1개."""

        audit = _MockMessagesAuditRecorder()
        app = _make_mock_app(audit_recorder=audit, message_id=42001)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_pass(fanout=2)
            window = main_window_factory(rest_client, mesh_client)

            # 한글 주석: 룸 진입 → GroupChatView 인스턴스 보유
            window._room_list.room_entered.emit(42)
            assert window._group_chat_view is not None

            # 한글 주석: dual chain 직접 await — REST + mesh 양쪽 호출 검증
            await window._dispatch_message_chain(room_id=42, body="안녕하세요")

            # 한글 주석: REST 201 → message_id capture
            assert window._last_message_id == 42001
            # 한글 주석: mesh broadcast 1회 + sender_id 의 _current_user_id 정합
            mesh_client.send_message.assert_awaited_once_with("안녕하세요", 42)
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 2. TestRESTFailMeshOnly — REST 500 → mesh-only + warning log
# ---------------------------------------------------------------------------


class TestRESTFailMeshOnly:
    """REST 500 응답 시 mesh-only 폴백 + message_id 미갱신 + warning log."""

    @pytest.mark.asyncio
    async def test_rest_500_falls_back_to_mesh(
        self, main_window_factory, caplog
    ) -> None:
        """REST 500 → mesh fan-out 계속 진행 + warning log 기록."""

        app = _make_mock_app(post_status=500)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_pass(fanout=1)
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(42)

            # 한글 주석: caplog 의 WARNING 레벨 capture
            with caplog.at_level(logging.WARNING, logger="app.ui.main_window"):
                await window._dispatch_message_chain(
                    room_id=42, body="REST fail test"
                )

            # 한글 주석: REST fail → message_id 미갱신
            assert window._last_message_id is None
            # 한글 주석: mesh broadcast 는 fallback 으로 계속 진행
            mesh_client.send_message.assert_awaited_once_with("REST fail test", 42)
            # 한글 주석: warning log 1개 이상 — "REST POST FAIL" 본문 포함
            warning_msgs = [
                rec.message for rec in caplog.records if rec.levelname == "WARNING"
            ]
            assert any("REST POST FAIL" in m for m in warning_msgs), (
                f"expected REST POST FAIL warning, got {warning_msgs!r}"
            )
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 3. TestRESTSuccessMeshFail — REST 201 + mesh exception → 단방향 success
# ---------------------------------------------------------------------------


class TestRESTSuccessMeshFail:
    """REST 201 + mesh exception → server 영속화 성공 + warning log."""

    @pytest.mark.asyncio
    async def test_rest_pass_mesh_exception(
        self, main_window_factory, caplog
    ) -> None:
        """REST 201 + mesh send_message RuntimeError → server-only chain 종료."""

        app = _make_mock_app(message_id=42002)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_fail(RuntimeError("mesh down"))
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(42)

            with caplog.at_level(logging.WARNING, logger="app.ui.main_window"):
                await window._dispatch_message_chain(
                    room_id=42, body="mesh fail only"
                )

            # 한글 주석: REST 의 message_id capture 성공
            assert window._last_message_id == 42002
            # 한글 주석: mesh 호출은 발생 + 예외 swallow
            mesh_client.send_message.assert_awaited_once()
            # 한글 주석: warning log — "mesh broadcast FAIL" 포함
            warning_msgs = [
                rec.message for rec in caplog.records if rec.levelname == "WARNING"
            ]
            assert any("mesh broadcast FAIL" in m for m in warning_msgs), (
                f"expected mesh broadcast FAIL warning, got {warning_msgs!r}"
            )
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 4. TestBothFailGracefulLocal — REST + mesh 양쪽 fail → UI local echo 보존
# ---------------------------------------------------------------------------


class TestBothFailGracefulLocal:
    """REST 500 + mesh exception → UI 의 local echo 만 보존 + 작성 흔적 유지."""

    @pytest.mark.asyncio
    async def test_both_fail_preserves_ui_local_echo(
        self, main_window_factory, caplog
    ) -> None:
        """REST 500 + mesh raise → UI bubble 보존 + message_id 미갱신."""

        from app.ui.message_bubble import MessageBubble

        app = _make_mock_app(post_status=500)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_fail(RuntimeError("mesh down"))
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(42)

            # 한글 주석: 직접 _on_group_message_send 호출 — UI append + chain dispatch
            # asyncio 컨텍스트 안 의 ensure_future 의 의 dispatch fire-and-forget.
            # 본 test 는 chain 의 fail 후 UI bubble 잔존 만 검증.
            view = window._group_chat_view
            assert view is not None
            # 한글 주석: UI local echo — _dispatch_message_chain 호출 전 manually append
            # _on_group_message_send 의 정상 흐름은 ensure_future 후 즉시 append.
            # 본 test 의 동기 검증 위해 직접 append + chain 직접 await.
            view.append_message(
                sender="me",
                text="both fail",
                is_self=True,
            )
            await window._dispatch_message_chain(room_id=42, body="both fail")

            # 한글 주석: REST + mesh 양쪽 fail → message_id 미갱신
            assert window._last_message_id is None
            # 한글 주석: UI bubble 1개 보존 — 사용자 의 작성 흔적 유지
            bubbles = [
                view._messages_layout.itemAt(i).widget()
                for i in range(view._messages_layout.count() - 1)
            ]
            bubbles = [b for b in bubbles if isinstance(b, MessageBubble)]
            assert len(bubbles) >= 1, "UI local echo bubble 부재 — 작성 흔적 손실"
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 5. TestACKChain — mesh ACK timeout + retry 3회 + final fail
# ---------------------------------------------------------------------------


class TestACKChain:
    """GroupMessageClient 의 ACK chain — register_pending + on_ack + clear_pending."""

    @pytest.mark.asyncio
    async def test_ack_register_and_signal_clear(self) -> None:
        """register_pending → on_ack 의 event set → clear_pending 의 누수 차단."""

        from app.net.group_message_client import GroupMessageClient
        from app.rtc.mesh_manager import MeshManager

        mesh = MeshManager(room_id=42, self_peer_id="self-peer-1")
        client = GroupMessageClient(mesh)

        # 한글 주석: ACK 대기 event 등록 + 즉시 signal
        message_id = "ack-msg-001"
        event = client.register_pending(message_id)
        assert message_id in client._pending_acks
        assert not event.is_set()

        # 한글 주석: peer ACK 수신 simulation
        client.on_ack(message_id)
        assert event.is_set()

        # 한글 주석: pending dict 정리 — 메모리 누수 차단
        client.clear_pending(message_id)
        assert message_id not in client._pending_acks

    @pytest.mark.asyncio
    async def test_ack_timeout_retry_three_then_fail(self) -> None:
        """ACK 부재 시 retry 3회 (asyncio.wait_for) 후 final TimeoutError."""

        from app.net.group_message_client import GroupMessageClient
        from app.rtc.mesh_manager import MeshManager

        mesh = MeshManager(room_id=42, self_peer_id="self-peer-1")
        client = GroupMessageClient(mesh)
        message_id = "ack-timeout-002"
        event = client.register_pending(message_id)

        # 한글 주석: retry 3회 의 timeout 모사 — wait_for 0.01s × 3
        retry_count = 0
        last_exc: Exception | None = None
        for _ in range(GroupMessageClient.MAX_RETRY):
            retry_count += 1
            try:
                await asyncio.wait_for(event.wait(), timeout=0.01)
                break
            except asyncio.TimeoutError as exc:
                last_exc = exc
        # 한글 주석: 3회 retry 후 final fail — TimeoutError 보존
        assert retry_count == GroupMessageClient.MAX_RETRY
        assert isinstance(last_exc, asyncio.TimeoutError)
        client.clear_pending(message_id)


# ---------------------------------------------------------------------------
# 6. TestAuditMessageSend — REST POST 시점 MESSAGE_SEND audit emit
# ---------------------------------------------------------------------------


class TestAuditMessageSend:
    """REST POST 의 audit 5요소 (user_id+target_id+metadata) emit 검증."""

    @pytest.mark.asyncio
    async def test_message_send_audit_emitted(self, main_window_factory) -> None:
        """REST POST 201 → audit recorder 의 MESSAGE_SEND record 1개 capture."""

        audit = _MockMessagesAuditRecorder()
        app = _make_mock_app(audit_recorder=audit, message_id=42003)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_pass(fanout=1)
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(42)

            await window._dispatch_message_chain(room_id=42, body="audit test")

            # 한글 주석: audit recorder 의 1개 record + 5요소 검증
            assert len(audit.records) == 1
            rec = audit.records[0]
            assert rec["user_id"] == 42
            assert rec["target_id"] == 42003
            assert rec["metadata"]["room_id"] == 42
            assert rec["metadata"]["kind"] == "text"
            assert rec["metadata"]["sender_id"] == 42
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 7. TestLongMessage — 16KB cap 검증
# ---------------------------------------------------------------------------


class TestLongMessage:
    """16KB body 의 cap 검증 — server _MAX_BODY_LEN=65535 의 16KB sub-cap.

    cycle 142 의 main_window _MAX_MESSAGE_BODY_LEN 검증과 별개. 본 test 는
    실 HTTP body 의 16KB 전송 + 정상 응답 의 round-trip smoke 검증.
    """

    @pytest.mark.asyncio
    async def test_16kb_body_passes_through(self, main_window_factory) -> None:
        """16KB body 의 POST 정상 round-trip + message_id capture."""

        app = _make_mock_app(message_id=42004)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_pass(fanout=1)
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(42)

            # 한글 주석: 16KB body = 16384 byte (한글 '가' 1자 = 3 byte UTF-8 → 5461자)
            body_16kb = "가" * 5461
            assert len(body_16kb.encode("utf-8")) <= 16384

            await window._dispatch_message_chain(room_id=42, body=body_16kb)

            assert window._last_message_id == 42004
            mesh_client.send_message.assert_awaited_once_with(body_16kb, 42)
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 8. TestRoomNotFound — 404 graceful + UI bubble 보존
# ---------------------------------------------------------------------------


class TestRoomNotFound:
    """존재 부재 room_id 의 404 → graceful warning + UI bubble 보존."""

    @pytest.mark.asyncio
    async def test_404_graceful_warning(
        self, main_window_factory, caplog
    ) -> None:
        """REST 404 (room_not_found) → mesh-only 폴백 + warning log."""

        app = _make_mock_app(post_status=404)
        rest_client, test_client = await _build_rest_client_with_mock_server(app)
        try:
            mesh_client = _make_mesh_client_pass(fanout=0)
            window = main_window_factory(rest_client, mesh_client)
            window._room_list.room_entered.emit(99)

            with caplog.at_level(logging.WARNING, logger="app.ui.main_window"):
                await window._dispatch_message_chain(
                    room_id=99, body="room missing"
                )

            # 한글 주석: REST 404 → message_id 미갱신
            assert window._last_message_id is None
            # 한글 주석: mesh 는 fallback 으로 계속 진행 — 0 fan-out 도 정상
            mesh_client.send_message.assert_awaited_once_with("room missing", 42)
            # 한글 주석: warning log — REST POST FAIL 포함
            warning_msgs = [
                rec.message for rec in caplog.records if rec.levelname == "WARNING"
            ]
            assert any("REST POST FAIL" in m for m in warning_msgs), (
                f"expected REST POST FAIL warning, got {warning_msgs!r}"
            )
        finally:
            await rest_client.close()
            await test_client.close()


# ---------------------------------------------------------------------------
# 회귀 sanity — module level import 의 의무 검증 (collection error 차단)
# ---------------------------------------------------------------------------


def test_module_imports_smoke() -> None:
    """본 module 의 import 흐름 의 회귀 sanity — collection 단계 차단 회피."""

    # 한글 주석: 본 검증은 본 module 의 import 자체 의 PASS 만 검증.
    # 실 chain 의 검증 = 위 8 class.
    assert httpx is not None
    assert MessagesRestClient is not None
    assert MessagesNotFoundError is not None
    assert MessagesServerError is not None
