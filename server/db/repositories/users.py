# SPDX-License-Identifier: GPL-3.0-or-later
"""users 테이블 repository — 회원가입 + 조회 + 인증 상태 갱신.

DDL 정합: ``server/db/migrations/0001_init.sql`` 의 `users` 테이블.
모든 함수 = pool 인스턴스 dependency injection 패턴.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class UserRow:
    """users row dataclass — repository 도메인 객체."""

    id: int
    email: str
    username: str
    password_hash: str
    email_verified: bool
    status: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]


async def insert_user(
    pool: Any,
    *,
    email: str,
    username: str,
    password_hash: str,
) -> int:
    """회원가입 시점 의 users row 신규 생성.

    Parameters
    ----------
    pool : asyncmy.Pool
        DB pool (server.db.connection.create_pool 산출).
    email : str
        로그인 식별자 (UNIQUE 검증 의무 — caller 사전 lookup).
    username : str
        표시 이름 (UNIQUE).
    password_hash : str
        PBKDF2-SHA256 해시 (app.core.security.hash_password 산출).

    Returns
    -------
    int
        신규 user.id (AUTO_INCREMENT 결과).
    """

    sql = (
        "INSERT INTO users (email, username, password_hash, email_verified, status) "
        "VALUES (%s, %s, %s, 0, 'active')"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email.lower(), username, password_hash))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_user_by_email(pool: Any, email: str) -> Optional[UserRow]:
    """email lookup — case-insensitive (소문자 normalize).

    Returns
    -------
    UserRow | None
        row 부재 시 None.
    """

    sql = (
        "SELECT id, email, username, password_hash, email_verified, status, "
        "       created_at, updated_at, last_login_at "
        "FROM users WHERE email = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (email.lower(),))
            row = await cur.fetchone()
    if row is None:
        return None
    return UserRow(*row)


async def get_user_by_username(pool: Any, username: str) -> Optional[UserRow]:
    """username lookup (case-sensitive)."""

    sql = (
        "SELECT id, email, username, password_hash, email_verified, status, "
        "       created_at, updated_at, last_login_at "
        "FROM users WHERE username = %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (username,))
            row = await cur.fetchone()
    if row is None:
        return None
    return UserRow(*row)


async def mark_email_verified(pool: Any, user_id: int) -> None:
    """OTP 검증 PASS 후 email_verified = 1 갱신.

    Notes
    -----
    호출자 = 이미 OTP 검증 PASS 검증 완료. 본 함수 = 단순 갱신.
    """

    sql = "UPDATE users SET email_verified = 1 WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
        await conn.commit()


async def update_last_login(pool: Any, user_id: int) -> None:
    """로그인 PASS 시점 의 last_login_at = NOW() 갱신."""

    sql = "UPDATE users SET last_login_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
        await conn.commit()


async def get_user_by_username_excluding(
    pool: Any,
    username: str,
    exclude_user_id: int,
) -> Optional[UserRow]:
    """username lookup — 특정 user_id 제외 (reclaim 의 의 self conflict 회피)."""

    sql = (
        "SELECT id, email, username, password_hash, email_verified, status, "
        "       created_at, updated_at, last_login_at "
        "FROM users WHERE username = %s AND id != %s"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (username, exclude_user_id))
            row = await cur.fetchone()
    if row is None:
        return None
    return UserRow(*row)


async def reclaim_unverified_user(
    pool: Any,
    *,
    user_id: int,
    username: str,
    password_hash: str,
) -> bool:
    """OTP 미검증 user row reclaim — username + password_hash + created_at 갱신.

    사용자 directive 회수 — `email_verified=0` 인 row 가 회원가입 재 진입 시
    기존 row 를 새 자격 정보로 덮어쓴다 (user_id 보존 → FK reference 안전).

    Notes
    -----
    H-1 회수 (reviewer 169.42) — 본 함수 단독 호출 시 race window 잔존. 동시 reclaim
    safe path = `reclaim_unverified_user_atomic` (단일 transaction + SELECT FOR UPDATE).
    본 함수는 backward compat + 단순 test mock 정합 한정.

    Returns
    -------
    bool
        UPDATE 성공 시 True (email_verified=0 AND id=user_id row 갱신).
        verified 가 1 로 race 진입한 경우 0 row → False.
    """

    sql = (
        "UPDATE users "
        "SET username = %s, password_hash = %s, "
        "    created_at = CURRENT_TIMESTAMP, "
        "    updated_at = CURRENT_TIMESTAMP "
        "WHERE id = %s AND email_verified = 0"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (username, password_hash, user_id))
            affected = cur.rowcount  # M-4 회수 — driver-agnostic rowcount 직접 read
        await conn.commit()
    return int(affected or 0) > 0


async def reclaim_unverified_user_atomic(
    pool: Any,
    *,
    email: str,
    username: str,
    password_hash: str,
) -> tuple[str, Optional[int]]:
    """단일 transaction + SELECT FOR UPDATE 안 reclaim chain (H-1 + M-2 회수).

    동시 reclaim 안 lost update 차단 + invalidate_pending ordering 역전 (verify race 차단).

    Flow (단일 connection + BEGIN..COMMIT):
        1. SELECT id, email_verified FROM users WHERE email=? FOR UPDATE
        2. row 부재 → return ("absent", None)
        3. email_verified=1 → ROLLBACK + return ("verified", None)
        4. SELECT id FROM users WHERE username=? AND id != ? — conflict check
        5. conflict → ROLLBACK + return ("username_conflict", None)
        6. UPDATE email_verification SET consumed_at=NOW WHERE email=? AND purpose='signup'
           AND consumed_at IS NULL  ← M-2 reclaim 이전 invalidate (verify race 차단)
        7. UPDATE users SET username, password_hash, created_at/updated_at=NOW WHERE id=?
        8. COMMIT

    Returns
    -------
    tuple[str, int | None]
        status:
            - "reclaimed" → reclaim PASS, second = user_id
            - "absent" → row 부재 (caller 가 신규 INSERT 진입)
            - "verified" → email_verified=1 (이전 검증 완료 사용자)
            - "verified_race" → email_verified=1 race (updated_at 5초 이내 동시 verify, cycle 169.70)
            - "username_conflict" → 다른 user 의 username 점유
    """

    # cycle 169.70 회수 — updated_at SELECT 추가 (EmailRaceVerified race detect)
    sql_select_user = (
        "SELECT id, email_verified, updated_at FROM users WHERE email = %s FOR UPDATE"
    )
    sql_select_uname = (
        "SELECT id FROM users WHERE username = %s AND id != %s LIMIT 1"
    )
    sql_invalidate_otp = (
        "UPDATE email_verification SET consumed_at = CURRENT_TIMESTAMP "
        "WHERE email = %s AND purpose = 'signup' AND consumed_at IS NULL"
    )
    sql_update_user = (
        "UPDATE users SET username = %s, password_hash = %s, "
        "created_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = %s"
    )

    email_norm = email.lower()
    async with pool.acquire() as conn:
        try:
            await conn.begin()
        except AttributeError:
            await conn.autocommit(False)

        try:
            async with conn.cursor() as cur:
                await cur.execute(sql_select_user, (email_norm,))
                row = await cur.fetchone()
                if row is None:
                    await conn.rollback()
                    return ("absent", None)
                user_id, email_verified = int(row[0]), int(row[1])
                updated_at = row[2] if len(row) > 2 else None
                if email_verified:
                    await conn.rollback()
                    # 한글 주석 — cycle 169.70 회수 — race detect — updated_at 5초 이내 시 EmailRaceVerified 분기
                    if updated_at is not None:
                        try:
                            from datetime import datetime, timedelta
                            now = datetime.now()
                            if hasattr(updated_at, "tzinfo") and updated_at.tzinfo is not None:
                                updated_at = updated_at.replace(tzinfo=None)
                            if abs((now - updated_at).total_seconds()) < 5:
                                return ("verified_race", None)
                        except Exception:
                            pass
                    return ("verified", None)

                await cur.execute(sql_select_uname, (username, user_id))
                conflict = await cur.fetchone()
                if conflict is not None:
                    await conn.rollback()
                    return ("username_conflict", None)

                # M-2 회수 — reclaim 이전 invalidate (verify race 차단)
                await cur.execute(sql_invalidate_otp, (email_norm,))
                await cur.execute(sql_update_user, (username, password_hash, user_id))
            await conn.commit()
            return ("reclaimed", user_id)
        except Exception:
            await conn.rollback()
            raise


async def update_password(pool: Any, user_id: int, new_hash: str) -> None:
    """비번 재설정 — password_hash 갱신.

    Parameters
    ----------
    new_hash : str
        신규 PBKDF2 해시 (app.core.security.hash_password 산출).
    """

    sql = "UPDATE users SET password_hash = %s WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (new_hash, user_id))
        await conn.commit()
