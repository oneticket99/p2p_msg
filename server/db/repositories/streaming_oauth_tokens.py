# SPDX-License-Identifier: GPL-3.0-or-later
"""streaming_oauth_tokens 테이블 repository — Phase 5 cycle 169.486.

4 platform OAuth2 token persistence — Twitch + YouTube + CHZZK + Kick.
사용자 + platform 단일 row UNIQUE (UPSERT chain).

DDL 정합: ``server/db/migrations/0016_streaming_oauth_tokens.sql``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OAuthTokenRow:
    """streaming_oauth_tokens row dataclass."""

    id: int
    user_id: int
    platform: str
    access_token: str
    refresh_token: Optional[str]
    expires_at: datetime
    scopes: Optional[str]
    token_type: str
    channel_id: Optional[str]
    channel_login: Optional[str]
    created_at: datetime
    updated_at: datetime


_PLATFORMS = ("twitch", "youtube", "chzzk", "kick")


async def upsert_token(
    pool: Any,
    *,
    user_id: int,
    platform: str,
    access_token: str,
    refresh_token: Optional[str],
    expires_at: datetime,
    scopes: Optional[str] = None,
    token_type: str = "Bearer",
    channel_id: Optional[str] = None,
    channel_login: Optional[str] = None,
) -> int:
    """OAuth token UPSERT — 사용자 + platform UNIQUE 정합.

    Returns
    -------
    int
        token row PK (신규 INSERT id 또는 기존 row id).
    """
    if platform not in _PLATFORMS:
        raise ValueError(f"platform={platform!r} 부재 — 4 platform 의 한정")

    sql = (
        "INSERT INTO streaming_oauth_tokens "
        "(user_id, platform, access_token, refresh_token, expires_at, scopes, "
        "token_type, channel_id, channel_login) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "access_token = VALUES(access_token), "
        "refresh_token = VALUES(refresh_token), "
        "expires_at = VALUES(expires_at), "
        "scopes = VALUES(scopes), "
        "token_type = VALUES(token_type), "
        "channel_id = VALUES(channel_id), "
        "channel_login = VALUES(channel_login)"
    )
    sql_select = (
        "SELECT id FROM streaming_oauth_tokens WHERE user_id = %s AND platform = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                sql,
                (
                    user_id, platform, access_token, refresh_token, expires_at,
                    scopes, token_type, channel_id, channel_login,
                ),
            )
            await cur.execute(sql_select, (user_id, platform))
            row = await cur.fetchone()
        await conn.commit()
    return int(row[0]) if row else 0


async def get_token(
    pool: Any, *, user_id: int, platform: str,
) -> Optional[OAuthTokenRow]:
    """사용자 + platform 의 OAuth token row 조회."""
    if platform not in _PLATFORMS:
        raise ValueError(f"platform={platform!r} 부재")

    sql = (
        "SELECT id, user_id, platform, access_token, refresh_token, expires_at, "
        "scopes, token_type, channel_id, channel_login, created_at, updated_at "
        "FROM streaming_oauth_tokens WHERE user_id = %s AND platform = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, platform))
            row = await cur.fetchone()
    if row is None:
        return None
    return OAuthTokenRow(*row)


async def list_tokens_by_user(pool: Any, *, user_id: int) -> list[OAuthTokenRow]:
    """사용자 의 platform 전수 OAuth token 조회."""
    sql = (
        "SELECT id, user_id, platform, access_token, refresh_token, expires_at, "
        "scopes, token_type, channel_id, channel_login, created_at, updated_at "
        "FROM streaming_oauth_tokens WHERE user_id = %s ORDER BY platform"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id,))
            rows = await cur.fetchall()
    return [OAuthTokenRow(*row) for row in rows]


async def delete_token(pool: Any, *, user_id: int, platform: str) -> int:
    """사용자 + platform 의 token 삭제 — OAuth revoke 후 호출 의무.

    Returns
    -------
    int
        삭제된 row 수 (0 또는 1).
    """
    if platform not in _PLATFORMS:
        raise ValueError(f"platform={platform!r} 부재")

    sql = "DELETE FROM streaming_oauth_tokens WHERE user_id = %s AND platform = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, platform))
            affected = cur.rowcount
        await conn.commit()
    return int(affected or 0)


async def list_expiring_tokens(
    pool: Any, *, within_seconds: int = 300,
) -> list[OAuthTokenRow]:
    """만료 임박 token 조회 — cron refresh chain base.

    Parameters
    ----------
    within_seconds : int
        현재 시각 + within_seconds 안 만료 token detect (default 5분).
    """
    sql = (
        "SELECT id, user_id, platform, access_token, refresh_token, expires_at, "
        "scopes, token_type, channel_id, channel_login, created_at, updated_at "
        "FROM streaming_oauth_tokens "
        "WHERE expires_at <= DATE_ADD(NOW(), INTERVAL %s SECOND) "
        "  AND refresh_token IS NOT NULL "
        "ORDER BY expires_at ASC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (within_seconds,))
            rows = await cur.fetchall()
    return [OAuthTokenRow(*row) for row in rows]
