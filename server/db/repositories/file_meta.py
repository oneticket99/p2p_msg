# SPDX-License-Identifier: GPL-3.0-or-later
"""file_meta 테이블 repository — Agent #16 파일 송수신 영속화."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class FileMetaRow:
    """file_meta row dataclass."""

    id: int
    file_id: str
    room_id: int
    sender_id: int
    name: str
    size: int
    mime: str
    sha256: str
    status: str
    thumbnail_base64: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


async def insert_file_meta(
    pool: Any,
    *,
    file_id: str,
    room_id: int,
    sender_id: int,
    name: str,
    size: int,
    mime: str,
    sha256: str,
    thumbnail_base64: Optional[str] = None,
) -> int:
    """FILE_META 수신 시점 의 row 생성. status=uploading."""

    sql = (
        "INSERT INTO file_meta (file_id, room_id, sender_id, name, size, "
        "                       mime, sha256, status, thumbnail_base64) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, 'uploading', %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (file_id, room_id, sender_id, name, size, mime, sha256, thumbnail_base64),
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def mark_completed(pool: Any, file_id: str) -> None:
    """FILE_DONE 수신 시점 의 status=completed + completed_at=NOW()."""

    sql = (
        "UPDATE file_meta SET status = 'completed', "
        "                     completed_at = CURRENT_TIMESTAMP "
        "WHERE file_id = %s AND status = 'uploading'"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
        await conn.commit()


async def mark_failed(pool: Any, file_id: str) -> None:
    """오류 시점 의 status=failed."""

    sql = "UPDATE file_meta SET status = 'failed' WHERE file_id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
        await conn.commit()


async def get_by_file_id(pool: Any, file_id: str) -> Optional[FileMetaRow]:
    """file_id (UUID hex) lookup."""

    sql = (
        "SELECT id, file_id, room_id, sender_id, name, size, mime, sha256, "
        "       status, thumbnail_base64, created_at, completed_at "
        "FROM file_meta WHERE file_id = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (file_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return FileMetaRow(*row)
