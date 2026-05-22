# SPDX-License-Identifier: GPL-3.0-or-later
"""bots + bot_tokens repository — Phase 3+ bot framework BotFather 등가 (cycle 169.420 신설).

DDL 정합: `server/db/migrations/0012_bots.sql`.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class BotRow:
    """bots row dataclass."""

    id: int
    owner_user_id: int
    name: str
    username: str
    description: Optional[str]
    webhook_url: Optional[str]
    inline_enabled: bool
    is_public: bool
    status: str
    created_at: datetime


def _hash_token(token: str) -> str:
    """token plaintext → SHA-256 hex (64 lowercase)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_bot_token() -> tuple[str, str]:
    """봇 token plaintext + hash 생성. 한글 주석 — 사용자 directive 보안 의무.

    Returns
    -------
    tuple[str, str]
        (plaintext token, sha256 hex). plaintext = caller 응답 1회 노출 + DB 저장 부재.
    """
    plaintext = f"bot_{secrets.token_urlsafe(32)}"
    return plaintext, _hash_token(plaintext)


async def insert_bot(
    pool: Any, *, owner_user_id: int, name: str, username: str,
    description: Optional[str] = None, webhook_url: Optional[str] = None,
    inline_enabled: bool = False, is_public: bool = False,
) -> int:
    """신규 봇 INSERT — 반환값 = bot.id."""
    if owner_user_id <= 0:
        raise ValueError(f"owner_user_id 양수 의무 — {owner_user_id}")
    if not name or len(name) > 64:
        raise ValueError(f"name 1~64자 의무 — len={len(name)}")
    if not username or len(username) > 32:
        raise ValueError(f"username 1~32자 의무 — len={len(username)}")
    if description is not None and len(description) > 255:
        raise ValueError(f"description 255자 cap — len={len(description)}")
    if webhook_url is not None and len(webhook_url) > 512:
        raise ValueError(f"webhook_url 512자 cap — len={len(webhook_url)}")

    sql = (
        "INSERT INTO bots (owner_user_id, name, username, description, "
        "webhook_url, inline_enabled, is_public) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (
                owner_user_id, name, username, description, webhook_url,
                1 if inline_enabled else 0, 1 if is_public else 0,
            ))
            bot_id = int(cur.lastrowid)
        await conn.commit()
    return bot_id


async def insert_bot_token(
    pool: Any, *, bot_id: int, label: Optional[str] = None,
) -> tuple[str, int]:
    """봇 token 생성 + DB INSERT — 반환값 = (plaintext, token_id).

    한글 주석 — plaintext 의 응답 1회 노출 만 가능 (DB 저장 부재).
    """
    if bot_id <= 0:
        raise ValueError(f"bot_id 양수 의무 — {bot_id}")
    plaintext, token_hash = generate_bot_token()
    sql = "INSERT INTO bot_tokens (bot_id, token_hash, label) VALUES (%s, %s, %s)"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (bot_id, token_hash, label))
            token_id = int(cur.lastrowid)
        await conn.commit()
    return plaintext, token_id


async def get_bot_by_username(pool: Any, username: str) -> Optional[BotRow]:
    """username 기준 단일 SELECT (UNIQUE)."""
    sql = (
        "SELECT id, owner_user_id, name, username, description, webhook_url, "
        "inline_enabled, is_public, status, created_at FROM bots WHERE username = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (username,))
            row = await cur.fetchone()
    if row is None:
        return None
    return BotRow(
        id=int(row[0]), owner_user_id=int(row[1]), name=str(row[2]),
        username=str(row[3]), description=row[4], webhook_url=row[5],
        inline_enabled=bool(row[6]), is_public=bool(row[7]),
        status=str(row[8]), created_at=row[9],
    )


async def list_public_bots(
    pool: Any, *, limit: int = 50, offset: int = 0,
) -> List[BotRow]:
    """공개 + active 봇 list — 디렉토리 페이지 chain."""
    if limit <= 0 or limit > 200:
        raise ValueError(f"limit 1~200 의무 — {limit}")
    if offset < 0:
        raise ValueError(f"offset 음수 차단 — {offset}")
    sql = (
        "SELECT id, owner_user_id, name, username, description, webhook_url, "
        "inline_enabled, is_public, status, created_at FROM bots "
        "WHERE is_public = 1 AND status = 'active' "
        "ORDER BY id DESC LIMIT %s OFFSET %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (limit, offset))
            rows = await cur.fetchall()
    return [
        BotRow(
            id=int(r[0]), owner_user_id=int(r[1]), name=str(r[2]),
            username=str(r[3]), description=r[4], webhook_url=r[5],
            inline_enabled=bool(r[6]), is_public=bool(r[7]),
            status=str(r[8]), created_at=r[9],
        )
        for r in rows
    ]


async def authenticate_bot_token(pool: Any, plaintext: str) -> Optional[BotRow]:
    """token plaintext → SHA-256 lookup → bot row return.

    revoked_at IS NULL + bot status='active' 의 의무 chain.
    last_used_at NOW() 갱신.
    """
    if not plaintext:
        return None
    token_hash = _hash_token(plaintext)
    sql = (
        "SELECT b.id, b.owner_user_id, b.name, b.username, b.description, "
        "       b.webhook_url, b.inline_enabled, b.is_public, b.status, b.created_at, "
        "       t.id AS token_id "
        "FROM bot_tokens t JOIN bots b ON t.bot_id = b.id "
        "WHERE t.token_hash = %s AND t.revoked_at IS NULL AND b.status = 'active' "
        "LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_hash,))
            row = await cur.fetchone()
            if row is None:
                return None
            # last_used_at 갱신 (graceful)
            try:
                await cur.execute(
                    "UPDATE bot_tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = %s",
                    (int(row[10]),),
                )
                await conn.commit()
            except Exception:
                pass
    return BotRow(
        id=int(row[0]), owner_user_id=int(row[1]), name=str(row[2]),
        username=str(row[3]), description=row[4], webhook_url=row[5],
        inline_enabled=bool(row[6]), is_public=bool(row[7]),
        status=str(row[8]), created_at=row[9],
    )


async def revoke_bot_token(pool: Any, *, token_id: int) -> bool:
    """token revoke — revoked_at NOW() UPDATE. 반환값 = rowcount > 0."""
    if token_id <= 0:
        raise ValueError(f"token_id 양수 의무 — {token_id}")
    sql = "UPDATE bot_tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = %s AND revoked_at IS NULL"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
            rowcount = int(cur.rowcount or 0)
        await conn.commit()
    return rowcount > 0


async def list_owner_bots(pool: Any, *, owner_user_id: int) -> List[BotRow]:
    """owner_user_id 의 봇 list (status 무관 — owner self 영역)."""
    if owner_user_id <= 0:
        raise ValueError(f"owner_user_id 양수 의무 — {owner_user_id}")
    sql = (
        "SELECT id, owner_user_id, name, username, description, webhook_url, "
        "inline_enabled, is_public, status, created_at FROM bots "
        "WHERE owner_user_id = %s ORDER BY id DESC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (owner_user_id,))
            rows = await cur.fetchall()
    return [
        BotRow(
            id=int(r[0]), owner_user_id=int(r[1]), name=str(r[2]),
            username=str(r[3]), description=r[4], webhook_url=r[5],
            inline_enabled=bool(r[6]), is_public=bool(r[7]),
            status=str(r[8]), created_at=r[9],
        )
        for r in rows
    ]
