# SPDX-License-Identifier: GPL-3.0-or-later
"""bots + bot_tokens repository — bot framework BotFather 등가 (Phase 3+, cycle 169.420 신설).

역할
----
봇 등록·조회·공개 디렉토리와 봇 인증 토큰(발급/검증/revoke)을 영속한다. 텔레그램 BotFather 등가.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = bot 관리 handler + bot API 인증 미들웨어.
DDL 정합: ``server/db/migrations/0012_bots.sql``.

보안 / invariant
---------------
- **토큰 평문 비저장** — bot_tokens 에는 ``token_hash``(SHA-256)만. 평문은 발급 응답 1회만 노출.
- 인증 = 평문 → SHA-256 → ``revoked_at IS NULL`` AND bot ``status='active'`` 조회(authenticate_bot_token).
  성공 시 last_used_at 갱신(graceful — 갱신 실패해도 인증 자체는 통과).
- revoke = soft(revoked_at 기록). 입력 검증(owner/name/username/길이) DB 도달 전 ValueError fail-fast.
- 8 공개 함수 — generate_bot_token + insert_bot + insert_bot_token + get_bot_by_username +
  list_public_bots + authenticate_bot_token + revoke_bot_token + list_owner_bots(+ _hash_token 내부).

부작용
------
insert/revoke/authenticate(last_used 갱신) 는 write. get/list 는 부작용 없음. generate/_hash_token 은 순수.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class BotRow:
    """bots 단일 row 의 read-only 투영 — 10 column.

    불변식: frozen. ``status`` = active/disabled 등, ``is_public`` True 만 디렉토리 노출,
    ``inline_enabled`` = 인라인 모드 허용. 토큰은 본 row 에 없음(bot_tokens 분리).
    """

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
    """username(UNIQUE) 기준 봇 단건 조회. 부재 시 None. 부작용 없음(SELECT only).

    의도: @username 멘션/딥링크로 봇 식별. 토큰 미포함(BotRow) — 인증은 authenticate_bot_token.
    """
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
    """공개(is_public=1) + active 봇 list — 디렉토리 페이지. 부작용 없음(SELECT only).

    의도: 누구나 탐색 가능한 봇 디렉토리. is_public=0/비active 봇은 제외. limit 상한(1..200)으로
    unbounded SELECT 차단. 부재/권한은 list_owner_bots(소유자 전용, status 무관)와 분리.

    Raises
    ------
    ValueError
        limit 범위(1..200) 또는 offset 음수 위반.
    """
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
    """token 평문 → SHA-256 lookup → 인증된 bot row 반환. 실패 시 None.

    의도: bot API 요청의 Bearer 토큰 인증. 평문을 해시해 bot_tokens JOIN bots 조회 —
    ``revoked_at IS NULL`` AND bot ``status='active'`` 둘 다 통과해야 인증. 성공 시 last_used_at 을
    갱신하되 그 UPDATE 실패는 graceful(인증 결과는 보존). 부작용: last_used_at UPDATE(graceful).

    Returns
    -------
    BotRow | None
        인증 통과한 봇, 토큰 무효/revoke/비active/빈 평문 시 None.
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
    """token soft revoke — revoked_at NOW(). 갱신 여부 bool. 부작용: UPDATE + commit.

    의도: 토큰 폐기. WHERE 의 ``revoked_at IS NULL`` 가드로 이미 revoke 된 토큰의 재revoke 를 무시
    (멱등). 이후 authenticate_bot_token 이 해당 토큰을 거부.

    Raises
    ------
    ValueError
        token_id 비양수.
    """
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
    """owner 의 봇 list — status 무관(소유자 자신 영역). 부작용 없음(SELECT only).

    의도: "내 봇 관리" 화면 — 비공개/비active 봇도 소유자에게는 보여야 하므로 list_public_bots 와 달리
    status/is_public 필터 없이 owner_user_id 만으로 전수 조회.

    Raises
    ------
    ValueError
        owner_user_id 비양수.
    """
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
