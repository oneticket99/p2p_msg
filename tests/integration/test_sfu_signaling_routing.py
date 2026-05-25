# SPDX-License-Identifier: GPL-3.0-or-later
"""SFU signaling 라우팅 통합 테스트 — cycle 169.801 SFU 확장 M3c.

`_dispatch_text` 가 SFU_PUBLISH/SFU_SUBSCRIBE 를 SfuRegistry/SfuRoom 으로
라우팅해 SFU_ANSWER 회신 + SFU_PRODUCERS broadcast 하는지, 실 aiortc offer
SDP 로 검증한다. 실 WebSocket 서버 없이 fake ws + _dispatch_text 직접 구동.

기본 pytest 실행 시 deselect — `pytest -m integration` 명시 실행 의무.
"""

from __future__ import annotations

import pytest

pytest.importorskip("aiortc", reason="aiortc + av wheel install 의무")

from aiortc import RTCPeerConnection  # noqa: E402
from aiortc.mediastreams import VideoStreamTrack  # noqa: E402

from server.protocol import (  # noqa: E402
    MSG_ERROR,
    MSG_SFU_ANSWER,
    MSG_SFU_PRODUCERS,
)
from server.room import Peer, RoomRegistry  # noqa: E402
from server.signaling import _dispatch_text  # noqa: E402

pytestmark = pytest.mark.integration


class _FakeApp(dict):
    """aiohttp web.Application 대체 — dict 기반 registry 저장소."""


class _FakeReq:
    def __init__(self, app: _FakeApp) -> None:
        self.app = app


class _FakeWS:
    """ws.send_json 을 캡처하는 최소 대역 — _dispatch_text 핸들러 검증용."""

    def __init__(self, app: _FakeApp) -> None:
        self.sent: list[dict] = []
        self._req = _FakeReq(app)
        # Peer.send_json 이 ws.closed 를 검사하므로 대역에도 노출
        self.closed = False

    async def send_json(self, payload: dict) -> bool:
        # 한글 주석 — SFU 핸들러의 직접 송신 경로
        self.sent.append(payload)
        return True

    async def send_str(self, raw: str) -> None:
        # 한글 주석 — Peer.send_json 의 내부 송신 경로 (JOIN PEERS/PRODUCERS broadcast)
        import json

        self.sent.append(json.loads(raw))


async def _join(ws: _FakeWS, registry: RoomRegistry, room: str, peer_id: str) -> Peer:
    """JOIN 메시지를 _dispatch_text 로 보내 Peer 를 합류시킨다."""
    import json

    peer = await _dispatch_text(
        ws, None, json.dumps({"type": "JOIN", "room": room, "peer_id": peer_id}), registry
    )
    assert peer is not None and peer.room_id == room
    return peer


async def _make_offer_sdp(video: bool = True, recvonly: bool = False) -> tuple[RTCPeerConnection, str]:
    """publisher/subscriber 용 offer SDP 생성."""
    pc = RTCPeerConnection()
    if recvonly:
        pc.addTransceiver("video", direction="recvonly")
    elif video:
        pc.addTrack(VideoStreamTrack())
    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    return pc, pc.localDescription.sdp


class TestSfuSignalingRouting:
    """SFU_PUBLISH/SFU_SUBSCRIBE 라우팅 검증."""

    @pytest.mark.asyncio
    async def test_publish_without_join_errors(self) -> None:
        """JOIN 이전 SFU_PUBLISH 는 NOT_JOINED 오류."""
        import json

        app = _FakeApp()
        registry = RoomRegistry()
        app["room_registry"] = registry
        ws = _FakeWS(app)
        await _dispatch_text(
            ws, None, json.dumps({"type": "SFU_PUBLISH", "sdp": "x"}), registry
        )
        assert ws.sent and ws.sent[-1]["type"] == MSG_ERROR
        assert ws.sent[-1]["code"] == "NOT_JOINED"

    @pytest.mark.asyncio
    async def test_publish_then_subscribe_flow(self) -> None:
        """JOIN → SFU_PUBLISH(answer + producers broadcast) → SFU_SUBSCRIBE(answer)."""
        import json

        app = _FakeApp()
        registry = RoomRegistry()
        app["room_registry"] = registry
        pcs: list[RTCPeerConnection] = []
        try:
            # alice JOIN + publish
            alice_ws = _FakeWS(app)
            alice = await _join(alice_ws, registry, "r1", "alice")
            pub_pc, pub_offer = await _make_offer_sdp(video=True)
            pcs.append(pub_pc)
            await _dispatch_text(
                alice_ws,
                alice,
                json.dumps({"type": "SFU_PUBLISH", "sdp": pub_offer}),
                registry,
            )
            # SFU_ANSWER(publish) + SFU_PRODUCERS 수신
            answer = next(m for m in alice_ws.sent if m["type"] == MSG_SFU_ANSWER)
            assert answer["kind"] == "publish" and answer["sdp"]
            producers = next(m for m in alice_ws.sent if m["type"] == MSG_SFU_PRODUCERS)
            assert "alice" in producers["producers"]

            # bob JOIN + subscribe to alice
            bob_ws = _FakeWS(app)
            bob = await _join(bob_ws, registry, "r1", "bob")
            sub_pc, sub_offer = await _make_offer_sdp(recvonly=True)
            pcs.append(sub_pc)
            await _dispatch_text(
                bob_ws,
                bob,
                json.dumps(
                    {"type": "SFU_SUBSCRIBE", "producer_id": "alice", "sdp": sub_offer}
                ),
                registry,
            )
            sub_answer = next(m for m in bob_ws.sent if m["type"] == MSG_SFU_ANSWER)
            assert sub_answer["kind"] == "subscribe" and sub_answer["producer_id"] == "alice"
            assert sub_answer["sdp"]
        finally:
            sfu = app.get("sfu_registry")
            if sfu is not None:
                await sfu.shutdown()
            for pc in pcs:
                await pc.close()

    @pytest.mark.asyncio
    async def test_subscribe_missing_producer_errors(self) -> None:
        """존재하지 않는 producer 구독은 SFU_NO_PRODUCER 오류."""
        import json

        app = _FakeApp()
        registry = RoomRegistry()
        app["room_registry"] = registry
        try:
            ws = _FakeWS(app)
            peer = await _join(ws, registry, "r2", "carol")
            await _dispatch_text(
                ws,
                peer,
                json.dumps(
                    {"type": "SFU_SUBSCRIBE", "producer_id": "ghost", "sdp": "x"}
                ),
                registry,
            )
            assert ws.sent[-1]["type"] == MSG_ERROR
            assert ws.sent[-1]["code"] == "SFU_NO_PRODUCER"
        finally:
            sfu = app.get("sfu_registry")
            if sfu is not None:
                await sfu.shutdown()
