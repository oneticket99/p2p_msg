# SPDX-License-Identifier: GPL-3.0-or-later
"""rooms 테이블 repository — 시그널링 룸 CRUD."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class RoomRow:
    """rooms row dataclass."""

    id: int
    room_code: str
    owner_id: int
    kind: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime]


async def insert_room(
    pool: Any,
    *,
    room_code: str,
    owner_id: int,
    kind: str = "direct",
) -> int:
    """룸 신규 생성. kind = direct (Phase 1) / group (Phase 2+)."""

    sql = (
        "INSERT INTO rooms (room_code, owner_id, kind, status) "
        "VALUES (%s, %s, %s, 'active')"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_code, owner_id, kind))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_room_by_code(pool: Any, room_code: str) -> Optional[RoomRow]:
    """room_code lookup."""

    sql = (
        "SELECT id, room_code, owner_id, kind, status, created_at, closed_at "
        "FROM rooms WHERE room_code = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_code,))
            row = await cur.fetchone()
    if row is None:
        return None
    return RoomRow(*row)


async def close_room(pool: Any, room_id: int) -> None:
    """룸 종료 — status=closed + closed_at=NOW()."""

    sql = (
        "UPDATE rooms SET status = 'closed', closed_at = CURRENT_TIMESTAMP "
        "WHERE id = %s AND status = 'active'"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id,))
        await conn.commit()
