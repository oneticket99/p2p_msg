# SPDX-License-Identifier: GPL-3.0-or-later
"""read_states repository — 읽음 상태 추적 (cycle 169.447 신설)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


async def upsert_last_read(
    pool: Any, *, user_id: int, room_id: int, last_read_msg_id: int,
) -> None:
    """user + room 의 last_read_msg_id UPSERT. 새 msg_id < 기존 시점 skip (역행 차단)."""
    if user_id <= 0 or room_id <= 0:
        raise ValueError("user_id/room_id 양수 의무")
    if last_read_msg_id < 0:
        raise ValueError("last_read_msg_id 음수 차단")
    sql = (
        "INSERT INTO read_states (user_id, room_id, last_read_msg_id) "
        "VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "  last_read_msg_id = GREATEST(last_read_msg_id, VALUES(last_read_msg_id))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, room_id, last_read_msg_id))
        await conn.commit()


async def get_last_read(
    pool: Any, *, user_id: int, room_id: int,
) -> int:
    """user + room 의 last_read_msg_id 반환. row 부재 시 0."""
    sql = (
        "SELECT last_read_msg_id FROM read_states "
        "WHERE user_id = %s AND room_id = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, room_id))
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def get_unread_counts(
    pool: Any, *, user_id: int, room_ids: List[int],
) -> Dict[int, int]:
    """multiple room 의 unread count batch 조회 (chat_list 의 의 batch fan-out).

    SQL = LEFT JOIN messages COUNT(WHERE msg.id > last_read AND sender != user_id).
    """
    if not room_ids:
        return {}
    placeholders = ",".join(["%s"] * len(room_ids))
    sql = (
        f"SELECT m.room_id, COUNT(*) AS unread "
        f"FROM messages m "
        f"LEFT JOIN read_states rs ON rs.user_id = %s AND rs.room_id = m.room_id "
        f"WHERE m.room_id IN ({placeholders}) "
        f"  AND m.sender_id != %s "
        f"  AND m.id > COALESCE(rs.last_read_msg_id, 0) "
        f"GROUP BY m.room_id"
    )
    params = (user_id, *room_ids, user_id)
    out: Dict[int, int] = {rid: 0 for rid in room_ids}
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    for r in rows:
        out[int(r[0])] = int(r[1])
    return out
