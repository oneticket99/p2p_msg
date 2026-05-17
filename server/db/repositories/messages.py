# SPDX-License-Identifier: GPL-3.0-or-later
"""messages 테이블 repository — 텍스트/파일/시스템 메시지 history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class MessageRow:
    """messages row dataclass."""

    id: int
    room_id: int
    sender_id: int
    kind: str
    body: Optional[str]
    file_id: Optional[str]
    created_at: datetime


async def insert_text_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> int:
    """텍스트 메시지 기록. kind=text + body 본문."""

    sql = (
        "INSERT INTO messages (room_id, sender_id, kind, body) "
        "VALUES (%s, %s, 'text', %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, sender_id, body))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def insert_file_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    file_id: str,
) -> int:
    """파일 메시지 기록. kind=file + file_meta 참조."""

    sql = (
        "INSERT INTO messages (room_id, sender_id, kind, file_id) "
        "VALUES (%s, %s, 'file', %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, sender_id, file_id))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def insert_system_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> int:
    """시스템 알림 (join/leave/owner change). sender_id = 작업 주체."""

    sql = (
        "INSERT INTO messages (room_id, sender_id, kind, body) "
        "VALUES (%s, %s, 'system', %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, sender_id, body))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def list_recent(
    pool: Any,
    *,
    room_id: int,
    limit: int = 100,
) -> List[MessageRow]:
    """룸 의 최근 N건 (default 100) 의 의 의 의 의 의 의 의 의 의 의 timeline."""

    sql = (
        "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
        "FROM messages WHERE room_id = %s "
        "ORDER BY created_at DESC, id DESC LIMIT %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, limit))
            rows = await cur.fetchall()
    return [MessageRow(*row) for row in rows]
