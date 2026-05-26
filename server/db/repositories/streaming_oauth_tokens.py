# SPDX-License-Identifier: GPL-3.0-or-later
"""streaming_oauth_tokens 테이블 repository — 방송 플랫폼 OAuth2 토큰 영속 (Phase 5 cycle 169.486).

역할
----
방송 도우미 봇(나이트봇 등가)이 외부 방송 플랫폼 API 를 호출하기 위한 OAuth2 토큰(access/refresh +
만료/스코프/채널)을 사용자·플랫폼별로 영속한다. 4 platform — Twitch + YouTube + CHZZK + Kick.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = streaming OAuth handler / cron refresh chain.
DDL 정합: ``server/db/migrations/0016_streaming_oauth_tokens.sql``.

보안 / invariant
---------------
- (user_id, platform) UNIQUE — 사용자·플랫폼당 토큰 1건. upsert(ON DUPLICATE KEY)의 근거.
- platform 은 4 ENUM(_PLATFORMS) — 그 외 값은 DB 도달 전 ValueError fail-fast.
- access_token/refresh_token 은 민감 정보 — 로그/보고에 평문 노출 금지(호출자 redact 책임).
- 5 공개 함수 — upsert_token + get_token + list_tokens_by_user + delete_token + list_expiring_tokens.

부작용
------
upsert/delete 는 write(commit). get/list 류는 부작용 없음(SELECT only).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OAuthTokenRow:
    """streaming_oauth_tokens 단일 row 의 read-only 투영 — 12 column 정합.

    불변식: frozen + 필드 순서 = SELECT 컬럼 1:1. ``refresh_token`` None = refresh 불가(재인증 필요),
    ``expires_at`` = access_token 만료 시각(refresh chain trigger 기준). access/refresh_token = 민감.
    """

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
    """OAuth token UPSERT — (user_id, platform) UNIQUE. row PK 반환.

    의도: OAuth 인증 완료/갱신 시 토큰 저장. 같은 사용자·플랫폼 재인증이면 INSERT 대신
    토큰/만료/채널을 전부 최신값으로 덮어쓴다(ON DUPLICATE KEY). UPSERT 후 별도 SELECT 로
    PK 를 재조회해 반환(driver 의 ON DUPLICATE lastrowid 불확실성 회피). 부작용: upsert + commit.

    Raises
    ------
    ValueError
        platform 이 4 ENUM(twitch/youtube/chzzk/kick) 외.

    Returns
    -------
    int
        token row PK (조회 실패 시 0).
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
    """사용자·platform 의 OAuth token row 단건 조회. 부재 시 None. 부작용 없음.

    의도: 방송 플랫폼 API 호출 직전 토큰 로드. 호출자는 expires_at 으로 만료/갱신 여부 판단.

    Raises
    ------
    ValueError
        platform 이 4 ENUM 외.
    """
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
    """사용자의 전 platform OAuth token 조회 — platform 정렬. 부작용 없음(SELECT only).

    의도: 연동 관리 화면 — 어떤 방송 플랫폼이 연결됐는지 일괄 표시.
    """
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
    """사용자·platform 의 token 삭제(hard). 삭제 row 수 반환. 부작용: DELETE + commit.

    의도: 연동 해제. **OAuth revoke API 호출 후** 본 함수로 로컬 토큰을 제거하는 순서가 의무다
    (DB 만 지우고 플랫폼 쪽 토큰이 유효하면 좀비 권한 잔존). password_reset 의 soft 와 달리 hard delete.

    Raises
    ------
    ValueError
        platform 이 4 ENUM 외.

    Returns
    -------
    int
        삭제된 row 수(0 또는 1).
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
    """만료 임박 token 조회 — cron refresh chain 의 입력. 부작용 없음(SELECT only).

    의도: 백그라운드 갱신 작업이 "곧 만료될 + refresh 가능한" 토큰을 선제 갱신하도록 후보 산출.
    WHERE 에 ``refresh_token IS NOT NULL`` 을 둬 갱신 불가(재인증 필요) 토큰은 제외한다.

    Parameters
    ----------
    within_seconds : int
        현재 시각 + within_seconds 안에 만료될 token 을 대상으로(default 300=5분).

    Returns
    -------
    list[OAuthTokenRow]
        만료 임박 순(expires_at ASC). 부재 시 빈 list.
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
