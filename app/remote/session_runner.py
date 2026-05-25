# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteSessionRunner — 원격 데스크탑 1 세션의 host/controller orchestration.

cycle 169.777 신설 — Exec Plan `docs/exec-plans/active/2026-05-25-remote-desktop-real-binding.md`
M2 핵심 산출물. 기존 빌딩블록(capture / input_forward / protocol / permission)을 살아있는
DataChannel 위에서 양방향 loop 로 묶는 orchestration layer.

역할(role) 2종:

- **HOST(피제어)** — 화면을 주기적으로 capture → `RemoteFrame` encode → frame 채널 송신.
  controller 가 보낸 input bytes 를 수신 → decode → `check_grant_active` 게이트 통과 시
  input backend 로 OS event 적용(apply_events).
- **CONTROLLER(제어)** — host 가 보낸 frame bytes 를 수신 → decode → `on_frame` 콜백으로
  렌더 위임. 로컬 input 을 `RemoteInput` 으로 encode → input 채널 송신.

설계 정합(Exec Plan §7):

- DataChannel 송수신은 주입 callable(`send_frame` / `send_input`)로 추상화한다 — 실 코드는
  `RTCDataChannel.send` 에, test 는 Mock 채널에 결선(headless 검증 가능).
- frame 채널과 input 채널은 별도 label 분리(`tootalk-remote-frame` ordered=false /
  `tootalk-remote-input` ordered=true)를 전제로 하되, 본 runner 는 채널 객체를 직접 알지
  않고 callable 만 받는다.
- capture / input backend 는 DI — 실 OS backend 와 Mock backend 를 동일 runner 가 구동.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import struct
import time
from enum import Enum
from typing import Any, Awaitable, Callable, Optional

from app.remote.capture import CaptureBackend, CapturedFrame, captured_to_remote_frame
from app.remote.input_forward import InputForwardBackend, apply_events
from app.remote.permission import PermissionGrant, check_grant_active
from app.remote.protocol import FrameFormat, InputEventType, RemoteFrame, RemoteInput

log = logging.getLogger(__name__)

# 와이어 frame 헤더 — frame_id(uint32) + width(uint16) + height(uint16) + fmt(uint8) + ts(uint64)
_FRAME_HEADER = struct.Struct("!IHHBQ")
# FrameFormat ↔ 1 byte 매핑 (와이어 절약)
_FMT_TO_BYTE: dict[FrameFormat, int] = {
    FrameFormat.RAW_RGB: 0,
    FrameFormat.PNG: 1,
    FrameFormat.JPEG: 2,
}
_BYTE_TO_FMT: dict[int, FrameFormat] = {v: k for k, v in _FMT_TO_BYTE.items()}


class SessionRole(str, Enum):
    """원격 세션에서 본 노드의 역할."""

    HOST = "host"  # 피제어 — 화면 capture 송신 + input 수신/적용
    CONTROLLER = "controller"  # 제어 — frame 수신/렌더 + input 송신


# ----------------------------------------------------------------------
# 와이어 직렬화 — RemoteFrame / RemoteInput ↔ bytes
# ----------------------------------------------------------------------

def encode_frame(frame: RemoteFrame) -> bytes:
    """``RemoteFrame`` → 와이어 bytes (고정 헤더 + raw payload)."""

    fmt_byte = _FMT_TO_BYTE[frame.format]
    header = _FRAME_HEADER.pack(
        frame.frame_id, frame.width, frame.height, fmt_byte, frame.timestamp_ms
    )
    return header + frame.payload


def decode_frame(data: bytes) -> RemoteFrame:
    """와이어 bytes → ``RemoteFrame`` (헤더 파싱 + payload 분리)."""

    if len(data) < _FRAME_HEADER.size:
        raise ValueError(f"frame bytes 가 헤더보다 짧음 — len={len(data)}")
    frame_id, width, height, fmt_byte, ts = _FRAME_HEADER.unpack(
        data[: _FRAME_HEADER.size]
    )
    payload = data[_FRAME_HEADER.size :]
    fmt = _BYTE_TO_FMT.get(fmt_byte)
    if fmt is None:
        raise ValueError(f"알 수 없는 frame format byte — {fmt_byte}")
    return RemoteFrame(
        frame_id=frame_id,
        width=width,
        height=height,
        format=fmt,
        payload=payload,
        timestamp_ms=ts,
    )


