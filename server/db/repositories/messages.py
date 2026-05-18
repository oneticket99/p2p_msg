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
    """룸 의 최근 N건 (default 100) timeline."""

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


async def list_messages_in_range(
    pool: Any,
    *,
    room_id: int,
    start_ts: datetime,
    end_ts: datetime,
    limit: int = 1000,
) -> List[MessageRow]:
    """룸 의 [start_ts, end_ts) 구간 timeline — ChatView lazy load 의 server-side.

    사이클 60 신설 ([[feedback-chat-accumulation-memory-release-mandatory]] 정합).
    클라이언트 의 lazy load page fetch (default 30 일 batch) 의 query 의 source.

    Parameters
    ----------
    pool : Any
        asyncmy pool (또는 mock).
    room_id : int
        대상 room.
    start_ts : datetime
        구간 시작 (inclusive). UTC 또는 KST 의 정합 = caller responsibility.
    end_ts : datetime
        구간 끝 (exclusive).
    limit : int, default 1000
        page size 상한. unbounded SELECT 차단 의무 ([[feedback-chat-accumulation-memory-release-mandatory]]).

    Returns
    -------
    list[MessageRow]
        created_at 의 DESC + id DESC 의 정렬 (최신 → 과거). caller 의 reverse 의무.
    """

    if end_ts <= start_ts:
        raise ValueError(
            f"end_ts 의 start_ts 초과 의무 — start={start_ts} end={end_ts}"
        )
    if limit <= 0:
        raise ValueError(f"limit 양수 의무 — {limit}")
    sql = (
        "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
        "FROM messages WHERE room_id = %s "
        "AND created_at >= %s AND created_at < %s "
        "ORDER BY created_at DESC, id DESC LIMIT %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, start_ts, end_ts, limit))
            rows = await cur.fetchall()
    return [MessageRow(*row) for row in rows]
