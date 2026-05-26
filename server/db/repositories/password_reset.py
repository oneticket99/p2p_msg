# SPDX-License-Identifier: GPL-3.0-or-later
"""password_reset 테이블 repository — 비번 재설정 토큰 발급 + 검증 + 소진.

역할
----
비밀번호 재설정 1회용 토큰의 생명주기(발급 → 활성 검증 → 소진)를 영속한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = ``server/auth/`` reset use case(재설정 요청·실행).

보안 invariant
--------------
- **토큰 평문 비저장** — DB 에는 ``token_hash`` 만 저장(평문 토큰은 메일로만 전달, 호출자가 해시).
  DB 유출 시에도 원 토큰 복원 불가.
- **만료 + 1회 소진** — 활성 토큰 = ``consumed_at IS NULL`` AND ``expires_at > NOW()``. 재사용/만료 차단.
- TTL default 1800초(30분) — 발급 시 expires_at = NOW() + ttl.
- 3 공개 함수 — insert_reset_token + find_active_token + consume_token.

부작용
------
insert/consume 는 write(commit). find_active_token 은 부작용 없음(SELECT only).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class ResetTokenRow:
    """password_reset 단일 row 의 read-only 투영 — 6 column 정합.

    책임: ``find_active_token`` SELECT 결과 래핑. 불변식: frozen + 필드 순서 = SELECT 컬럼 1:1.
    ``consumed_at`` None = 미사용(소진 가능), 값 존재 = 이미 소진됨.
    """

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
    """비번 재설정 토큰 발급 — expires_at = NOW() + ttl(default 30분). 신규 id 반환.

    의도: 재설정 요청 시 1회용 토큰 row 생성. expires_at 은 DB 의 DATE_ADD 로 계산(서버 시계 기준,
    클라/앱 시계 불일치 영향 배제). token_hash 만 저장(평문 비저장). 부작용: INSERT + commit.

    Parameters
    ----------
    token_hash : str
        평문 토큰의 해시(호출자가 해시 후 전달 — 평문은 메일로만).
    ttl_seconds : int
        유효 기간(초). default 1800(30분).

    Returns
    -------
    int
        신규 password_reset.id.
    """

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
    """미사용 + 미만료 토큰 lookup. 부재(소진/만료/없음) 시 None.

    의도: 재설정 실행 전 토큰 유효성 검증. WHERE 에 ``consumed_at IS NULL`` +
    ``expires_at > NOW()`` 를 둬 소진·만료 토큰을 SQL 단계에서 배제(애플리케이션 분기 불요).
    부작용 없음(SELECT only).

    Returns
    -------
    ResetTokenRow | None
        유효 토큰 row, 부재 시 None(호출자는 재설정 거부).
    """

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
    """토큰 소진 표시 — consumed_at = NOW() (재사용 차단).

    의도: 재설정 성공 직후 호출 — 이후 같은 토큰의 ``find_active_token`` 이 None 을 반환하게 해
    1회용을 강제한다. 부작용: UPDATE + commit 즉시 영속.
    """

    sql = "UPDATE password_reset SET consumed_at = CURRENT_TIMESTAMP WHERE id = %s"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (token_id,))
        await conn.commit()
