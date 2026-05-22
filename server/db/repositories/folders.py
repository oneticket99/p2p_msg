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


async def list_folder_chats(pool: Any, folder_pk: int) -> dict:
    """cycle 169.387 — folder_chats list fetch (included + excluded 분리).

    사용자 critique image #148 회수 — server response 안 included_chats / excluded_chats
    field 부재 root cause. folder_chats JOIN chain 활성.
    """
    sql = (
        "SELECT chat_kind, chat_target_id, mode FROM folder_chats "
        "WHERE folder_id = %s"
    )
    included: list = []
    excluded: list = []
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk,))
            rows = await cur.fetchall()
    for kind, tid, mode in rows or []:
        entry = {"kind": kind, "target_id": int(tid)}
        if mode == "exclude":
            excluded.append(entry)
        else:
            included.append(entry)
    return {"included_chats": included, "excluded_chats": excluded}


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


async def fetch_by_folder_id_and_owner(
    pool: Any, folder_id: str, owner_id: int,
) -> Optional[FolderRow]:
    """단일 SELECT — owner check + folder_id 정합 (cycle 169.79 MED-1 회수)."""
    sql = (
        "SELECT id, folder_id, owner_id, name, color_name, color_hex, chat_count, created_at "
        "FROM folders WHERE folder_id = %s AND owner_id = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_id, owner_id))
            row = await cur.fetchone()
    return FolderRow(*row) if row is not None else None


async def insert_folder_with_chats(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
    included_chats: Optional[list] = None,
    excluded_chats: Optional[list] = None,
) -> int:
    """folder + chats batch — 단일 transaction (cycle 169.79 HIGH-2 회수)."""
    sql_folder = (
        "INSERT INTO folders (folder_id, owner_id, name, color_name, color_hex, chat_count) "
        "VALUES (%s, %s, %s, %s, %s, %s)"
    )
    sql_chat = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    included_chats = included_chats or []
    excluded_chats = excluded_chats or []
    chat_count_cache = len(included_chats)
    async with pool.acquire() as conn:
        try:
            await conn.begin()
        except AttributeError:
            await conn.autocommit(False)
        try:
            async with conn.cursor() as cur:
                await cur.execute(
                    sql_folder,
                    (folder_id, owner_id, name, color_name, color_hex, chat_count_cache),
                )
                new_id = cur.lastrowid
                for chat in included_chats:
                    await cur.execute(
                        sql_chat,
                        (new_id, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "include"),
                    )
                for chat in excluded_chats:
                    await cur.execute(
                        sql_chat,
                        (new_id, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "exclude"),
                    )
            await conn.commit()
            return int(new_id)
        except Exception:
            await conn.rollback()
            raise


async def update_folder_with_chats(
    pool: Any,
    *,
    folder_id: str,
    owner_id: int,
    name: str,
    color_name: Optional[str] = None,
    color_hex: Optional[str] = None,
    included_chats: Optional[list] = None,
    excluded_chats: Optional[list] = None,
) -> bool:
    """cycle 169.411 — folder edit mode 의 server UPDATE chain (Phase 1 잔존 회수).

    단일 transaction 안 sequence:
    1. folders UPDATE (name + color + chat_count + updated_at) — owner_id 정합 의무
    2. folder_chats DELETE (folder_pk 기준 전수 삭제)
    3. folder_chats INSERT batch (included + excluded reconciliation)

    Returns True = UPDATE PASS (1+ row affected). False = folder_id 부재 또는 권한 부재.
    """
    sql_update = (
        "UPDATE folders SET name = %s, color_name = %s, color_hex = %s, chat_count = %s "
        "WHERE folder_id = %s AND owner_id = %s"
    )
    sql_delete_chats = "DELETE FROM folder_chats WHERE folder_id = %s"
    sql_insert_chat = (
        "INSERT IGNORE INTO folder_chats (folder_id, chat_kind, chat_target_id, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    included_chats = included_chats or []
    excluded_chats = excluded_chats or []
    chat_count_cache = len(included_chats)
    async with pool.acquire() as conn:
        try:
            await conn.begin()
        except AttributeError:
            await conn.autocommit(False)
        try:
            async with conn.cursor() as cur:
                # 한글 주석 — folder lookup 의 의 PK 확보
                row = None
                await cur.execute(
                    "SELECT id FROM folders WHERE folder_id = %s AND owner_id = %s LIMIT 1",
                    (folder_id, owner_id),
                )
                row = await cur.fetchone()
                if row is None:
                    await conn.rollback()
                    return False
                folder_pk = int(row[0])
                # 한글 주석 — folders UPDATE
                await cur.execute(
                    sql_update,
                    (name, color_name, color_hex, chat_count_cache, folder_id, owner_id),
                )
                # 한글 주석 — folder_chats 전수 DELETE + reconciliation
                await cur.execute(sql_delete_chats, (folder_pk,))
                for chat in included_chats:
                    await cur.execute(
                        sql_insert_chat,
                        (folder_pk, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "include"),
                    )
                for chat in excluded_chats:
                    await cur.execute(
                        sql_insert_chat,
                        (folder_pk, str(chat.get("kind", "")), int(chat.get("target_id", 0)), "exclude"),
                    )
            await conn.commit()
            return True
        except Exception:
            await conn.rollback()
            raise


async def create_invite(
    pool: Any,
    *,
    folder_pk: int,
    created_by: int,
    expires_days: int = 7,
) -> str:
    """초대 link token 생성 — folder_invites row insert + 7일 default expires (cycle 169.79 LOW-1)."""
    token = secrets.token_hex(16)
    sql = (
        "INSERT INTO folder_invites (folder_id, invite_token, created_by, expires_at) "
        "VALUES (%s, %s, %s, DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s DAY))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (folder_pk, token, created_by, expires_days))
        await conn.commit()
    return token
