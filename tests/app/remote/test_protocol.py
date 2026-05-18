# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.remote.protocol`` 단위 테스트.

RemoteFrame + RemoteInput + RemoteSession 의 wire format 검증. 3 frame format
+ 4 input event type + payload 필수 key + dataclass invariant.
"""

from __future__ import annotations

import secrets

import pytest

from app.remote.permission import (
    PermissionGrant,
    PermissionMode,
    PermissionRequest,
    derive_revoke_token,
)
from app.remote.protocol import (
    FrameFormat,
    InputEventType,
    RemoteFrame,
    RemoteInput,
    RemoteSession,
)


def _make_grant() -> PermissionGrant:
    """test fixture — 활성 PermissionGrant."""

    req = PermissionRequest(
        requester_user_id=1,
        target_user_id=2,
        mode=PermissionMode.HELP,
        duration_seconds=300,
        reason="OBS 설정 도움",
    )
    return PermissionGrant(
        request=req,
        granted_at_ms=1_700_000_000_000,
        expires_at_ms=1_700_000_300_000,
        revoke_token=derive_revoke_token(),
        scope="screen+input",
    )


class TestRemoteFrameValidation:
    """``RemoteFrame`` dataclass 검증."""

    def test_valid_png_frame(self) -> None:
        frame = RemoteFrame(
            frame_id=0,
            width=1920,
            height=1080,
            format=FrameFormat.PNG,
            payload=b"\x89PNG\r\n\x1a\n",
            timestamp_ms=1_700_000_000_000,
        )
        assert frame.format == FrameFormat.PNG
        assert frame.width == 1920

    def test_valid_raw_rgb_frame(self) -> None:
        frame = RemoteFrame(
            frame_id=42,
            width=4,
            height=2,
            format=FrameFormat.RAW_RGB,
            payload=b"\xff\x00\x00" * 8,
            timestamp_ms=100,
        )
        assert frame.format == FrameFormat.RAW_RGB
        assert len(frame.payload) == 24

    def test_negative_frame_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="frame_id 음수 불가"):
            RemoteFrame(
                frame_id=-1,
                width=10,
                height=10,
                format=FrameFormat.JPEG,
                payload=b"jpg",
                timestamp_ms=0,
            )

    def test_zero_width_rejected(self) -> None:
        with pytest.raises(ValueError, match="width 양수 의무"):
            RemoteFrame(
                frame_id=0,
                width=0,
                height=10,
                format=FrameFormat.PNG,
                payload=b"x",
                timestamp_ms=0,
            )

    def test_zero_height_rejected(self) -> None:
        with pytest.raises(ValueError, match="height 양수 의무"):
            RemoteFrame(
                frame_id=0,
                width=10,
                height=0,
                format=FrameFormat.PNG,
                payload=b"x",
                timestamp_ms=0,
            )

    def test_empty_payload_rejected(self) -> None:
        with pytest.raises(ValueError, match="payload 빈 bytes 불가"):
            RemoteFrame(
                frame_id=0,
                width=10,
                height=10,
                format=FrameFormat.PNG,
                payload=b"",
                timestamp_ms=0,
            )

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            RemoteFrame(
                frame_id=0,
                width=10,
                height=10,
                format=FrameFormat.PNG,
                payload=b"x",
                timestamp_ms=-1,
            )


class TestRemoteInputValidation:
    """``RemoteInput`` event-type 별 payload 검증."""

    def test_mouse_move_valid(self) -> None:
        evt = RemoteInput(
            event_type=InputEventType.MOUSE_MOVE,
            payload={"x": 100, "y": 200},
            timestamp_ms=1_700_000_000_000,
        )
        assert evt.event_type == InputEventType.MOUSE_MOVE

    def test_mouse_click_valid(self) -> None:
        evt = RemoteInput(
            event_type=InputEventType.MOUSE_CLICK,
            payload={"x": 100, "y": 200, "button": "left", "pressed": True},
            timestamp_ms=1_700_000_000_000,
        )
        assert evt.payload["button"] == "left"

    def test_key_down_valid(self) -> None:
        evt = RemoteInput(
            event_type=InputEventType.KEY_DOWN,
            payload={"keycode": 65, "modifiers": ["shift"]},
            timestamp_ms=1_700_000_000_000,
        )
        assert evt.payload["keycode"] == 65

    def test_mouse_move_missing_y_rejected(self) -> None:
        with pytest.raises(ValueError, match="mouse_move payload 필수 key 누락"):
            RemoteInput(
                event_type=InputEventType.MOUSE_MOVE,
                payload={"x": 100},
                timestamp_ms=0,
            )

    def test_mouse_click_missing_button_rejected(self) -> None:
        with pytest.raises(ValueError, match="mouse_click payload 필수 key 누락"):
            RemoteInput(
                event_type=InputEventType.MOUSE_CLICK,
                payload={"x": 100, "y": 200, "pressed": True},
                timestamp_ms=0,
            )

    def test_key_down_missing_keycode_rejected(self) -> None:
        with pytest.raises(ValueError, match="key_down payload 필수 key 누락"):
            RemoteInput(
                event_type=InputEventType.KEY_DOWN,
                payload={"modifiers": []},
                timestamp_ms=0,
            )

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            RemoteInput(
                event_type=InputEventType.MOUSE_MOVE,
                payload={"x": 0, "y": 0},
                timestamp_ms=-1,
            )


class TestRemoteSessionValidation:
    """``RemoteSession`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        session = RemoteSession(
            session_id=secrets.token_bytes(16),
            grant=_make_grant(),
            started_at_ms=1_700_000_000_000,
            bandwidth_bps=5_000_000,
        )
        assert session.bandwidth_bps == 5_000_000

    def test_unknown_bandwidth_zero(self) -> None:
        session = RemoteSession(
            session_id=secrets.token_bytes(16),
            grant=_make_grant(),
            started_at_ms=1_700_000_000_000,
        )
        assert session.bandwidth_bps == 0

    def test_invalid_session_id_length(self) -> None:
        with pytest.raises(ValueError, match="session_id 길이 불일치"):
            RemoteSession(
                session_id=b"short",
                grant=_make_grant(),
                started_at_ms=0,
            )

    def test_negative_started_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="started_at_ms 음수 불가"):
            RemoteSession(
                session_id=secrets.token_bytes(16),
                grant=_make_grant(),
                started_at_ms=-1,
            )

    def test_negative_bandwidth_rejected(self) -> None:
        with pytest.raises(ValueError, match="bandwidth_bps 음수 불가"):
            RemoteSession(
                session_id=secrets.token_bytes(16),
                grant=_make_grant(),
                started_at_ms=0,
                bandwidth_bps=-1,
            )
