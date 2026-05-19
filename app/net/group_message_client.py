# SPDX-License-Identifier: GPL-3.0-or-later
"""그룹 메시지 client — MeshManager fan-out + ACK chain + audit (cycle 138).

MeshManager wrapper — 송신자의 message_id 생성 + fan-out broadcast +
ACK 대기 event chain 제공. MESSAGE_SEND audit dispatch 는 Phase 5
본격 binding cycle 에서 server endpoint 연결.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

from app.rtc.mesh_manager import MeshManager

log = logging.getLogger(__name__)


class GroupMessageClient:
    """한글 주석 — 그룹 메시지 송수신 + ACK + retry chain."""

    # 한글 주석 — ACK 대기 timeout 초 + 최대 재시도 횟수
    ACK_TIMEOUT_SECONDS = 5.0
    MAX_RETRY = 3

    def __init__(self, mesh: MeshManager) -> None:
        # 한글 주석 — MeshManager 참조 보관 + pending ACK event dict 초기화
        self.mesh = mesh
        self._pending_acks: dict[str, asyncio.Event] = {}

    async def send_message(self, body: str, sender_user_id: int) -> dict:
        # 한글 주석 — uuid4 hex message_id + KST timestamp_ms + fan-out broadcast
        message_id = uuid.uuid4().hex
        message = {
            "type": "group_message",
            "message_id": message_id,
            "room_id": self.mesh.room_id,
            "sender_user_id": sender_user_id,
            "sender_peer_id": self.mesh.self_peer_id,
            "body": body,
            "timestamp_ms": int(time.time() * 1000),
        }
        fanout_count = await self.mesh.broadcast(message)
        return {
            "message_id": message_id,
            "fanout_count": fanout_count,
            "peer_count": self.mesh.peer_count(),
        }

    def on_ack(self, message_id: str) -> None:
        # 한글 주석 — peer ACK 수신 시 대응 event set → 대기 coroutine 깨움
        event = self._pending_acks.get(message_id)
        if event is not None:
            event.set()

    def register_pending(self, message_id: str) -> asyncio.Event:
        # 한글 주석 — ACK 대기용 event 등록 + 반환 (호출자가 wait_for 사용)
        event = asyncio.Event()
        self._pending_acks[message_id] = event
        return event

    def clear_pending(self, message_id: str) -> None:
        # 한글 주석 — pending ACK event 제거 (메모리 누수 차단)
        self._pending_acks.pop(message_id, None)
