# SPDX-License-Identifier: GPL-3.0-or-later
"""friends 테이블 repository — 친구 관계 CRUD (cycle 144 신설).

DDL 정합: ``server/db/migrations/0007_friends.sql``.
모든 함수 = pool 인스턴스 dependency injection 패턴 + parameterized SQL.

설계 결정
---------
- FriendRow frozen dataclass — caller 의 tuple unpacking 안전.
- 8 SQL — insert_friend + get_friend + list_by_user + list_by_friend +
  update_status + delete_friend + search_user_by_username +
  set_nickname.
- status ENUM 4종 (pending / accepted / blocked / removed) — DDL ENUM 정합.
- 단방향 row 모델 — A → B 친구 의 row 1건 + B → A 친구 의 row 별개.
  caller (api) 가 양방향 mutual 검증 의 의무. 본 repository = 단순 CRUD.
- 자기 자신 친구 차단 의 검증 = caller (handlers) 영역.

본 module 범위 외
----------------
- 친구 활동 audit (FRIEND_REQUEST/ACCEPT/REMOVE) — server/api/friends_handlers.py 영역.
- 친구 추천 알고리즘 — Phase 5+ 별개.
- 친구 group/folder 분류 — Phase 5+ 별개.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


# ─── 도메인 객체 ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class FriendRow:
    """friends row dataclass — 7 column 정합."""

    id: int
    user_id: int
    friend_user_id: int
    status: str
    nickname: Optional[str]
    requested_at: datetime
    accepted_at: Optional[datetime]


@dataclass(frozen=True, slots=True)
class FriendWithProfile:
    """friends JOIN users — UI 표시 통합 row.

    friends row + peer 의 username + email_verified 합산.
    handle_list_friends 응답 의 base.
    """

    id: int
    user_id: int
    friend_user_id: int
    status: str
    nickname: Optional[str]
    requested_at: datetime
    accepted_at: Optional[datetime]
    friend_username: str
    friend_email_verified: int


# ─── SQL ────────────────────────────────────────────────────────────────────

_INSERT_FRIEND = (
    "INSERT INTO friends (user_id, friend_user_id, status, nickname) "
    "VALUES (%s, %s, %s, %s)"
)

_GET_FRIEND = (
    "SELECT id, user_id, friend_user_id, status, nickname, "
    "       requested_at, accepted_at "
    "FROM friends WHERE user_id = %s AND friend_user_id = %s"
)

_LIST_BY_USER = (
    "SELECT f.id, f.user_id, f.friend_user_id, f.status, f.nickname, "
    "       f.requested_at, f.accepted_at, u.username, u.email_verified "
    "FROM friends f INNER JOIN users u ON u.id = f.friend_user_id "
    "WHERE f.user_id = %s AND f.status IN ('pending', 'accepted', 'blocked') "
    "ORDER BY f.status ASC, f.requested_at DESC"
)

_LIST_BY_FRIEND = (
    "SELECT f.id, f.user_id, f.friend_user_id, f.status, f.nickname, "
    "       f.requested_at, f.accepted_at, u.username, u.email_verified "
    "FROM friends f INNER JOIN users u ON u.id = f.user_id "
    "WHERE f.friend_user_id = %s AND f.status = 'pending' "
    "ORDER BY f.requested_at DESC"
)

_UPDATE_STATUS_ACCEPT = (
    "UPDATE friends SET status = 'accepted', "
    "       accepted_at = CURRENT_TIMESTAMP "
    "WHERE user_id = %s AND friend_user_id = %s AND status = 'pending'"
)

_UPDATE_STATUS = (
    "UPDATE friends SET status = %s "
    "WHERE user_id = %s AND friend_user_id = %s"
)

_DELETE_FRIEND = (
    "DELETE FROM friends "
    "WHERE user_id = %s AND friend_user_id = %s"
)

_SEARCH_USER_BY_USERNAME = (
    "SELECT id, username, email_verified FROM users "
    "WHERE username LIKE %s AND status = 'active' "
    "ORDER BY username ASC LIMIT %s"
)

_UPDATE_NICKNAME = (
    "UPDATE friends SET nickname = %s "
    "WHERE user_id = %s AND friend_user_id = %s"
)


# ─── repository 함수 ────────────────────────────────────────────────────────


async def insert_friend(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
    status: str = "pending",
    nickname: Optional[str] = None,
) -> int:
    """친구 관계 row 신규 생성. status default = pending.

    Parameters
    ----------
    user_id : int
        관계 owner 사용자 PK.
    friend_user_id : int
        관계 peer 사용자 PK. user_id != friend_user_id (caller 검증 의무).
    status : str
        초기 상태 — pending / accepted / blocked. default pending.
    nickname : str | None
        owner 의 friend 별명 (Optional).

    Returns
    -------
    int
        신규 friends.id (AUTO_INCREMENT 결과).
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_FRIEND,
                (user_id, friend_user_id, status, nickname),
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_friend(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
) -> Optional[FriendRow]:
    """단일 친구 관계 lookup. (user_id, friend_user_id) UNIQUE.

    Returns
    -------
    FriendRow | None
        row 부재 시 None.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_FRIEND, (user_id, friend_user_id))
            row = await cur.fetchone()
    if row is None:
        return None
    return FriendRow(*row)


async def list_by_user(
    pool: Any,
    user_id: int,
) -> List[FriendWithProfile]:
    """user_id 의 친구 list — pending/accepted/blocked + peer 의 username JOIN.

    removed status = caller 의 history 조회 시 별개 함수 의 의무 (본 list 부재).
    pending 발신자 + accepted 양방향 + blocked 차단자 의 통합.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_BY_USER, (user_id,))
            rows = await cur.fetchall()
    return [FriendWithProfile(*row) for row in rows]


