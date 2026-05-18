# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 원격 데스크탑 wire format protocol — 사이클 55.

방향 정의 (사용자 directive 2026-05-21):

- ``controller`` = control 요청자 (PermissionRequest.requester_user_id). 화면
  view + input 제공 단. controller 의 키보드 / 마우스 = target 의 OS 의 적용 의무.
- ``target`` = control 대상 (PermissionRequest.target_user_id). 화면 capture
  + input 수신 + OS 의 키보드 / 마우스 의 controller 의 input event 의 의 적용 단.

3 envelope:

- ``RemoteFrame`` — target → controller 의 screen capture
- ``RemoteInput`` — controller → target 의 input event forward (target 의 OS 의 키보드 / 마우스 의 제어)
- ``RemoteSession`` — 양방향 binding

설계 결정
---------
- frame format = "raw_rgb" / "png" / "jpeg" 3 종 의 string enum. ABR encoding
  (h264 / vp9) = 별개 cycle 의무.
- input event = 4 종 (mouse_move / mouse_click / key_down / key_up). modifier +
  scroll + drag = 별개 cycle 확장.
- 본 module = pure 데이터 모델 + 검증 (network IO + screen capture 부재).
  실 capture / forward = platform-specific (Quartz / Win32 / X11) 의 별개 cycle.

본 module 범위
-------------
- ``FrameFormat`` Enum — 3 종 (raw_rgb / png / jpeg)
- ``InputEventType`` Enum — 4 종 (mouse_move / mouse_click / key_down / key_up)
- ``RemoteFrame`` frozen dataclass — frame_id + width + height + format + payload bytes + timestamp_ms
- ``RemoteInput`` frozen dataclass — event_type + payload Dict + timestamp_ms
- ``RemoteSession`` frozen dataclass — session_id + grant + start_at_ms + bandwidth_bps

본 cycle 의 범위 외 (별개 cycle):
- platform-specific screen capture (Quartz CGDisplayCreateImage / Win32 BitBlt / X11 XGetImage)
- platform-specific input forward (CGEventCreateMouseEvent / SendInput / XTestFakeKeyEvent)
- ABR encoding (h264 / vp9 / raw RGB diff)
- bandwidth estimation + dynamic resolution 조절
- cursor pointer overlay (Pattern A 의 도움 시각화)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Final

from app.remote.permission import PermissionGrant

# session_id 길이 = 16 byte (CSPRNG 권장 — UUID4 등가)
_SESSION_ID_BYTES: Final[int] = 16


class FrameFormat(str, Enum):
    """RemoteFrame payload 의 format."""

    RAW_RGB = "raw_rgb"  # 3 byte per pixel (R, G, B). compression 부재.
    PNG = "png"  # lossless compression.
    JPEG = "jpeg"  # lossy compression — bandwidth 절약.


class InputEventType(str, Enum):
    """RemoteInput 의 event type."""

    MOUSE_MOVE = "mouse_move"  # payload = {x, y} (pixel 절대좌표)
    MOUSE_CLICK = "mouse_click"  # payload = {x, y, button, pressed}
    KEY_DOWN = "key_down"  # payload = {keycode, modifiers}
    KEY_UP = "key_up"  # payload = {keycode, modifiers}


@dataclass(frozen=True, slots=True)
class RemoteFrame:
    """target → controller 의 screen capture 1 frame.

    Attributes
    ----------
    frame_id : int
        sequential 식별자 (0부터 monotonic +1).
    width : int
        frame 가로 pixel.
    height : int
        frame 세로 pixel.
    format : FrameFormat
        payload 의 encoding.
    payload : bytes
        실 image data (format 정합).
    timestamp_ms : int
        capture 시점 (UNIX epoch ms).
    """

    frame_id: int
    width: int
    height: int
    format: FrameFormat
    payload: bytes
    timestamp_ms: int

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            raise ValueError(f"frame_id 음수 불가 — {self.frame_id}")
        if self.width <= 0:
            raise ValueError(f"width 양수 의무 — {self.width}")
        if self.height <= 0:
            raise ValueError(f"height 양수 의무 — {self.height}")
        if not self.payload:
            raise ValueError("payload 빈 bytes 불가")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")


@dataclass(frozen=True, slots=True)
class RemoteInput:
    """controller → target 의 input event forward (target 의 OS 의 키보드 / 마우스 의 제어).

    Attributes
    ----------
    event_type : InputEventType
        4 종 의 1.
    payload : dict
        event 별 데이터 (mouse 좌표 / key code / modifier 등).
    timestamp_ms : int
        event 발생 시점 (UNIX epoch ms).
    """

    event_type: InputEventType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp_ms: int = 0

    def __post_init__(self) -> None:
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")
        # event_type 별 payload 의 필수 key 검증
        required_keys = {
            InputEventType.MOUSE_MOVE: ("x", "y"),
            InputEventType.MOUSE_CLICK: ("x", "y", "button", "pressed"),
            InputEventType.KEY_DOWN: ("keycode",),
            InputEventType.KEY_UP: ("keycode",),
        }
        missing = [
            k for k in required_keys[self.event_type] if k not in self.payload
        ]
        if missing:
            raise ValueError(
                f"{self.event_type.value} payload 필수 key 누락 — {missing}"
            )


@dataclass(frozen=True, slots=True)
class RemoteSession:
    """원격 데스크탑 1 세션 의 binding.

    Attributes
    ----------
    session_id : bytes
        16 byte 세션 식별자 (CSPRNG).
    grant : PermissionGrant
        세션 의 권한 (mode + expiry + revoke_token).
    started_at_ms : int
        세션 시작 시점.
    bandwidth_bps : int
        세션 의 estimated bandwidth (bits per second). 0 = unknown.
    """

    session_id: bytes
    grant: PermissionGrant
    started_at_ms: int
    bandwidth_bps: int = 0

    def __post_init__(self) -> None:
        if len(self.session_id) != _SESSION_ID_BYTES:
            raise ValueError(
                f"session_id 길이 불일치 — "
                f"len={len(self.session_id)} (기대 {_SESSION_ID_BYTES})"
            )
        if self.started_at_ms < 0:
            raise ValueError(
                f"started_at_ms 음수 불가 — {self.started_at_ms}"
            )
        if self.bandwidth_bps < 0:
            raise ValueError(
                f"bandwidth_bps 음수 불가 — {self.bandwidth_bps}"
            )
