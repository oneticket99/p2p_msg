# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.rtc.mesh_manager`` + ``app.net.group_message_client`` 단위 테스트.

cycle 138 skeleton 검증 — mesh cap 8 가드 + fan-out chain + ACK event.

테스트 범위:
- ``MeshManager`` 초기화 (room_id + self_peer_id + peers dict)
- ``add_peer`` cap 검증 (8 peer 도달 시 False) + duplicate 차단
- ``remove_peer`` cleanup (DataChannel.close + RTCPeerConnection.close)
- ``broadcast`` 성공 count (connected=True peer 만 + 미연결 skip)
- ``GroupMessageClient.send_message`` message_id uuid4 + fan-out count
- ``GroupMessageClient.on_ack`` event set 동작
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.net.group_message_client import GroupMessageClient
from app.rtc.mesh_manager import MAX_MESH_PEERS, MeshManager, MeshPeer


class TestMeshManagerInit:
    """한글 주석 — MeshManager 초기화 + 빈 peers dict 검증."""

    def test_init_room_id_and_self_peer_id(self) -> None:
        # 한글 주석 — 생성자 인자 보관 검증
        mgr = MeshManager(room_id=42, self_peer_id="self-abc")
        assert mgr.room_id == 42
        assert mgr.self_peer_id == "self-abc"
        assert mgr.peers == {}
        assert mgr.peer_count() == 0
        assert mgr.connected_count() == 0


class TestAddPeer:
    """한글 주석 — add_peer cap 가드 + duplicate 차단 검증."""

    @pytest.mark.asyncio
    async def test_add_peer_success(self) -> None:
        # 한글 주석 — 신규 peer 등록 성공 + peer_count 증가
        mgr = MeshManager(room_id=1, self_peer_id="self")
        ok = await mgr.add_peer("peer-1", user_id=100)
        assert ok is True
        assert mgr.peer_count() == 1
        assert isinstance(mgr.peers["peer-1"], MeshPeer)
        assert mgr.peers["peer-1"].user_id == 100

    @pytest.mark.asyncio
    async def test_add_peer_duplicate_rejected(self) -> None:
        # 한글 주석 — 동일 peer_id 재등록 차단
        mgr = MeshManager(room_id=1, self_peer_id="self")
        await mgr.add_peer("peer-1", user_id=100)
        ok = await mgr.add_peer("peer-1", user_id=200)
        assert ok is False
        assert mgr.peer_count() == 1

    @pytest.mark.asyncio
    async def test_add_peer_cap_enforced(self) -> None:
        # 한글 주석 — MAX_MESH_PEERS 도달 시 추가 등록 차단 (9 번째 = False)
        mgr = MeshManager(room_id=1, self_peer_id="self")
        for i in range(MAX_MESH_PEERS):
            ok = await mgr.add_peer(f"peer-{i}", user_id=i)
            assert ok is True
        assert mgr.peer_count() == MAX_MESH_PEERS
        overflow = await mgr.add_peer("peer-overflow", user_id=999)
        assert overflow is False
        assert mgr.peer_count() == MAX_MESH_PEERS


class TestRemovePeer:
    """한글 주석 — remove_peer cleanup + idempotent 검증."""

    @pytest.mark.asyncio
    async def test_remove_peer_calls_close(self) -> None:
        # 한글 주석 — DataChannel.close + RTCPeerConnection.close 호출 확인
        mgr = MeshManager(room_id=1, self_peer_id="self")
        await mgr.add_peer("peer-1", user_id=100)
        dc = MagicMock()
        pc = MagicMock()
        pc.close = AsyncMock()
        mgr.peers["peer-1"].data_channel = dc
        mgr.peers["peer-1"].rtc_peer_connection = pc

        await mgr.remove_peer("peer-1")

        assert mgr.peer_count() == 0
        dc.close.assert_called_once()
        pc.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remove_peer_missing_noop(self) -> None:
        # 한글 주석 — 미등록 peer remove 시 예외 없이 통과
        mgr = MeshManager(room_id=1, self_peer_id="self")
        await mgr.remove_peer("ghost")
        assert mgr.peer_count() == 0


