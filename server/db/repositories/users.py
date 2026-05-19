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
            affected = await cur.execute(sql, (username, password_hash, user_id))
        await conn.commit()
    return int(affected or 0) > 0


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