async def list_pending_requests(
    pool: Any,
    user_id: int,
) -> List[FriendWithProfile]:
    """user_id 가 수신자 인 pending 요청 list — friend_user_id = user_id 의 row."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_BY_FRIEND, (user_id,))
            rows = await cur.fetchall()
    return [FriendWithProfile(*row) for row in rows]


async def accept_friend(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
) -> int:
    """pending → accepted 전환 + accepted_at = NOW(). rowcount 반환 (0 = 부재).

    user_id = 수락자 (request 의 friend_user_id) + friend_user_id = 발신자.
    수락 시 caller 의 의무 — reverse direction row 의 별개 INSERT (accepted 상태).
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _UPDATE_STATUS_ACCEPT, (user_id, friend_user_id)
            )
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def update_status(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
    new_status: str,
) -> int:
    """status 갱신 — pending/accepted/blocked/removed 의 4 ENUM. rowcount 반환."""

    if new_status not in ("pending", "accepted", "blocked", "removed"):
        raise ValueError(f"invalid status: {new_status}")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _UPDATE_STATUS, (new_status, user_id, friend_user_id)
            )
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def delete_friend(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
) -> int:
    """친구 관계 row 의 hard delete. rowcount 반환 (0 = 부재).

    soft delete (status=removed) 와 별개 — production 의 caller = update_status
    의 removed 패턴 권장 (history 보존). 본 함수 = admin/test 용 hard delete.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DELETE_FRIEND, (user_id, friend_user_id))
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def search_users_by_username(
    pool: Any,
    *,
    keyword: str,
    limit: int = 20,
) -> List[dict]:
    """username 의 부분 매칭 검색 — LIKE %keyword% + status=active + LIMIT.

    Returns
    -------
    List[dict]
        ``{"id": int, "username": str, "email_verified": bool}`` 의 list.
        UI dropdown 의 검색 결과 base.
    """

    # 한글 주석: SQL injection 차단 — LIKE 의 % 는 query 안 wrap, keyword 는 parameterized.
    pattern = f"%{keyword}%"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SEARCH_USER_BY_USERNAME, (pattern, int(limit)))
            rows = await cur.fetchall()
    return [
        {
            "id": int(row[0]),
            "username": str(row[1]),
            "email_verified": bool(row[2]),
        }
        for row in rows
    ]


async def set_nickname(
    pool: Any,
    *,
    user_id: int,
    friend_user_id: int,
    nickname: Optional[str],
) -> int:
    """owner 의 friend 별명 갱신. NULL = 별명 제거 (username 폴백). rowcount 반환."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _UPDATE_NICKNAME, (nickname, user_id, friend_user_id)
            )
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)