class TestBroadcast:
    """한글 주석 — broadcast fan-out + 미연결 skip + 송신 성공 count."""

    @pytest.mark.asyncio
    async def test_broadcast_connected_only(self) -> None:
        # 한글 주석 — connected=True peer 의 DataChannel 만 송신
        mgr = MeshManager(room_id=1, self_peer_id="self")
        await mgr.add_peer("peer-1", user_id=100)
        await mgr.add_peer("peer-2", user_id=200)
        await mgr.add_peer("peer-3", user_id=300)

        dc1 = MagicMock()
        dc2 = MagicMock()
        mgr.peers["peer-1"].data_channel = dc1
        mgr.peers["peer-1"].connected = True
        mgr.peers["peer-2"].data_channel = dc2
        mgr.peers["peer-2"].connected = False  # 미연결 skip
        # peer-3 = data_channel=None → skip

        sent = await mgr.broadcast({"type": "hello", "body": "안녕"})
        assert sent == 1
        dc1.send.assert_called_once()
        payload = dc1.send.call_args[0][0]
        decoded = json.loads(payload)
        assert decoded["type"] == "hello"
        assert decoded["body"] == "안녕"
        dc2.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_exception_swallowed(self) -> None:
        # 한글 주석 — send 예외 발생 peer 는 count 미증가 + 전체 chain 계속
        mgr = MeshManager(room_id=1, self_peer_id="self")
        await mgr.add_peer("peer-1", user_id=100)
        await mgr.add_peer("peer-2", user_id=200)

        dc1 = MagicMock()
        dc1.send.side_effect = RuntimeError("boom")
        dc2 = MagicMock()
        mgr.peers["peer-1"].data_channel = dc1
        mgr.peers["peer-1"].connected = True
        mgr.peers["peer-2"].data_channel = dc2
        mgr.peers["peer-2"].connected = True

        sent = await mgr.broadcast({"type": "ping"})
        assert sent == 1
        dc1.send.assert_called_once()
        dc2.send.assert_called_once()


class TestGroupMessageClient:
    """한글 주석 — GroupMessageClient send + ACK event chain 검증."""

    @pytest.mark.asyncio
    async def test_send_message_fan_out(self) -> None:
        # 한글 주석 — send_message 결과 dict 의 message_id + fanout_count + peer_count
        mgr = MeshManager(room_id=7, self_peer_id="self-xyz")
        await mgr.add_peer("peer-1", user_id=100)
        dc = MagicMock()
        mgr.peers["peer-1"].data_channel = dc
        mgr.peers["peer-1"].connected = True

        client = GroupMessageClient(mgr)
        result = await client.send_message(body="hello", sender_user_id=1)

        assert "message_id" in result
        assert len(result["message_id"]) == 32  # uuid4 hex 길이
        assert result["fanout_count"] == 1
        assert result["peer_count"] == 1

        dc.send.assert_called_once()
        payload = json.loads(dc.send.call_args[0][0])
        assert payload["type"] == "group_message"
        assert payload["room_id"] == 7
        assert payload["sender_peer_id"] == "self-xyz"
        assert payload["sender_user_id"] == 1
        assert payload["body"] == "hello"
        assert isinstance(payload["timestamp_ms"], int)

    @pytest.mark.asyncio
    async def test_on_ack_sets_event(self) -> None:
        # 한글 주석 — register_pending → on_ack 호출 시 event set + wait_for 통과
        mgr = MeshManager(room_id=1, self_peer_id="self")
        client = GroupMessageClient(mgr)
        event = client.register_pending("msg-abc")
        assert event.is_set() is False

        client.on_ack("msg-abc")
        await asyncio.wait_for(event.wait(), timeout=1.0)
        assert event.is_set() is True

        client.clear_pending("msg-abc")
        assert "msg-abc" not in client._pending_acks

    def test_on_ack_unknown_message_noop(self) -> None:
        # 한글 주석 — 미등록 message_id ACK 수신 시 예외 없이 통과
        mgr = MeshManager(room_id=1, self_peer_id="self")
        client = GroupMessageClient(mgr)
        client.on_ack("nonexistent")  # 예외 없이 통과
