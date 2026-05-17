# SPDX-License-Identifier: GPL-3.0-or-later
"""peers 테이블 repository — 룸 참여자 join/leave 영속화."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class PeerRow:
    """peers row dataclass."""

    id: int
    room_id: int
    user_id: int
    role: str
    joined_at: datetime
    left_at: Optional[datetime]


async def insert_peer(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
    role: str = "member",
) -> int:
    """참여자 등록. role = owner / member."""

    sql = (
        "INSERT INTO peers (room_id, user_id, role) "
        "VALUES (%s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, user_id, role))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def mark_peer_left(pool: Any, room_id: int, user_id: int) -> None:
    """참여자 leave — left_at=NOW() 갱신 (히스토리 보존)."""

    sql = (
        "UPDATE peers SET left_at = CURRENT_TIMESTAMP "
        "WHERE room_id = %s AND user_id = %s AND left_at IS NULL"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, user_id))
        await conn.commit()


async def list_active_peers(pool: Any, room_id: int) -> List[PeerRow]:
    """룸 의 현재 활성 참여자 list."""

    sql = (
        "SELECT id, room_id, user_id, role, joined_at, left_at "
        "FROM peers WHERE room_id = %s AND left_at IS NULL "
        "ORDER BY joined_at ASC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id,))
            rows = await cur.fetchall()
    return [PeerRow(*row) for row in rows]
