# SPDX-License-Identifier: GPL-3.0-or-later
"""RemoteSessionRunner 의 실 aiortc DataChannel loopback 통합 test — cycle 169.782 (G2).

Exec Plan `docs/exec-plans/active/2026-05-25-remote-desktop-real-binding.md` M2 게이트 G2.
지금까지 RemoteSessionRunner 는 Mock 주입 callable 로만 검증됐다(headless unit). 본 test 는
동일 프로세스의 두 RTCPeerConnection(host + controller) + 실 DataChannel 위에서:

- host capture loop → RemoteFrame encode → frame 채널 send → controller on_frame 도달
- controller send_local_input → RemoteInput encode → input 채널 send → host grant 게이트 → apply

를 검증한다. "친구 화면이 내 창에 뜨고 내 클릭이 채널로 전달됨(mock dispatch)"의 실 채널 증명.
실 OS capture/dispatch 는 M4(수동 ack) 범위 — 본 test 는 MockCapture/MockInput 사용.
"""

from __future__ import annotations

import asyncio

import pytest

from aiortc import RTCPeerConnection, RTCSessionDescription

from app.remote.capture import MockCaptureBackend
from app.remote.input_forward import MockInputForwardBackend
from app.remote.permission import (
    PermissionGrant,
    PermissionMode,
    PermissionRequest,
    derive_revoke_token,
)
from app.remote.protocol import InputEventType, RemoteInput
from app.remote.session_runner import RemoteSessionRunner, SessionRole, encode_input

pytestmark = pytest.mark.integration

_NOW_MS = 1_700_000_000_000


def _active_grant() -> PermissionGrant:
    req = PermissionRequest(
        requester_user_id=1, target_user_id=2, mode=PermissionMode.HELP,
        duration_seconds=300, reason="loopback",
    )
    return PermissionGrant(
        request=req, granted_at_ms=_NOW_MS, expires_at_ms=_NOW_MS + 300_000,
        revoke_token=derive_revoke_token(), scope="screen+input",
    )


async def _negotiate(pc1: RTCPeerConnection, pc2: RTCPeerConnection) -> None:
    """SDP offer/answer 직접 교환 (실 시그널링 서버 없이 동일 프로세스 loopback)."""

    offer = await pc1.createOffer()
    await pc1.setLocalDescription(offer)
    await pc2.setRemoteDescription(
        RTCSessionDescription(sdp=pc1.localDescription.sdp, type=pc1.localDescription.type)
    )
    answer = await pc2.createAnswer()
    await pc2.setLocalDescription(answer)
    await pc1.setRemoteDescription(
        RTCSessionDescription(sdp=pc2.localDescription.sdp, type=pc2.localDescription.type)
    )


class TestRemoteSessionLoopback:
    """RemoteSessionRunner 실 DataChannel 양방향 chain."""

    @pytest.mark.asyncio
    async def test_frame_and_input_over_real_datachannel(self) -> None:
        host_pc = RTCPeerConnection()
        ctrl_pc = RTCPeerConnection()
        try:
            # host = frame 송신 채널 생성 + controller 의 input 채널 수신
            frame_ch = host_pc.createDataChannel("tootalk-remote-frame")
            # controller = input 송신 채널 생성 + host 의 frame 채널 수신
            input_ch = ctrl_pc.createDataChannel("tootalk-remote-input")

            rendered: list = []
            host_backend = MockInputForwardBackend()

            controller = RemoteSessionRunner(
                SessionRole.CONTROLLER,
                on_frame=lambda f: rendered.append(f),
                send_input=lambda b: input_ch.send(b),
                now_ms=lambda: _NOW_MS,
            )
            host = RemoteSessionRunner(
                SessionRole.HOST,
                grant=_active_grant(),
                capture_backend=MockCaptureBackend(width=4, height=4),
                input_backend=host_backend,
                send_frame=lambda b: frame_ch.send(b),
                frame_interval_s=0.01,
                max_frames=3,
                now_ms=lambda: _NOW_MS,
            )

            frames_done = asyncio.get_event_loop().create_future()
            input_done = asyncio.get_event_loop().create_future()

            # controller 쪽 — host 가 보낸 frame 채널 수신 → runner.handle_incoming_frame
            @ctrl_pc.on("datachannel")
            def _ctrl_dc(dc: object) -> None:
                @dc.on("message")  # type: ignore[attr-defined]
                def _on_frame_msg(message: object) -> None:
                    if isinstance(message, (bytes, bytearray)):
                        async def _render() -> None:
                            # 한글 주석 — handle 완료 후 count 체크 (ensure_future race 회피)
                            await controller.handle_incoming_frame(bytes(message))
                            if len(rendered) >= 3 and not frames_done.done():
                                frames_done.set_result(True)
                        asyncio.ensure_future(_render())

            # host 쪽 — controller 가 보낸 input 채널 수신 → runner.handle_incoming_input
            @host_pc.on("datachannel")
            def _host_dc(dc: object) -> None:
                @dc.on("message")  # type: ignore[attr-defined]
                def _on_input_msg(message: object) -> None:
                    if isinstance(message, (bytes, bytearray)):
                        async def _apply() -> None:
                            await host.handle_incoming_input(bytes(message))
                            if host_backend.applied and not input_done.done():
                                input_done.set_result(True)
                        asyncio.ensure_future(_apply())

            await _negotiate(host_pc, ctrl_pc)

            # frame 채널 open 대기 후 host capture loop 기동
            frame_open = asyncio.Event()

            @frame_ch.on("open")
            def _fo() -> None:
                frame_open.set()

            await asyncio.wait_for(frame_open.wait(), timeout=10.0)
            await host.start()

            # host 가 3 frame 송신 → controller 렌더 도달
            await asyncio.wait_for(frames_done, timeout=10.0)
            assert len(rendered) >= 3

            # input 채널 open 대기 후 controller → host input 송신
            input_open = asyncio.Event()
            if input_ch.readyState == "open":
                input_open.set()
            else:
                @input_ch.on("open")
                def _io() -> None:
                    input_open.set()
            await asyncio.wait_for(input_open.wait(), timeout=10.0)

            await controller.send_local_input(
                RemoteInput(
                    event_type=InputEventType.MOUSE_CLICK,
                    payload={"x": 12, "y": 34, "button": "left", "pressed": True},
                    timestamp_ms=_NOW_MS,
                )
            )
            # host 가 실 채널로 input 수신 + grant 게이트 통과 + apply
            await asyncio.wait_for(input_done, timeout=10.0)
            assert len(host_backend.applied) >= 1
            assert host_backend.applied[0].event_type is InputEventType.MOUSE_CLICK
        finally:
            await host.stop()
            await host_pc.close()
            await ctrl_pc.close()
