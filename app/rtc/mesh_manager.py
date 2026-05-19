# SPDX-License-Identifier: GPL-3.0-or-later
"""WebRTC full-mesh manager — ≤ 8 peer fan-out (cycle 138 skeleton).

cycle 138 skeleton — Phase 5 본격 cycle 에서 aiortc RTCPeerConnection
실 binding 수행. 본 모듈은 mesh cap 검증 + peer dict 관리 + fan-out
broadcast chain 만 제공.

9 peer 초과 시 MAX_MESH_PEERS 가드 → SFU 의무 (Phase 5 마무리).
"""
from __future__ import annotations

import asyncio  # noqa: F401  # Phase 5 본격 binding 에서 사용
import logging
from dataclasses import dataclass
from typing import Callable, Optional

log = logging.getLogger(__name__)

# 한글 주석 — full-mesh 상한. 9 peer 초과 시 SFU 전환 의무 (Phase 5 마무리)
MAX_MESH_PEERS = 8


@dataclass(slots=True)
class MeshPeer:
    """한글 주석 — N-peer mesh 안 단일 peer connection 상태 보관."""

    peer_id: str
    user_id: int
    rtc_peer_connection: object = None  # aiortc RTCPeerConnection (Phase 5 binding)
    data_channel: object = None  # aiortc RTCDataChannel (Phase 5 binding)
    connected: bool = False


class MeshManager:
    """한글 주석 — full-mesh N peer DataChannel + fan-out broadcast manager."""

    def __init__(self, room_id: int, self_peer_id: str) -> None:
        # 한글 주석 — room_id + 자신 peer_id 보관 + peer dict 초기화
        self.room_id = room_id
        self.self_peer_id = self_peer_id
        self.peers: dict[str, MeshPeer] = {}
        self._on_message: Optional[Callable[[str, dict], None]] = None

    def set_message_handler(self, handler: Callable[[str, dict], None]) -> None:
        # 한글 주석 — 수신 DataChannel message handler 등록
        self._on_message = handler

    async def add_peer(self, peer_id: str, user_id: int) -> bool:
        # 한글 주석 — mesh cap 검증 후 신규 peer 등록. 초과/중복 시 False
        if len(self.peers) >= MAX_MESH_PEERS:
            log.warning("[mesh] MAX_MESH_PEERS 도달 — SFU 의무 (Phase 5)")
            return False
        if peer_id in self.peers:
            return False
        self.peers[peer_id] = MeshPeer(peer_id=peer_id, user_id=user_id)
        return True

    async def remove_peer(self, peer_id: str) -> None:
        # 한글 주석 — peer cleanup + DataChannel + RTCPeerConnection close
        peer = self.peers.pop(peer_id, None)
        if peer is None:
            return
        if peer.data_channel is not None:
            try:
                peer.data_channel.close()
            except Exception:  # noqa: BLE001
                pass
        if peer.rtc_peer_connection is not None:
            try:
                await peer.rtc_peer_connection.close()
            except Exception:  # noqa: BLE001
                pass

    async def broadcast(self, message: dict) -> int:
        # 한글 주석 — 모든 connected peer 대상 DataChannel fan-out + 성공 count 반환
        import json

        payload = json.dumps(message, ensure_ascii=False)
        success = 0
        for peer in self.peers.values():
            if not peer.connected or peer.data_channel is None:
                continue
            try:
                peer.data_channel.send(payload)
                success += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("[mesh] broadcast 실패 peer=%s err=%r", peer.peer_id, exc)
        return success

    async def broadcast_payload(self, payload) -> int:
        """MessagePayload (cycle 156) broadcast — schema v1.0 통합 (cycle 158 신설).

        Parameters
        ----------
        payload : MessagePayload
            app.net.message_protocol.MessagePayload instance.

        Returns
        -------
        int
            성공 송신 peer count.
        """
        success = 0
        raw = payload.to_json()
        for peer in self.peers.values():
            if not peer.connected or peer.data_channel is None:
                continue
            try:
                peer.data_channel.send(raw)
                success += 1
            except Exception as exc:  # noqa: BLE001
                log.warning("[mesh] payload broadcast 실패 peer=%s err=%r", peer.peer_id, exc)
        return success

    def dispatch_incoming(self, raw_json: str) -> None:
        """DataChannel 수신 raw json → MessagePayload 파싱 + handler dispatch (cycle 158).

        message_handler 부재 시 graceful skip.
        """
        if self._on_message is None:
            return
        try:
            from app.net.message_protocol import MessagePayload
            payload = MessagePayload.from_json(raw_json)
            # 한글 주석 — handler signature = (sender_peer_id, payload_or_dict)
            # 기존 호환 = dict, cycle 158 안 MessagePayload object 전달
            self._on_message(payload.sender, payload)  # type: ignore[arg-type]
        except Exception as exc:  # noqa: BLE001
            log.warning("[mesh] dispatch 실패 — %r", exc)

    def peer_count(self) -> int:
        # 한글 주석 — 등록된 전체 peer 수 반환
        return len(self.peers)

    def connected_count(self) -> int:
        # 한글 주석 — connected=True 인 peer 만 count
        return sum(1 for p in self.peers.values() if p.connected)
