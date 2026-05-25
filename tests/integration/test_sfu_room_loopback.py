# SPDX-License-Identifier: GPL-3.0-or-later
"""server-side SFU room 의 1→2 forward loopback 통합 테스트 — cycle 169.799 M3b.

동일 프로세스에서 publisher 1명 + subscriber 2명을 실 aiortc
``RTCPeerConnection`` 으로 결선해, publisher 의 미디어 track 이 ``SfuRoom``
(MediaRelay) 을 거쳐 두 subscriber 에게 forward 되는지 검증한다. 시그널링
서버 없이 SDP 본문을 직접 교환한다 (Exec Plan M3 게이트 G3).

publish·subscribe 모두 client-offer / server-answer 대칭 — subscriber 는
recvonly transceiver 로 offer 를 만들고 SFU answer 에 forward track 이 실린다.

기본 pytest 실행 시 deselect — `pytest -m integration` 명시 실행 의무.
"""

from __future__ import annotations

import asyncio

import pytest

# aiortc + av wheel install 부재 시 skip (brew install ffmpeg 의존)
pytest.importorskip("aiortc", reason="aiortc + av wheel install 의무")

from aiortc import RTCPeerConnection, RTCSessionDescription  # noqa: E402
from aiortc.mediastreams import VideoStreamTrack  # noqa: E402

from server.sfu_room import SfuRoom  # noqa: E402

pytestmark = pytest.mark.integration


async def _wait_connected(pc: RTCPeerConnection, timeout: float = 10.0) -> None:
    """RTCPeerConnection 이 connected/completed 상태에 도달할 때까지 대기."""
    done: asyncio.Future = asyncio.get_running_loop().create_future()

    @pc.on("connectionstatechange")
    def _on_state() -> None:
        # 한글 주석 — connected 또는 completed 도달 시 대기 해제
        if pc.connectionState in ("connected", "completed") and not done.done():
            done.set_result(None)
        elif pc.connectionState == "failed" and not done.done():
            done.set_exception(RuntimeError("connection failed"))

    if pc.connectionState in ("connected", "completed"):
        return
    await asyncio.wait_for(done, timeout=timeout)


class TestSfuRoomLoopback:
    """publisher 1 → subscriber 2 forward 의 실 결선 검증."""

    @pytest.mark.asyncio
    async def test_one_publisher_forwarded_to_two_subscribers(self) -> None:
        """1명 publish 한 video track 이 2명 subscriber 에게 forward 된다."""
        room = SfuRoom("room-sfu-1")
        clients: list[RTCPeerConnection] = []
        try:
            # --- publisher upstream 결선 (client offer → SFU answer) ---
            pub_pc = RTCPeerConnection()
            clients.append(pub_pc)
            pub_pc.addTrack(VideoStreamTrack())
            offer = await pub_pc.createOffer()
            await pub_pc.setLocalDescription(offer)
            answer_sdp = await room.add_publisher("alice", pub_pc.localDescription.sdp)
            await pub_pc.setRemoteDescription(
                RTCSessionDescription(sdp=answer_sdp, type="answer")
            )
            await _wait_connected(pub_pc)

            # producer 등록 확인
            assert room.producer_ids() == ["alice"]

            # --- subscriber 2명 downstream 결선 (client recvonly offer → SFU answer) ---
            received: dict[str, asyncio.Future] = {}
            for sub_id in ("bob", "carol"):
                sub_pc = RTCPeerConnection()
                clients.append(sub_pc)
                fut: asyncio.Future = asyncio.get_running_loop().create_future()
                received[sub_id] = fut

                @sub_pc.on("track")
                def _on_track(track, _fut=fut) -> None:  # noqa: ANN001
                    # 한글 주석 — forward 된 track 수신 시 future 완료
                    if not _fut.done():
                        _fut.set_result(track)

                # 한글 주석 — subscriber 는 recvonly transceiver 로 offer 생성
                sub_pc.addTransceiver("video", direction="recvonly")
                sub_offer = await sub_pc.createOffer()
                await sub_pc.setLocalDescription(sub_offer)
                sub_answer_sdp = await room.subscribe(
                    sub_id, "alice", sub_pc.localDescription.sdp
                )
                await sub_pc.setRemoteDescription(
                    RTCSessionDescription(sdp=sub_answer_sdp, type="answer")
                )
                await _wait_connected(sub_pc)

            # 두 subscriber 모두 forward track 수신
            for sub_id, fut in received.items():
                track = await asyncio.wait_for(fut, timeout=10.0)
                assert track.kind == "video", f"{sub_id} video track 미수신"

            # --- 실제 프레임 forward 검증 (subscriber 1명 1 frame recv) ---
            bob_track = received["bob"].result()
            frame = await asyncio.wait_for(bob_track.recv(), timeout=10.0)
            assert frame is not None, "forward frame 수신 실패"
        finally:
            await room.close()
            for pc in clients:
                await pc.close()

    @pytest.mark.asyncio
    async def test_subscribe_missing_producer_raises(self) -> None:
        """존재하지 않는 producer 구독은 KeyError (Router 가 ERR_SFU_NO_PRODUCER 변환)."""
        room = SfuRoom("room-sfu-2")
        try:
            assert not room.has_producer("ghost")
            with pytest.raises(KeyError):
                await room.subscribe("bob", "ghost", "dummy-offer-sdp")
        finally:
            await room.close()

    @pytest.mark.asyncio
    async def test_remove_peer_cleans_producer(self) -> None:
        """publisher 이탈 시 producer registry 에서 제거된다."""
        room = SfuRoom("room-sfu-3")
        try:
            pub_pc = RTCPeerConnection()
            pub_pc.addTrack(VideoStreamTrack())
            offer = await pub_pc.createOffer()
            await pub_pc.setLocalDescription(offer)
            await room.add_publisher("dave", pub_pc.localDescription.sdp)
            assert "dave" in room.producer_ids()
            await room.remove_peer("dave")
            assert room.producer_ids() == []
            assert room.is_empty()
            await pub_pc.close()
        finally:
            await room.close()
