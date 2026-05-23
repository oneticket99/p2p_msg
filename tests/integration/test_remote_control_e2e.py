# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 데스크탑 제어 chain E2E — cycle 169.660 신설.

사용자 directive #8 — "친구간 원격 데스크탑 제어 (capture + input_forward backend 4 +
signaling extension)"

chain:
1. controller → target session grant (PermissionGrant + revoke_token)
2. target 의 MockCaptureBackend 안 capture() → CapturedFrame
3. captured_to_remote_frame → RemoteFrame envelope (frame_id + payload bytes)
4. controller → target 의 RemoteInput (mouse_move + mouse_click + key_down)
5. session bandwidth + payload size verify
"""

from __future__ import annotations

import time

import pytest


pytestmark = pytest.mark.integration


class TestRemoteCaptureChain:
    """MockCaptureBackend → CapturedFrame → RemoteFrame envelope chain."""

    def test_mock_capture_returns_bgra_frame(self) -> None:
        from app.remote.capture import CaptureFormat, MockCaptureBackend

        backend = MockCaptureBackend(width=4, height=4)
        frame = backend.capture()
        assert frame.width == 4
        assert frame.height == 4
        assert frame.format == CaptureFormat.BGRA
        # 4x4 BGRA = 64 bytes
        assert len(frame.buffer) == 64
        assert frame.capture_time_ms > 0

    def test_captured_to_remote_frame_envelope(self) -> None:
        from app.remote.capture import MockCaptureBackend, captured_to_remote_frame
        from app.remote.protocol import FrameFormat

        backend = MockCaptureBackend(width=2, height=2)
        captured = backend.capture()
        remote = captured_to_remote_frame(captured, frame_id=42)
        assert remote.frame_id == 42
        assert remote.width == 2
        assert remote.height == 2
        # 한글 주석 — FrameFormat = RAW_RGB / PNG / JPEG
        assert remote.format in (FrameFormat.RAW_RGB, FrameFormat.PNG, FrameFormat.JPEG)
        assert remote.payload
        assert remote.timestamp_ms == captured.capture_time_ms

    def test_mock_capture_invalid_dimension_raises(self) -> None:
        from app.remote.capture import MockCaptureBackend

        with pytest.raises(ValueError, match="양수 의무"):
            MockCaptureBackend(width=0, height=1)


class TestRemoteInputChain:
    """controller → target 의 RemoteInput envelope verify."""

    def test_mouse_move_event(self) -> None:
        from app.remote.protocol import InputEventType, RemoteInput

        ev = RemoteInput(
            event_type=InputEventType.MOUSE_MOVE,
            payload={"x": 100, "y": 200},
            timestamp_ms=int(time.time() * 1000),
        )
        assert ev.event_type == InputEventType.MOUSE_MOVE
        assert ev.payload["x"] == 100
        assert ev.payload["y"] == 200

    def test_mouse_click_event(self) -> None:
        from app.remote.protocol import InputEventType, RemoteInput

        ev = RemoteInput(
            event_type=InputEventType.MOUSE_CLICK,
            payload={"x": 50, "y": 75, "button": "left", "pressed": True},
            timestamp_ms=1,
        )
        assert ev.payload["button"] == "left"
        assert ev.payload["pressed"] is True

    def test_key_down_event(self) -> None:
        from app.remote.protocol import InputEventType, RemoteInput

        ev = RemoteInput(
            event_type=InputEventType.KEY_DOWN,
            payload={"keycode": 65, "modifiers": ["shift"]},
            timestamp_ms=1,
        )
        assert ev.payload["keycode"] == 65

    def test_missing_required_key_raises(self) -> None:
        from app.remote.protocol import InputEventType, RemoteInput

        with pytest.raises(ValueError, match="필수 key 누락"):
            RemoteInput(
                event_type=InputEventType.MOUSE_MOVE,
                payload={"x": 100},  # 한글 주석 — y 누락
                timestamp_ms=1,
            )

    def test_mouse_click_missing_button_raises(self) -> None:
        from app.remote.protocol import InputEventType, RemoteInput

        with pytest.raises(ValueError, match="필수 key 누락"):
            RemoteInput(
                event_type=InputEventType.MOUSE_CLICK,
                payload={"x": 50, "y": 75},  # 한글 주석 — button + pressed 누락
                timestamp_ms=1,
            )


class TestRemoteSessionChain:
    """RemoteSession binding + revoke chain."""

    def test_session_binding_with_permission(self) -> None:
        # 한글 주석 — cycle 169.673 정합: PermissionGrant fields = request +
        # granted_at_ms + expires_at_ms + revoke_token(32B) + scope
        import secrets

        from app.remote.permission import (
            PermissionGrant, PermissionMode, PermissionRequest,
        )
        from app.remote.protocol import RemoteSession

        req = PermissionRequest(
            requester_user_id=10,
            target_user_id=20,
            mode=PermissionMode.CONTROL,
            duration_seconds=3600,
            reason="screen share help",
        )
        now_ms = int(time.time() * 1000)
        grant = PermissionGrant(
            request=req,
            granted_at_ms=now_ms,
            expires_at_ms=now_ms + 3600_000,
            revoke_token=secrets.token_bytes(32),
            scope="screen+input",
        )
        session = RemoteSession(
            session_id=secrets.token_bytes(16),
            grant=grant,
            started_at_ms=now_ms,
            bandwidth_bps=10_000_000,
        )
        assert len(session.session_id) == 16
        assert session.grant.request.mode == PermissionMode.CONTROL
        assert session.grant.scope == "screen+input"
        assert session.bandwidth_bps == 10_000_000

    def test_permission_request_self_target_raises(self) -> None:
        # 한글 주석 — requester == target → ValueError 차단
        from app.remote.permission import PermissionMode, PermissionRequest

        with pytest.raises(ValueError, match="동일 user_id"):
            PermissionRequest(
                requester_user_id=10, target_user_id=10,
                mode=PermissionMode.HELP, duration_seconds=60, reason="x",
            )

    def test_permission_grant_expires_before_granted_raises(self) -> None:
        # 한글 주석 — expires_at <= granted_at → ValueError
        import secrets

        from app.remote.permission import (
            PermissionGrant, PermissionMode, PermissionRequest,
        )

        req = PermissionRequest(
            requester_user_id=10, target_user_id=20,
            mode=PermissionMode.HELP, duration_seconds=60, reason="x",
        )
        with pytest.raises(ValueError, match="expires_at_ms"):
            PermissionGrant(
                request=req, granted_at_ms=1000, expires_at_ms=500,
                revoke_token=secrets.token_bytes(32), scope="screen+input",
            )
