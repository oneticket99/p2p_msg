# SPDX-License-Identifier: GPL-3.0-or-later
"""그룹 메시지 client — MeshManager fan-out + ACK chain + audit (cycle 138).

역할 — 그룹 룸 메시지를 mesh peer 전원에게 fan-out 하고, message_id 별 ACK
대기 event 를 관리한다(REST 아님 — P2P mesh 경로).

계층 위치 — app/net 클라이언트 계층(정본 §E). `app.rtc.mesh_manager.MeshManager`
를 wrapping 하며, UI mixin 이 본 client 를 호출한다. MESSAGE_SEND audit 의 server
endpoint 연결은 Phase 5 본격 binding cycle.

범위 한계 — message_id 생성 + broadcast + ACK event 관리만. 실 재전송 루프·메시지
영속·순서 보장은 호출자(또는 별개 cycle) 책임. ACK event 는 호출자가 register →
wait_for → clear 로 수명 관리(미clear 시 누수).
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid

from app.rtc.mesh_manager import MeshManager

log = logging.getLogger(__name__)


class GroupMessageClient:
    """그룹 메시지 송수신 + ACK + retry chain.

    불변식 — pending ACK event 는 message_id 당 1개, 호출자가 clear 까지 보관.
    협력 — `MeshManager`(fan-out 실행) 주입.
    """

    # ACK 대기 timeout 초 + 최대 재시도 횟수(재전송 루프는 호출자 구현)
    ACK_TIMEOUT_SECONDS = 5.0
    MAX_RETRY = 3

    def __init__(self, mesh: MeshManager) -> None:
        # MeshManager 참조 보관 + pending ACK event dict 초기화
        self.mesh = mesh
        self._pending_acks: dict[str, asyncio.Event] = {}

    async def send_message(self, body: str, sender_user_id: int) -> dict:
        """메시지를 mesh peer 전원에게 fan-out.

        Parameters — body(본문), sender_user_id(발신자).
        Returns — ``{message_id, fanout_count, peer_count}``.
        부작용 — MeshManager.broadcast(P2P 송신 IO). 영속/audit 부재(별개 경로).
        """
        # uuid4 hex message_id + epoch ms + fan-out broadcast
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
        """peer ACK 수신 핸들러 — 대응 event set 으로 대기 coroutine 을 깨운다."""
        event = self._pending_acks.get(message_id)
        if event is not None:
            event.set()

    def register_pending(self, message_id: str) -> asyncio.Event:
        """ACK 대기용 event 등록 + 반환(호출자가 wait_for 로 대기).

        부작용 — `_pending_acks` 에 event 추가. clear_pending 으로 해제 의무(누수 차단).
        """
        event = asyncio.Event()
        self._pending_acks[message_id] = event
        return event

    def clear_pending(self, message_id: str) -> None:
        """pending ACK event 제거 — 메모리 누수 차단(wait 종료 후 호출 의무)."""
        self._pending_acks.pop(message_id, None)
