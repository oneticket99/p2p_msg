# SPDX-License-Identifier: GPL-3.0-or-later
"""SFU room 레지스트리 — cycle 169.801 SFU 확장 M3c.

room_id 별 ``SfuRoom`` 인스턴스의 생성·조회·정리를 한 곳에서 관리한다.
``RoomRegistry`` (시그널링 peer 관리) 와 책임을 분리해 SFU 미디어 forward
상태만 담당한다 (계층 분리, 정본 §E). 첫 ``SFU_PUBLISH`` 시점에 lazy 생성하고,
room 의 producer·subscriber 가 모두 비면 GC 한다.

``signaling.py`` (Router) 가 app context 에서 본 레지스트리 1개를 공유한다.
"""

from __future__ import annotations

import asyncio

from server.sfu_room import SfuRoom


class SfuRegistry:
    """room_id → ``SfuRoom`` 매핑의 생애주기 관리자."""

    def __init__(self) -> None:
        # 한글 주석 — room_id 별 SfuRoom + 동시 접근 직렬화 mutex
        self._rooms: dict[str, SfuRoom] = {}
        self._mutex = asyncio.Lock()

    async def get_or_create(self, room_id: str) -> SfuRoom:
        """room 의 SfuRoom 을 반환하되 없으면 생성한다 (첫 publish 시점 lazy)."""
        async with self._mutex:
            room = self._rooms.get(room_id)
            if room is None:
                room = SfuRoom(room_id)
                self._rooms[room_id] = room
            return room

    def get(self, room_id: str) -> SfuRoom | None:
        """room 의 SfuRoom 을 반환하되 없으면 None (생성하지 않음 — subscribe 조회용)."""
        return self._rooms.get(room_id)

    async def remove_peer(self, room_id: str, peer_id: str) -> None:
        """room 안 peer 의 producer/subscriber 연결을 정리하고, 빈 room 은 GC 한다."""
        async with self._mutex:
            room = self._rooms.get(room_id)
            if room is None:
                return
            await room.remove_peer(peer_id)
            # 한글 주석 — producer·subscriber 가 모두 비면 room 자체 제거 (메모리 회수)
            if room.is_empty():
                del self._rooms[room_id]

    async def shutdown(self) -> None:
        """서버 종료 시 모든 room 의 연결을 정리한다."""
        async with self._mutex:
            for room in self._rooms.values():
                await room.close()
            self._rooms.clear()

    def room_count(self) -> int:
        """활성 SFU room 수 (관측·테스트용)."""
        return len(self._rooms)
