# SPDX-License-Identifier: GPL-3.0-or-later
"""password_reset 테이블 repository — 비번 재설정 토큰 발급 + 검증 + 소진."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ResetTokenRow:
    """password_reset row dataclass."""

    id: int
    user_id: int
    token_hash: str
    expires_at: datetime
    consumed_at: Optional[datetime]
    created_at: datetime


async def insert_reset_token(
    pool: Any,
    *,
    user_id: int,
    token_hash: str,
    ttl_seconds: int = 1800,
) -> int:
    """비번 재설정 토큰 발급 — 30분 default."""

    sql = (
        "INSERT INTO password_reset (user_id, token_hash, expires_at) "
        "VALUES (%s, %s, DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s SECOND))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, token_hash, ttl_seconds))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def find_active_token(pool: Any, token_hash: str) -> Optional[ResetTokenRow]:
    """미사용 + 미만료 토큰 lookup."""

    sql = (
        "SELECT id, user_id, token_hash, expires_at, consumed_at, created_at "
        "FROM password_reset "
        "WHERE token_hash = %s AND consumed_at IS NULL "
        "  AND expires_at > CURRENT_TIMESTAMP"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_hash,))
            row = await cur.fetchone()
    if row is None:
        return None
    return ResetTokenRow(*row)


async def consume_token(pool: Any, token_id: int) -> None:
    """토큰 사용 완료 — 재사용 차단."""

    sql = "UPDATE password_reset SET consumed_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
        await conn.commit()