def encode_input(event: RemoteInput) -> bytes:
    """``RemoteInput`` → 와이어 bytes (JSON utf-8, event 작아 overhead 무시 가능)."""

    obj = {
        "t": event.event_type.value,
        "p": event.payload,
        "ts": event.timestamp_ms,
    }
    return json.dumps(obj, ensure_ascii=False).encode("utf-8")


def decode_input(data: bytes) -> RemoteInput:
    """와이어 bytes → ``RemoteInput``."""

    obj = json.loads(data.decode("utf-8"))
    return RemoteInput(
        event_type=InputEventType(obj["t"]),
        payload=dict(obj.get("p") or {}),
        timestamp_ms=int(obj.get("ts") or 0),
    )


# 송신 callable 타입 — bytes 를 받아 (코루틴일 수도 있는) 송신 수행
_SendCallable = Callable[[bytes], Any]
_FrameCallback = Callable[[RemoteFrame], Any]


async def _maybe_await(result: Any) -> None:
    """동기/비동기 callable 결과를 통일 처리 — 코루틴이면 await."""

    if inspect.isawaitable(result):
        await result


class RemoteSessionRunner:
    """host/controller loop orchestrator (DataChannel 추상화 + backend DI)."""

    def __init__(
        self,
        role: SessionRole,
        *,
        grant: Optional[PermissionGrant] = None,
        capture_backend: Optional[CaptureBackend] = None,
        input_backend: Optional[InputForwardBackend] = None,
        send_frame: Optional[_SendCallable] = None,
        send_input: Optional[_SendCallable] = None,
        on_frame: Optional[_FrameCallback] = None,
        frame_interval_s: float = 0.1,
        max_frames: Optional[int] = None,
        now_ms: Optional[Callable[[], int]] = None,
    ) -> None:
        """runner 초기화.

        Parameters
        ----------
        role : SessionRole
            HOST(피제어) 또는 CONTROLLER(제어).
        grant : PermissionGrant | None
            세션 권한 — HOST 의 input 적용 게이트(``check_grant_active``)에 사용.
            None 이면 HOST 는 모든 input 을 거부(안전 기본값).
        capture_backend : CaptureBackend | None
            HOST 의 화면 capture backend (DI). HOST 역할 + capture loop 시 의무.
        input_backend : InputForwardBackend | None
            HOST 의 input 적용 backend (DI). None 이면 input 수신 시 drop.
        send_frame : callable | None
            HOST 가 frame bytes 를 송신할 callable (frame 채널). 동기/비동기 모두 허용.
        send_input : callable | None
            CONTROLLER 가 input bytes 를 송신할 callable (input 채널).
        on_frame : callable | None
            CONTROLLER 가 frame 수신 시 호출할 렌더 콜백 (RemoteFrame 인자).
        frame_interval_s : float
            HOST capture loop 의 frame 간격(초). 기본 0.1s = 10fps.
        max_frames : int | None
            HOST capture loop 가 송신할 최대 frame 수 (test/벤치용). None = 무제한.
        now_ms : callable | None
            현재 시각(ms) 주입 — grant 만료 검증 + test 결정성. 기본 time 기반.
        """

        self._role = role
        self._grant = grant
        self._capture_backend = capture_backend
        self._input_backend = input_backend
        self._send_frame = send_frame
        self._send_input = send_input
        self._on_frame = on_frame
        self._frame_interval_s = frame_interval_s
        self._max_frames = max_frames
        self._now_ms = now_ms or (lambda: int(time.time() * 1000))

        self._running = False
        self._capture_task: Optional[asyncio.Task[None]] = None
        self._frame_counter = 0  # HOST 의 monotonic frame_id
        self._applied_count = 0  # HOST 가 적용한 input 누계 (관측용)

    # ------------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """역할별 기동 — HOST 는 capture loop 예약, CONTROLLER 는 수신 대기(수동)."""

        if self._running:
            return
        self._running = True
        if self._role is SessionRole.HOST and self._capture_backend is not None:
            self._capture_task = asyncio.create_task(
                self._host_capture_loop(), name="remote-host-capture"
            )

    async def stop(self) -> None:
        """capture loop 취소 + 정리 (멱등)."""

        self._running = False
        if self._capture_task is not None and not self._capture_task.done():
            self._capture_task.cancel()
            try:
                await self._capture_task
            except (asyncio.CancelledError, Exception):
                pass
        self._capture_task = None

    # ------------------------------------------------------------------
    # HOST 측 — capture 송신 + input 수신/적용
    # ------------------------------------------------------------------

    async def _host_capture_loop(self) -> None:
        """주기적 화면 capture → RemoteFrame encode → frame 채널 송신."""

        assert self._capture_backend is not None
        try:
            while self._running:
                if self._max_frames is not None and self._frame_counter >= self._max_frames:
                    break
                try:
                    captured: CapturedFrame = self._capture_backend.capture()
                except Exception:
                    log.exception("화면 capture 실패 — 다음 주기 재시도")
                    await asyncio.sleep(self._frame_interval_s)
                    continue
                frame = captured_to_remote_frame(captured, self._frame_counter)
                self._frame_counter += 1
                if self._send_frame is not None:
                    await _maybe_await(self._send_frame(encode_frame(frame)))
                await asyncio.sleep(self._frame_interval_s)
        except asyncio.CancelledError:
            raise

    async def handle_incoming_input(self, data: bytes) -> int:
        """HOST: controller 가 보낸 input bytes 수신 → grant 게이트 → OS 적용.

        Returns
        -------
        int
            적용 성공 event 수 (0 = grant 비활성/backend 부재/적용 실패).
        """

        if self._input_backend is None:
            log.debug("input backend 부재 — input drop")
            return 0
        # grant 게이트 — 무단 제어 차단 (grant None 또는 만료/revoke 시 0)
        if self._grant is None or not check_grant_active(self._grant, self._now_ms()):
            log.warning("grant 비활성 — input 거부 (무단 제어 차단)")
            return 0
        try:
            event = decode_input(data)
        except Exception:
            log.exception("input decode 실패 — drop")
            return 0
        applied = apply_events(self._input_backend, [event])
        self._applied_count += applied
        return applied

    # ------------------------------------------------------------------
    # CONTROLLER 측 — frame 수신/렌더 + input 송신
    # ------------------------------------------------------------------

    async def handle_incoming_frame(self, data: bytes) -> Optional[RemoteFrame]:
        """CONTROLLER: host 가 보낸 frame bytes 수신 → decode → on_frame 콜백."""

        try:
            frame = decode_frame(data)
        except Exception:
            log.exception("frame decode 실패 — drop")
            return None
        if self._on_frame is not None:
            await _maybe_await(self._on_frame(frame))
        return frame

    async def send_local_input(self, event: RemoteInput) -> bool:
        """CONTROLLER: 로컬 input event → encode → input 채널 송신.

        Returns
        -------
        bool
            송신 시도 여부 (send_input callable 부재 시 False).
        """

        if self._send_input is None:
            return False
        await _maybe_await(self._send_input(encode_input(event)))
        return True

    # ------------------------------------------------------------------
    # 관측 property
    # ------------------------------------------------------------------

    @property
    def frame_counter(self) -> int:
        """HOST 가 지금까지 송신한 frame 수."""

        return self._frame_counter

    @property
    def applied_count(self) -> int:
        """HOST 가 지금까지 적용한 input event 누계."""

        return self._applied_count

    @property
    def is_running(self) -> bool:
        """runner 가동 여부."""

        return self._running
