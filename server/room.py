"""Room / Peer 레지스트리 + 메시지 전달 (Service 계층).

본 모듈은 다음을 책임진다.

- Peer 객체 (peer_id ↔ aiohttp WebSocketResponse) 의 lifecycle 관리
- Room 객체 (room_id ↔ Peer 집합) 의 lifecycle 관리
- OFFER/ANSWER/ICE 메시지 1:1 전달
- PEER_JOINED / PEER_LEFT 브로드캐스트
- 연결 종료 시 자동 cleanup

외부 IO 는 WebSocket 송신뿐이며 모두 ``async`` 다. 직접 외부 입력을 파싱하지
않는다 — 입력 검증은 Router 계층(``signaling.py``)이 수행하고, 본 모듈은
이미 정제된 dict 또는 호출 인자만 받는다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

from aiohttp import web

from .protocol import (
    MSG_ERROR,
    MSG_PEER_JOINED,
    MSG_PEER_LEFT,
    MSG_PEERS,
    internal_to_wire,
)


# 모듈 단위 로거 — main.py 에서 핸들러·포맷터·레벨을 설정함
logger = logging.getLogger(__name__)


@dataclass
class Peer:
    """단일 클라이언트 연결을 표현하는 객체.

    Attributes:
        peer_id: 클라이언트가 JOIN 메시지로 선언한 UUID 식별자.
        ws: aiohttp WebSocketResponse — 송신 채널.
        room_id: 합류한 방 식별자 (JOIN 이전에는 None).
        send_lock: 동일 소켓에 동시 송신이 끼어들지 않도록 직렬화하는 lock.
    """

    peer_id: str
    ws: web.WebSocketResponse
    room_id: str | None = None
    # asyncio.Lock 은 인스턴스마다 새로 생성되어야 하므로 default_factory 사용
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def send_json(self, payload: dict[str, Any]) -> bool:
        """JSON envelope 한 건 송신. 실패 시 False 반환 (예외 흡수).

        와이어 포맷 변환(``from_`` → ``from``)은 본 메서드 안에서 수행된다.
        외부 호출자는 내부 표현 dict 만 전달하면 된다.
        """
        wire_payload = internal_to_wire(payload)
        try:
            async with self.send_lock:
                if self.ws.closed:
                    return False
                await self.ws.send_str(json.dumps(wire_payload, ensure_ascii=False))
            return True
        except (ConnectionResetError, RuntimeError) as exc:
            # 연결이 이미 끊긴 경우 — 호출자가 후속 cleanup 을 수행
            logger.warning(
                "peer 송신 실패 peer_id=%s err=%s", self.peer_id, exc
            )
            return False


class Room:
    """동일 ``room_id`` 안의 peer 집합을 관리하는 컨테이너.

    한 방 안에서 peer 들이 서로의 존재를 인지하고 OFFER/ANSWER/ICE 를 교환할
    수 있도록 라우팅 인덱스를 제공한다. Phase 1 MVP 는 1:1 통신만 가정하므로
    peer 수 상한 검증은 두지 않는다 (Phase 2 에서 그룹/mesh 도입 시 확장).
    """

    def __init__(self, room_id: str) -> None:
        # 방 식별자
        self.room_id: str = room_id
        # peer_id → Peer 매핑 (송신 라우팅용)
        self._peers: dict[str, Peer] = {}
        # 컨테이너 변형 직렬화 lock — add/remove 동시성 보호
        self._mutex: asyncio.Lock = asyncio.Lock()

    async def add_peer(self, peer: Peer) -> list[str]:
        """방에 peer 를 추가하고 기존 peer 목록(자기 자신 제외)을 반환."""
        async with self._mutex:
            existing_ids = [pid for pid in self._peers if pid != peer.peer_id]
            self._peers[peer.peer_id] = peer
            peer.room_id = self.room_id
        return existing_ids

    async def remove_peer(self, peer_id: str) -> Peer | None:
        """방에서 peer 를 제거하고 제거된 Peer 객체를 반환 (없으면 None)."""
        async with self._mutex:
            return self._peers.pop(peer_id, None)

    def get_peer(self, peer_id: str) -> Peer | None:
        """peer_id 로 Peer 조회 (없으면 None). 읽기 전용이므로 lock 불필요."""
        return self._peers.get(peer_id)

    def peer_ids(self) -> list[str]:
        """현재 방 안의 모든 peer_id 스냅샷."""
        return list(self._peers.keys())

    def is_empty(self) -> bool:
        """방이 비었는지 여부 — RoomRegistry 가 GC 판단에 사용."""
        return not self._peers

    async def broadcast_except(
        self, payload: dict[str, Any], except_peer_id: str
    ) -> None:
        """특정 peer 를 제외한 동일 방의 모든 peer 에게 동일 payload 송신."""
        # 송신 도중 컨테이너 변형 가능성을 피하기 위해 스냅샷 후 순회
        targets = [p for pid, p in self._peers.items() if pid != except_peer_id]
        if not targets:
            return
        await asyncio.gather(
            *(p.send_json(payload) for p in targets),
            return_exceptions=False,
        )


class RoomRegistry:
    """전역 Room 레지스트리 — aiohttp app 단위 단일 인스턴스.

    Room 생성/삭제와 peer 라우팅을 한 곳에 모아 ``signaling.py`` (Router) 가
    얇은 핸들러로 유지될 수 있게 한다.
    """

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._mutex: asyncio.Lock = asyncio.Lock()

    async def join(self, room_id: str, peer: Peer) -> Room:
        """peer 를 방에 합류시키고 PEERS 응답 + PEER_JOINED 브로드캐스트.

        Returns:
            합류 완료한 Room 객체.
        """
        async with self._mutex:
            room = self._rooms.get(room_id)
            if room is None:
                room = Room(room_id)
                self._rooms[room_id] = room
                logger.info("신규 방 생성 room=%s", room_id)

        existing = await room.add_peer(peer)
        logger.info(
            "peer 합류 room=%s peer=%s existing=%d",
            room_id,
            peer.peer_id,
            len(existing),
        )

        # JOIN 한 본인에게 기존 peer 목록 회신
        peers_msg: dict[str, Any] = {
            "type": MSG_PEERS,
            "room": room_id,
            "peers": existing,
        }
        await peer.send_json(peers_msg)

        # 기존 peer 들에게 신규 합류 알림
        joined_msg: dict[str, Any] = {
            "type": MSG_PEER_JOINED,
            "peer_id": peer.peer_id,
        }
        await room.broadcast_except(joined_msg, except_peer_id=peer.peer_id)

        return room

    async def leave(self, room_id: str, peer_id: str) -> None:
        """peer 를 방에서 제거하고 PEER_LEFT 브로드캐스트.

        방이 비면 레지스트리에서 GC 한다. 존재하지 않는 방/peer 호출은
        조용히 무시한다 (이중 호출 안전).
        """
        async with self._mutex:
            room = self._rooms.get(room_id)
        if room is None:
            return

        removed = await room.remove_peer(peer_id)
        if removed is None:
            return

        logger.info("peer 이탈 room=%s peer=%s", room_id, peer_id)

        left_msg: dict[str, Any] = {
            "type": MSG_PEER_LEFT,
            "peer_id": peer_id,
        }
        await room.broadcast_except(left_msg, except_peer_id=peer_id)

        # 빈 방 GC — 다음 join 에서 다시 생성됨
        if room.is_empty():
            async with self._mutex:
                # 다른 코루틴이 사이에 peer 를 다시 넣지 않았는지 재확인
                if room_id in self._rooms and self._rooms[room_id].is_empty():
                    del self._rooms[room_id]
                    logger.info("빈 방 GC room=%s", room_id)

    async def relay(
        self,
        room_id: str | None,
        from_peer_id: str,
        to_peer_id: str,
        payload: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """OFFER/ANSWER/ICE 1:1 단순 중계.

        Returns:
            (성공 여부, 실패 코드 또는 None). 실패 코드는 ``protocol`` 모듈의
            ``ERR_*`` 상수와 정합한다.
        """
        if room_id is None:
            return False, "NOT_JOINED"

        room = self._rooms.get(room_id)
        if room is None:
            return False, "ROOM_NOT_FOUND"

        target = room.get_peer(to_peer_id)
        if target is None:
            return False, "PEER_NOT_FOUND"

        # 메시지 안에 ``from`` 식별자가 누락된 경우 서버가 보강한다 —
        # 클라이언트 위변조 방어 (전송자는 항상 합류한 본인이어야 함)
        sanitized = dict(payload)
        sanitized["from_"] = from_peer_id
        sanitized["to"] = to_peer_id

        ok = await target.send_json(sanitized)
        if not ok:
            return False, "PEER_NOT_FOUND"
        return True, None

    async def cleanup_peer(self, peer: Peer) -> None:
        """소켓 연결이 끊겼을 때 호출되는 cleanup 진입점.

        JOIN 한 적이 있다면 ``leave`` 와 동일 효과를 낸다. 한 번도 JOIN 하지
        않은 채 연결만 맺고 끊긴 경우는 무처리 (idempotent).
        """
        if peer.room_id is None:
            return
        await self.leave(peer.room_id, peer.peer_id)

    async def shutdown(self) -> None:
        """서버 종료 시 호출 — 모든 방에 ERROR 송신 후 비움.

        클라이언트는 ERROR 수신 직후 소켓 종료를 감지하고 재연결을 시도할 수
        있다. Phase 1 MVP 는 재연결 정책을 클라이언트 자율에 맡긴다.
        """
        async with self._mutex:
            rooms_snapshot = list(self._rooms.values())
            self._rooms.clear()

        shutdown_msg: dict[str, Any] = {
            "type": MSG_ERROR,
            "code": "SERVER_SHUTDOWN",
            "message": "시그널링 서버가 종료됩니다.",
        }
        for room in rooms_snapshot:
            for pid in room.peer_ids():
                peer = room.get_peer(pid)
                if peer is not None:
                    await peer.send_json(shutdown_msg)
        logger.info("RoomRegistry shutdown 완료 rooms=%d", len(rooms_snapshot))
