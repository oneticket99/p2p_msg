# SPDX-License-Identifier: GPL-3.0-or-later
"""email_verification 테이블 repository — OTP 발급 + 검증 + 만료 cleanup.

DDL 정합: ``server/db/migrations/0001_init.sql`` 의 `email_verification` 테이블.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class OtpRow:
    """email_verification row dataclass."""

    id: int
    email: str
    purpose: str
    code_hash: str
    expires_at: datetime
    consumed_at: Optional[datetime]
    attempt_count: int
    created_at: datetime


async def insert_otp(
    pool: Any,
    *,
    email: str,
    purpose: str,
    code_hash: str,
    ttl_seconds: int = 180,
) -> int:
    """OTP 발급 — 3분 만료 default.

    Parameters
    ----------
    purpose : str
        'signup' 또는 'password_reset'.
    code_hash : str
        SHA-256 hex (app.core.security.hash_otp 산출).
    ttl_seconds : int
        만료 시각 = NOW() + ttl_seconds (default 180 = 3분).

    Returns
    -------
    int
        신규 email_verification.id.
    """

    sql = (
        "INSERT INTO email_verification (email, purpose, code_hash, expires_at) "
        "VALUES (%s, %s, %s, DATE_ADD(CURRENT_TIMESTAMP, INTERVAL %s SECOND))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email.lower(), purpose, code_hash, ttl_seconds))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def find_active_otp(
    pool: Any,
    *,
    email: str,
    purpose: str,
) -> Optional[OtpRow]:
    """미사용 + 미만료 OTP 의 최신 1건 lookup.

    Returns
    -------
    OtpRow | None
        조건 부합 row 부재 시 None.
    """

    sql = (
        "SELECT id, email, purpose, code_hash, expires_at, consumed_at, "
        "       attempt_count, created_at "
        "FROM email_verification "
        "WHERE email = %s AND purpose = %s "
        "  AND consumed_at IS NULL "
        "  AND expires_at > CURRENT_TIMESTAMP "
        "  AND attempt_count < 5 "
        "ORDER BY id DESC LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email.lower(), purpose))
            row = await cur.fetchone()
    if row is None:
        return None
    return OtpRow(*row)


async def increment_attempt(pool: Any, otp_id: int) -> int:
    """검증 시도 +1 — 5회 초과 시 본 row 무효 (find_active_otp 의 의 의 의 의 의 의 의 자동 제외).

    Returns
    -------
    int
        갱신 후 attempt_count.
    """

    sql_update = "UPDATE email_verification SET attempt_count = attempt_count + 1 WHERE id = %s"
    sql_read = "SELECT attempt_count FROM email_verification WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql_update, (otp_id,))
            await cur.execute(sql_read, (otp_id,))
            row = await cur.fetchone()
        await conn.commit()
    return int(row[0]) if row else 0


async def consume_otp(pool: Any, otp_id: int) -> None:
    """검증 PASS 시점 의 consumed_at = NOW() 갱신 (재사용 차단)."""

    sql = "UPDATE email_verification SET consumed_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (otp_id,))
        await conn.commit()


async def cleanup_expired(pool: Any) -> int:
    """만료 + 사용 완료 + 24시간 경과 row 삭제 (cron 호출).

    Returns
    -------
    int
        삭제된 row 수.
    """

    sql = (
        "DELETE FROM email_verification "
        "WHERE (consumed_at IS NOT NULL AND consumed_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 DAY)) "
        "   OR (expires_at < DATE_SUB(CURRENT_TIMESTAMP, INTERVAL 1 DAY))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            rows = await cur.execute(sql)
        await conn.commit()
    return int(rows or 0)
