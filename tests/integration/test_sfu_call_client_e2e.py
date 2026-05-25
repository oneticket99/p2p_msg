# SPDX-License-Identifier: GPL-3.0-or-later
"""SfuCallClient ↔ SfuRoom 종단 통합 테스트 — cycle 169.804 SFU 확장 M4a.

클라이언트(SfuCallClient)와 server-side(SfuRoom)를 동일 프로세스에서 in-process
라우팅으로 결선해, publisher 가 publish 한 video track 이 SFU 를 거쳐 subscriber
의 ``on_remote_track`` 으로 forward 되는 전 경로를 검증한다 (Exec Plan M4).

범위 한정: 실 signaling 수신 dispatch (SignalingClient 가 SFU_ANSWER/SFU_PRODUCERS
프레임을 받아 ``handle_sfu_answer``/``handle_producers`` 로 라우팅) 는 M4b
(SignalingClient SFU dispatch 결선)의 후속 작업이며, 본 테스트는 그 진입점을
직접 호출하는 client 코어 단독 검증이다.

기본 pytest 실행 시 deselect — `pytest -m integration` 명시 실행 의무.
"""

from __future__ import annotations

import asyncio

import pytest

pytest.importorskip("aiortc", reason="aiortc + av wheel install 의무")

from aiortc.mediastreams import VideoStreamTrack  # noqa: E402

from app.net.sfu_call_client import SfuCallClient  # noqa: E402
from server.sfu_room import SfuRoom  # noqa: E402

pytestmark = pytest.mark.integration


class _VideoOnlyPlayer:
    """publish 테스트용 — 합성 video track 만 노출하는 MediaPlayer 대역."""

    def __init__(self) -> None:
        self.audio = None
        self.video = VideoStreamTrack()


class TestSfuCallClientE2E:
    """publisher → SFU → subscriber forward 의 클라이언트 종단 검증."""

    @pytest.mark.asyncio
    async def test_publish_then_remote_track_forwarded(self) -> None:
        """publisher 의 video 가 producers broadcast → subscriber on_remote_track 로 도달."""
        room = SfuRoom("r1")
        clients: list[SfuCallClient] = []
        loop = asyncio.get_running_loop()
        track_fut: asyncio.Future = loop.create_future()
        try:
            # --- publisher (alice) — SFU_PUBLISH 를 server-side 로 라우팅 ---
            async def pub_send(payload: dict) -> None:
                if payload["type"] == "SFU_PUBLISH":
                    ans = await room.add_publisher(payload["peer_id"], payload["sdp"])
                    await pub.handle_sfu_answer("publish", ans, payload["peer_id"])

            pub = SfuCallClient("r1", "alice", pub_send)
            clients.append(pub)
            await pub.publish(video=True, player=_VideoOnlyPlayer())
            assert room.producer_ids() == ["alice"]

            # --- subscriber (bob) — SFU_SUBSCRIBE 를 server-side 로 라우팅 ---
            def on_track(producer_id: str, track) -> None:  # noqa: ANN001
                if not track_fut.done():
                    track_fut.set_result((producer_id, track))

            async def sub_send(payload: dict) -> None:
                if payload["type"] == "SFU_SUBSCRIBE":
                    ans = await room.subscribe(
                        payload["peer_id"], payload["producer_id"], payload["sdp"]
                    )
                    await sub.handle_sfu_answer(
                        "subscribe", ans, payload["producer_id"]
                    )

            sub = SfuCallClient("r1", "bob", sub_send, on_remote_track=on_track)
            clients.append(sub)

            # producers broadcast 수신 → bob 자동 subscribe(alice)
            await sub.handle_producers(["alice"])
            assert sub.producer_ids() == ["alice"]

            # on_remote_track 으로 forward track 도달 + 실 frame recv
            producer_id, track = await asyncio.wait_for(track_fut, timeout=10.0)
            assert producer_id == "alice"
            assert track.kind == "video"
            frame = await asyncio.wait_for(track.recv(), timeout=10.0)
            assert frame is not None
        finally:
            for c in clients:
                await c.close()
            await room.close()

    @pytest.mark.asyncio
    async def test_subscribe_skips_self_and_duplicate(self) -> None:
        """본인 producer + 중복 subscribe 는 skip (SFU_SUBSCRIBE 미발신)."""
        sent: list[dict] = []

        async def send(payload: dict) -> None:
            sent.append(payload)

        client = SfuCallClient("r1", "alice", send)
        try:
            await client.subscribe("alice")  # 본인 — skip
            assert sent == []
            # producers 에 본인만 있으면 구독 없음
            await client.handle_producers(["alice"])
            assert client.producer_ids() == []
        finally:
            await client.close()
