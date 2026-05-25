# SPDX-License-Identifier: GPL-3.0-or-later
"""SignalingClient incoming dispatch unit test (cycle 169.81 신설).

_handle_text_frame 분기 6종 (PEERS / PEER_JOINED / PEER_LEFT / OFFER / ANSWER / ICE / ERROR) 검증.
"""

from __future__ import annotations

import json

import pytest

from app.core.config import load_config
from app.net.signaling_client import SignalingClient


@pytest.fixture
def client() -> SignalingClient:
    # 한글 주석 — minimal client + Config env load + signal capture chain
    cfg = load_config()
    return SignalingClient(config=cfg)


def _collect(signal):
    """pyqtSignal emit 누계 capture."""
    captured = []
    signal.connect(lambda *args: captured.append(args))
    return captured


class TestSignalingDispatch:

    def test_invalid_json_silent_drop(self, client) -> None:
        # 한글 주석 — JSON 파싱 fail 시점 silent drop + signal emit 0
        emitted = _collect(client.peers_received)
        client._handle_text_frame("not-a-json-{{{")
        assert emitted == []

    def test_non_dict_payload_drop(self, client) -> None:
        # 한글 주석 — list payload 차단
        emitted = _collect(client.peers_received)
        client._handle_text_frame(json.dumps(["a", "b"]))
        assert emitted == []

    def test_peers_received(self, client) -> None:
        emitted = _collect(client.peers_received)
        payload = {"type": "PEERS", "peers": ["peer-1", "peer-2"]}
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [(["peer-1", "peer-2"],)]

    def test_peer_joined(self, client) -> None:
        emitted = _collect(client.peer_joined)
        payload = {"type": "PEER_JOINED", "peer_id": "alice"}
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("alice",)]

    def test_peer_joined_empty_peer_skipped(self, client) -> None:
        emitted = _collect(client.peer_joined)
        client._handle_text_frame(json.dumps({"type": "PEER_JOINED", "peer_id": ""}))
        assert emitted == []

    def test_peer_left(self, client) -> None:
        emitted = _collect(client.peer_left)
        client._handle_text_frame(json.dumps({"type": "PEER_LEFT", "peer_id": "bob"}))
        assert emitted == [("bob",)]

    def test_offer_received(self, client) -> None:
        emitted = _collect(client.offer_received)
        payload = {
            "type": "OFFER",
            "from_": "alice",
            "sdp": "v=0\r\no=- 12345 2 IN IP4 0.0.0.0\r\n",
        }
        client._handle_text_frame(json.dumps(payload))
        assert len(emitted) == 1
        from_, sdp = emitted[0]
        assert from_ == "alice"
        assert sdp.startswith("v=0")

    def test_answer_received(self, client) -> None:
        emitted = _collect(client.answer_received)
        payload = {"type": "ANSWER", "from_": "bob", "sdp": "v=0\r\n"}
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("bob", "v=0\r\n")]

    def test_ice_received(self, client) -> None:
        emitted = _collect(client.ice_received)
        payload = {
            "type": "ICE",
            "from_": "alice",
            "candidate": {"candidate": "candidate:1 ...", "sdpMid": "0"},
        }
        client._handle_text_frame(json.dumps(payload))
        assert len(emitted) == 1
        from_, cand = emitted[0]
        assert from_ == "alice"
        assert cand["candidate"].startswith("candidate:1")

    def test_ice_non_dict_candidate_coerced(self, client) -> None:
        # 한글 주석 — candidate 가 dict 부재 시점 빈 dict 로 강제 변환
        emitted = _collect(client.ice_received)
        payload = {"type": "ICE", "from_": "alice", "candidate": "string"}
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("alice", {})]

    def test_error_received(self, client) -> None:
        emitted = _collect(client.error_received)
        payload = {"type": "ERROR", "code": "UNAUTHORIZED", "message": "token expired"}
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("UNAUTHORIZED", "token expired")]

    def test_unknown_type_silent(self, client) -> None:
        emitted_peers = _collect(client.peers_received)
        emitted_offer = _collect(client.offer_received)
        client._handle_text_frame(json.dumps({"type": "FOO_BAR_BAZ"}))
        assert emitted_peers == []
        assert emitted_offer == []


# ---------------------------------------------------------------------------
# SFU 그룹 통화 dispatch + send helper (cycle 169.805 M4b)
# ---------------------------------------------------------------------------


class TestSfuDispatch:
    """SFU_ANSWER / SFU_PRODUCERS 수신 분기 + send helper."""

    def test_sfu_answer_received(self, client) -> None:
        # 한글 주석 — SFU_ANSWER → (kind, sdp, producer_id) 신호 발행
        emitted = _collect(client.sfu_answer_received)
        payload = {
            "type": "SFU_ANSWER",
            "kind": "publish",
            "sdp": "v=0...",
            "producer_id": "alice",
        }
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("publish", "v=0...", "alice")]

    def test_sfu_producers_received(self, client) -> None:
        # 한글 주석 — SFU_PRODUCERS → (room, producers) 신호 발행
        emitted = _collect(client.sfu_producers_received)
        payload = {
            "type": "SFU_PRODUCERS",
            "room": "r1",
            "producers": ["alice", "bob"],
        }
        client._handle_text_frame(json.dumps(payload))
        assert emitted == [("r1", ["alice", "bob"])]

    @pytest.mark.asyncio
    async def test_send_sfu_publish(self, client) -> None:
        # 한글 주석 — send_sfu_publish 가 self peer_id 보강 + 올바른 payload 송신
        client._state.set_identity(room_id="r1", peer_id="alice")
        sent: list[str] = []

        class _FakeWS:
            closed = False

            async def send_str(self, raw: str) -> None:
                sent.append(raw)

        client._ws = _FakeWS()
        await client.send_sfu_publish("r1", "v=0-pub")
        payload = json.loads(sent[-1])
        assert payload == {
            "type": "SFU_PUBLISH",
            "room": "r1",
            "peer_id": "alice",
            "sdp": "v=0-pub",
        }

    @pytest.mark.asyncio
    async def test_send_sfu_subscribe(self, client) -> None:
        # 한글 주석 — send_sfu_subscribe 가 producer_id + recvonly offer 송신
        client._state.set_identity(room_id="r1", peer_id="bob")
        sent: list[str] = []

        class _FakeWS:
            closed = False

            async def send_str(self, raw: str) -> None:
                sent.append(raw)

        client._ws = _FakeWS()
        await client.send_sfu_subscribe("r1", "alice", "v=0-sub")
        payload = json.loads(sent[-1])
        assert payload == {
            "type": "SFU_SUBSCRIBE",
            "room": "r1",
            "peer_id": "bob",
            "producer_id": "alice",
            "sdp": "v=0-sub",
        }
