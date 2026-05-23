# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteFrame + RemoteInput envelope validation chain E2E — cycle 169.687 신설.

chain:
1. RemoteFrame negative frame_id → ValueError
2. RemoteFrame zero width → ValueError
3. RemoteFrame empty payload → ValueError
4. RemoteFrame valid construct
5. RemoteInput MOUSE_MOVE missing x → ValueError
6. RemoteInput MOUSE_CLICK missing button → ValueError
7. RemoteInput KEY_DOWN missing keycode → ValueError
8. RemoteInput KEY_UP valid construct
9. RemoteInput negative timestamp → ValueError
"""

from __future__ import annotations

import pytest

from app.remote.protocol import (
    FrameFormat, InputEventType, RemoteFrame, RemoteInput,
)


pytestmark = pytest.mark.integration


class TestRemoteFrameEnvelope:
    def test_negative_frame_id_raises(self) -> None:
        with pytest.raises(ValueError, match="frame_id"):
            RemoteFrame(
                frame_id=-1, width=10, height=10, format=FrameFormat.RAW_RGB,
                payload=b"x" * 4, timestamp_ms=0,
            )

    def test_zero_width_raises(self) -> None:
        with pytest.raises(ValueError, match="width"):
            RemoteFrame(
                frame_id=0, width=0, height=10, format=FrameFormat.RAW_RGB,
                payload=b"x" * 4, timestamp_ms=0,
            )

    def test_empty_payload_raises(self) -> None:
        with pytest.raises(ValueError, match="payload"):
            RemoteFrame(
                frame_id=0, width=10, height=10, format=FrameFormat.RAW_RGB,
                payload=b"", timestamp_ms=0,
            )

    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms"):
            RemoteFrame(
                frame_id=0, width=10, height=10, format=FrameFormat.RAW_RGB,
                payload=b"x" * 4, timestamp_ms=-1,
            )

    def test_valid_construct(self) -> None:
        # 한글 주석 — frame_id=0 + 정상 payload
        f = RemoteFrame(
            frame_id=42, width=100, height=50, format=FrameFormat.PNG,
            payload=b"PNGDATA", timestamp_ms=1000,
        )
        assert f.frame_id == 42
        assert f.format == FrameFormat.PNG


class TestRemoteInputEnvelope:
    def test_mouse_move_missing_x_raises(self) -> None:
        with pytest.raises(ValueError, match="x"):
            RemoteInput(
                event_type=InputEventType.MOUSE_MOVE,
                payload={"y": 10}, timestamp_ms=0,
            )

    def test_mouse_click_missing_button_raises(self) -> None:
        with pytest.raises(ValueError, match="button"):
            RemoteInput(
                event_type=InputEventType.MOUSE_CLICK,
                payload={"x": 10, "y": 20, "pressed": True},
                timestamp_ms=0,
            )

    def test_key_down_missing_keycode_raises(self) -> None:
        with pytest.raises(ValueError, match="keycode"):
            RemoteInput(
                event_type=InputEventType.KEY_DOWN,
                payload={}, timestamp_ms=0,
            )

    def test_key_up_valid_construct(self) -> None:
        # 한글 주석 — KEY_UP + keycode only path
        evt = RemoteInput(
            event_type=InputEventType.KEY_UP,
            payload={"keycode": 65}, timestamp_ms=100,
        )
        assert evt.event_type == InputEventType.KEY_UP
        assert evt.payload["keycode"] == 65

    def test_negative_timestamp_raises(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms"):
            RemoteInput(
                event_type=InputEventType.MOUSE_MOVE,
                payload={"x": 10, "y": 20}, timestamp_ms=-100,
            )
