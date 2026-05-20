# SPDX-License-Identifier: GPL-3.0-or-later
"""folders + folder_chats + folder_invites repository (cycle 169.76 신설).

DDL 정합: server/db/migrations/0009_folders.sql.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class FolderRow:
    id: int
    folder_id: str
    owner_id: int
    name: str
    color_name: Optional[str]
    color_hex: Optional[str]
    chat_count: int
    created_at: datetime


async def insert_folder(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
) -> int:
    """folder INSERT — folder_id (uuid 8자) + owner_id + name + color."""
    sql = (
        "INSERT INTO folders (folder_id, owner_id, name, color_name, color_hex) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id, name, color_name, color_hex))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def list_folders(pool: Any, owner_id: int) -> List[FolderRow]:
    sql = (
        "SELECT id, folder_id, owner_id, name, color_name, color_hex, chat_count, created_at "
        "FROM folders WHERE owner_id = %s ORDER BY id ASC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (owner_id,))
            rows = await cur.fetchall()
    return [FolderRow(*row) for row in rows]


async def delete_folder(pool: Any, folder_id: str, owner_id: int) -> bool:
    sql = "DELETE FROM folders WHERE folder_id = %s AND owner_id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id))
            affected = cur.rowcount
        await conn.commit()
    return int(affected or 0) > 0


async def add_folder_chat(
    pool: Any,
    *,
    folder_pk: int,
    chat_kind: str,
    chat_target_id: int,
    mode: str = "include",
) -> int:
    sql = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk, chat_kind, chat_target_id, mode))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id) if new_id else 0


async def create_invite(pool: Any, *, folder_pk: int, created_by: int) -> str:
    """초대 link token 생성 — folder_invites row insert."""
    token = secrets.token_hex(16)
    sql = (
        "INSERT INTO folder_invites (folder_id, invite_token, created_by) "
        "VALUES (%s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk, token, created_by))
        await conn.commit()
    return token
