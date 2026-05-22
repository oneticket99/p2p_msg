# SPDX-License-Identifier: GPL-3.0-or-later
"""email_verification 테이블 repository — OTP 발급 + 검증 + 만료 cleanup.

DDL 정합: ``server/db/migrations/0001_init.sql`` 의 `email_verification` 테이블.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable, Optional, TypeVar

log = logging.getLogger(__name__)

_T = TypeVar("_T")


async def _retry_on_record_changed(
    op_name: str,
    coro_factory: Callable[[], Awaitable[_T]],
    max_attempts: int = 4,
) -> _T:
    """cycle 169.480 — MariaDB error 1020 ('Record has changed since last read') retry helper.

    asyncmy + InnoDB 안 transient race (cursor reuse + pool connection reuse) 시점 1020 발생.
    Idempotent UPDATE/SELECT 의 retry safe — exponential backoff (50/100/150/200ms) 4회 시도.

    Parameters
    ----------
    op_name : str
        log + error context 의 의무 operation name.
    coro_factory : Callable
        매 retry 시 새 coroutine 생성 의무 (재 await 부재 — coroutine single-shot).
    """
    from asyncmy.errors import OperationalError

    last_exc: Optional[Exception] = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except OperationalError as exc:
            # 한글 주석 — error 1020 만 retry. 외 OperationalError 즉시 raise.
            if getattr(exc, "args", [None])[0] != 1020:
                raise
            last_exc = exc
            log.warning(
                "[%s] MariaDB error 1020 — retry %d/%d",
                op_name, attempt + 1, max_attempts,
            )
            await asyncio.sleep(0.05 * (attempt + 1))
    # 한글 주석 — 모든 retry fail 시 마지막 exception 재 raise (silent failure 차단)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError(f"_retry_on_record_changed[{op_name}] unreachable")


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
    """검증 시도 +1 — 5회 초과 시 본 row 무효 (find_active_otp 자동 제외).

    cycle 169.480 — MariaDB error 1020 retry chain 적용 (idempotent counter increment 부재 의
    의무 안 SELECT-after-UPDATE 의 cursor 의 결과 capture).

    Returns
    -------
    int
        갱신 후 attempt_count.
    """

    sql_update = "UPDATE email_verification SET attempt_count = attempt_count + 1 WHERE id = %s"
    sql_read = "SELECT attempt_count FROM email_verification WHERE id = %s"

    async def _op() -> int:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql_update, (otp_id,))
                await cur.execute(sql_read, (otp_id,))
                row = await cur.fetchone()
            await conn.commit()
        return int(row[0]) if row else 0

    return await _retry_on_record_changed("increment_attempt", _op)


async def consume_otp(pool: Any, otp_id: int) -> None:
    """검증 PASS 시점 의 consumed_at = NOW() 갱신 (재사용 차단).

    cycle 169.476 + 169.480 — MariaDB error 1020 retry chain 적용 (helper 통합).
    """

    sql = "UPDATE email_verification SET consumed_at = CURRENT_TIMESTAMP WHERE id = %s"

    async def _op() -> None:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, (otp_id,))
            await conn.commit()

    await _retry_on_record_changed("consume_otp", _op)


async def invalidate_pending(pool: Any, *, email: str, purpose: str) -> int:
    """미사용 OTP row 모두 consumed_at=NOW() force — reclaim 시 prior OTP 무효화.

    사용자 directive 회수 — OTP 입력 부재 종료 후 재 가입 진입 시
    prior pending OTP 가 남아있어 attempt_count abuse + 만료 race 가 발생한다.
    본 함수는 consumed_at 강제 set 으로 find_active_otp 검색에서 제외시킨다.

    Returns
    -------
    int
        무효화된 row 수.
    """

    sql = (
        "UPDATE email_verification "
        "SET consumed_at = CURRENT_TIMESTAMP "
        "WHERE email = %s AND purpose = %s AND consumed_at IS NULL"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            affected = await cur.execute(sql, (email.lower(), purpose))
        await conn.commit()
    return int(affected or 0)


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
