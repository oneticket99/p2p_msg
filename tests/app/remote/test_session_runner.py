# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteSessionRunner host/controller orchestration headless test — cycle 169.777 신설.

Exec Plan `docs/exec-plans/active/2026-05-25-remote-desktop-real-binding.md` M2 검증.
실 OS / 실 DataChannel 없이 Mock backend + 주입 callable 로 양방향 loop 를 격리 검증한다.

검증 범위:
- frame/input 와이어 직렬화 round-trip (encode↔decode)
- HOST capture loop: MockCaptureBackend → RemoteFrame encode → frame 채널 송신 (max_frames)
- CONTROLLER frame 수신 → decode → on_frame 콜백
- HOST input 수신 → grant 게이트(check_grant_active) → MockInputForwardBackend.apply
- grant 비활성/부재 시 input 거부 (무단 제어 차단)
- controller send_local_input → input 채널 송신
- host→controller→host loopback: capture send 가 controller on_frame 에 도달, controller
  input send 가 host apply 에 도달 (mock 채널 직결)
"""

from __future__ import annotations

import pytest

from app.remote.capture import MockCaptureBackend
from app.remote.input_forward import MockInputForwardBackend
from app.remote.permission import (
    PermissionGrant,
    PermissionMode,
    PermissionRequest,
    derive_revoke_token,
)
from app.remote.protocol import FrameFormat, InputEventType, RemoteFrame, RemoteInput
from app.remote.session_runner import (
    RemoteSessionRunner,
    SessionRole,
    decode_frame,
    decode_input,
    encode_frame,
    encode_input,
)

# 결정성 — 고정 now_ms (grant 활성 구간 내)
_NOW_MS = 1_700_000_010_000


def _active_grant() -> PermissionGrant:
    """1_700_000_000_000 시점 300초 HELP grant (now=_NOW_MS 시점 활성)."""

    req = PermissionRequest(
        requester_user_id=1,
        target_user_id=2,
        mode=PermissionMode.HELP,
        duration_seconds=300,
        reason="원격 도움",
    )
    return PermissionGrant(
        request=req,
        granted_at_ms=1_700_000_000_000,
        expires_at_ms=1_700_000_000_000 + 300 * 1000,
        revoke_token=derive_revoke_token(),
        scope="screen+input",
    )


def _expired_grant() -> PermissionGrant:
    """이미 만료된 grant (now=_NOW_MS 시점 비활성)."""

    req = PermissionRequest(
        requester_user_id=1,
        target_user_id=2,
        mode=PermissionMode.HELP,
        duration_seconds=1,
        reason="만료",
    )
    return PermissionGrant(
        request=req,
        granted_at_ms=1_600_000_000_000,
        expires_at_ms=1_600_000_001_000,
        revoke_token=derive_revoke_token(),
        scope="screen+input",
    )


def _mouse_move(x: int, y: int) -> RemoteInput:
    return RemoteInput(
        event_type=InputEventType.MOUSE_MOVE,
        payload={"x": x, "y": y},
        timestamp_ms=_NOW_MS,
    )


class TestWireRoundTrip:
    """frame/input 직렬화 round-trip."""

    def test_frame_round_trip(self) -> None:
        frame = RemoteFrame(
            frame_id=7,
            width=640,
            height=480,
            format=FrameFormat.RAW_RGB,
            payload=b"\x01\x02\x03\x04",
            timestamp_ms=_NOW_MS,
        )
        decoded = decode_frame(encode_frame(frame))
        assert decoded == frame

    def test_input_round_trip(self) -> None:
        event = RemoteInput(
            event_type=InputEventType.MOUSE_CLICK,
            payload={"x": 10, "y": 20, "button": "left", "pressed": True},
            timestamp_ms=_NOW_MS,
        )
        decoded = decode_input(encode_input(event))
        assert decoded == event

    def test_decode_frame_short_raises(self) -> None:
        with pytest.raises(ValueError):
            decode_frame(b"\x00\x01")


class TestHostCaptureLoop:
    """HOST capture loop → frame 채널 송신."""

    async def test_capture_loop_sends_n_frames(self) -> None:
        sent: list[bytes] = []
        runner = RemoteSessionRunner(
            SessionRole.HOST,
            capture_backend=MockCaptureBackend(width=4, height=4),
            send_frame=lambda b: sent.append(b),
            frame_interval_s=0.0,
            max_frames=3,
            now_ms=lambda: _NOW_MS,
        )
        await runner.start()
        # capture task 완료 대기
        if runner._capture_task is not None:
            await runner._capture_task
        await runner.stop()
        assert len(sent) == 3
        # 첫 frame decode 가능 + frame_id monotonic
        first = decode_frame(sent[0])
        assert first.frame_id == 0
        assert decode_frame(sent[2]).frame_id == 2
        assert runner.frame_counter == 3


class TestControllerFrameRecv:
    """CONTROLLER frame 수신 → on_frame 콜백."""

    async def test_incoming_frame_invokes_callback(self) -> None:
        received: list[RemoteFrame] = []
        runner = RemoteSessionRunner(
            SessionRole.CONTROLLER,
            on_frame=lambda f: received.append(f),
            now_ms=lambda: _NOW_MS,
        )
        frame = RemoteFrame(
            frame_id=1, width=8, height=8, format=FrameFormat.RAW_RGB,
            payload=b"abcd", timestamp_ms=_NOW_MS,
        )
        out = await runner.handle_incoming_frame(encode_frame(frame))
        assert out == frame
        assert received == [frame]

    async def test_corrupt_frame_dropped(self) -> None:
        runner = RemoteSessionRunner(SessionRole.CONTROLLER, now_ms=lambda: _NOW_MS)
        assert await runner.handle_incoming_frame(b"\x00") is None


class TestHostInputGate:
    """HOST input 수신 → grant 게이트 → apply."""

    async def test_active_grant_applies_input(self) -> None:
        backend = MockInputForwardBackend()
        runner = RemoteSessionRunner(
            SessionRole.HOST,
            grant=_active_grant(),
            input_backend=backend,
            now_ms=lambda: _NOW_MS,
        )
        applied = await runner.handle_incoming_input(encode_input(_mouse_move(5, 6)))
        assert applied == 1
        assert len(backend.applied) == 1
        assert backend.applied[0].payload == {"x": 5, "y": 6}
        assert runner.applied_count == 1

    async def test_expired_grant_rejects_input(self) -> None:
        backend = MockInputForwardBackend()
        runner = RemoteSessionRunner(
            SessionRole.HOST,
            grant=_expired_grant(),
            input_backend=backend,
            now_ms=lambda: _NOW_MS,
        )
        applied = await runner.handle_incoming_input(encode_input(_mouse_move(1, 2)))
        assert applied == 0
        assert backend.applied == []

    async def test_no_grant_rejects_input(self) -> None:
        backend = MockInputForwardBackend()
        runner = RemoteSessionRunner(
            SessionRole.HOST,
            grant=None,
            input_backend=backend,
            now_ms=lambda: _NOW_MS,
        )
        assert await runner.handle_incoming_input(encode_input(_mouse_move(1, 2))) == 0
        assert backend.applied == []

    async def test_no_backend_drops_input(self) -> None:
        runner = RemoteSessionRunner(
            SessionRole.HOST, grant=_active_grant(), input_backend=None,
            now_ms=lambda: _NOW_MS,
        )
        assert await runner.handle_incoming_input(encode_input(_mouse_move(1, 2))) == 0


class TestControllerInputSend:
    """CONTROLLER send_local_input → input 채널 송신."""

    async def test_send_local_input(self) -> None:
        sent: list[bytes] = []
        runner = RemoteSessionRunner(
            SessionRole.CONTROLLER,
            send_input=lambda b: sent.append(b),
            now_ms=lambda: _NOW_MS,
        )
        ok = await runner.send_local_input(_mouse_move(11, 22))
        assert ok is True
        assert len(sent) == 1
        assert decode_input(sent[0]).payload == {"x": 11, "y": 22}

    async def test_send_without_callable_returns_false(self) -> None:
        runner = RemoteSessionRunner(SessionRole.CONTROLLER, now_ms=lambda: _NOW_MS)
        assert await runner.send_local_input(_mouse_move(1, 1)) is False


class TestHostControllerLoopback:
    """host↔controller mock 채널 직결 full chain."""

    async def test_full_loopback_chain(self) -> None:
        # 한글 주석 — host send_frame 을 controller.handle_incoming_frame 에 직결,
        # controller send_input 을 host.handle_incoming_input 에 직결
        rendered: list[RemoteFrame] = []
        host_backend = MockInputForwardBackend()

        controller = RemoteSessionRunner(
            SessionRole.CONTROLLER,
            on_frame=lambda f: rendered.append(f),
            now_ms=lambda: _NOW_MS,
        )
        host = RemoteSessionRunner(
            SessionRole.HOST,
            grant=_active_grant(),
            capture_backend=MockCaptureBackend(width=2, height=2),
            input_backend=host_backend,
            send_frame=lambda b: controller.handle_incoming_frame(b),
            frame_interval_s=0.0,
            max_frames=2,
            now_ms=lambda: _NOW_MS,
        )
        # controller 의 input 송신을 host 의 input 수신에 직결
        controller_send: list[bytes] = []

        async def _route_input(b: bytes) -> None:
            controller_send.append(b)
            await host.handle_incoming_input(b)

        controller._send_input = _route_input  # 직결 (test 전용)

        # host capture → controller 렌더
        await host.start()
        if host._capture_task is not None:
            await host._capture_task
        await host.stop()
        assert len(rendered) == 2  # host 가 보낸 2 frame 이 controller 에 도달

        # controller input → host apply
        await controller.send_local_input(_mouse_move(99, 88))
        assert len(host_backend.applied) == 1
        assert host_backend.applied[0].payload == {"x": 99, "y": 88}
