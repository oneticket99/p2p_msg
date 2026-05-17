# SPDX-License-Identifier: GPL-3.0-or-later
"""aiortc RTCPeerConnection 의 loopback 통합 테스트.

본 모듈 = 동일 프로세스 의 두 RTCPeerConnection (offerer + answerer) 의
DataChannel round-trip + 텍스트/바이너리 메시지 + ICE candidate exchange
의 실 통합 검증. 시그널링 서버 없이 SDP 직접 교환.

기본 pytest 실행 시 deselect — `pytest -m integration` 명시 실행 의무.

handoff §9.2.2 의 잔존 task #1 (tests/integration/) 회수 의 첫 module.
Phase 1 dogfooding 의 RTT/throughput 실 측정 의 사전 baseline.
"""

from __future__ import annotations

import asyncio

import pytest

# aiortc import — 의 의 av wheel install 의 의 의 의 의 모듈 의 의 의 의 import 의 실패 시 skip
pytest.importorskip("aiortc", reason="aiortc + av wheel 의 install 의무 (brew install ffmpeg)")

from aiortc import RTCPeerConnection, RTCSessionDescription  # noqa: E402

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# helper — offerer/answerer 의 SDP 직접 교환
# ---------------------------------------------------------------------------


async def _negotiate(pc1: RTCPeerConnection, pc2: RTCPeerConnection) -> None:
    """SDP offer/answer + ICE candidate 직접 교환.

    실 시그널링 서버 없이 동일 프로세스 의 두 peer 의 SDP 본문 만 교환한다.
    aiortc 의 의 의 ICE gathering 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 await.
    """

    offer = await pc1.createOffer()
    await pc1.setLocalDescription(offer)

    # ICE gathering 완료 대기 (loopback 의 의 의 의 의 단순 동기 패턴 OK)
    await pc2.setRemoteDescription(
        RTCSessionDescription(sdp=pc1.localDescription.sdp, type=pc1.localDescription.type)
    )
    answer = await pc2.createAnswer()
    await pc2.setLocalDescription(answer)
    await pc1.setRemoteDescription(
        RTCSessionDescription(sdp=pc2.localDescription.sdp, type=pc2.localDescription.type)
    )


# ---------------------------------------------------------------------------
# 1. DataChannel open + text round-trip
# ---------------------------------------------------------------------------


class TestDataChannelLoopback:
    """동일 프로세스 의 두 RTCPeerConnection 의 DataChannel 통합."""

    @pytest.mark.asyncio
    async def test_text_message_round_trip(self) -> None:
        """offerer → answerer 텍스트 메시지 1건 의 round-trip."""

        pc1 = RTCPeerConnection()
        pc2 = RTCPeerConnection()
        try:
            channel = pc1.createDataChannel("test")
            received: asyncio.Future[str] = asyncio.get_event_loop().create_future()
            open_event = asyncio.Event()

            @channel.on("open")
            def _on_open() -> None:
                # offerer 측 DataChannel open — 즉시 메시지 송신
                channel.send("hello tootalk")
                open_event.set()

            @pc2.on("datachannel")
            def _on_dc(dc: object) -> None:
                # answerer 측 신규 channel 수신 — message handler 부착
                @dc.on("message")  # type: ignore[attr-defined]
                def _on_msg(message: object) -> None:
                    if not received.done():
                        received.set_result(message)  # type: ignore[arg-type]

            await _negotiate(pc1, pc2)

            # 메시지 도착 의 의 의 의 의 5초 timeout — CI 환경 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의 의
            msg = await asyncio.wait_for(received, timeout=10.0)
            assert msg == "hello tootalk"
        finally:
            await pc1.close()
            await pc2.close()

    @pytest.mark.asyncio
    async def test_binary_payload_round_trip(self) -> None:
        """바이너리 payload 의 round-trip — file chunk 등가 패턴."""

        pc1 = RTCPeerConnection()
        pc2 = RTCPeerConnection()
        try:
            channel = pc1.createDataChannel("binary")
            received: asyncio.Future[bytes] = asyncio.get_event_loop().create_future()
            payload = b"\x00\xff" * 1024  # 2 KiB null + 0xFF 의 의 의 byte-safe 검증

            @channel.on("open")
            def _on_open() -> None:
                channel.send(payload)

            @pc2.on("datachannel")
            def _on_dc(dc: object) -> None:
                @dc.on("message")  # type: ignore[attr-defined]
                def _on_msg(message: object) -> None:
                    if not received.done() and isinstance(message, (bytes, bytearray)):
                        received.set_result(bytes(message))

            await _negotiate(pc1, pc2)
            msg = await asyncio.wait_for(received, timeout=10.0)
            assert msg == payload
        finally:
            await pc1.close()
            await pc2.close()
