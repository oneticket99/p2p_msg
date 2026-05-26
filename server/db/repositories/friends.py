# SPDX-License-Identifier: GPL-3.0-or-later
"""friends 테이블 repository — 친구 관계 CRUD (cycle 144 신설).

[본 페이즈 주석 표준 본보기 — cycle 169.853 한글 주석 상세화 §4 D-1~D-6 reference exemplar]

역할
----
friends 테이블의 단순 CRUD를 캡슐화한다. 친구 요청/수락/차단/제거/검색/별명의 SQL을
한 곳에 모아, 상위 계층(API handler)이 raw SQL을 알지 못하게 격리한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = ``server/api/friends_handlers.py``(REST handler).
본 repository 는 더 하위(asyncmy connection pool)에만 의존하고, 상위(handler/UI)를 모른다.

의존성
------
- 의존 대상: asyncmy connection ``pool``(dependency injection — 모든 함수의 첫 인자).
  pool 을 직접 import 하지 않고 주입받아 test 의 mock pool 치환을 가능하게 한다.
- DDL 정합: ``server/db/migrations/0007_friends.sql``.
- 본 module 에 의존: ``friends_handlers``(REST), e2e/unit test.

설계 결정 (invariant)
--------------------
- 모든 SQL 은 parameterized(``%s``) — SQL injection 차단(D-5 위생). 문자열 포매팅 SQL 금지.
- FriendRow frozen dataclass — 호출자의 tuple unpacking 을 컬럼 순서 변경에 안전하게 한다.
- 8 SQL — insert_friend + get_friend + list_by_user + list_by_friend +
  update_status + delete_friend + search_user_by_username + set_nickname.
- status ENUM 4종 (pending / accepted / blocked / removed) — DDL ENUM 정합. 위반 시 ValueError.
- **단방향 row 모델** — "A → B 친구"는 row 1건, "B → A 친구"는 별개 row 다(대칭 보장 부재).
  양방향 mutual 관계 성립 검증은 호출자(handler) 책임이며, 본 repository 는 단방향 CRUD 만 한다.
- 자기 자신 친구 차단(user_id == friend_user_id) 검증 = 호출자(handler) 영역.

부작용 (side effect)
-------------------
- write 함수(insert/accept/update/delete/set_nickname)는 ``conn.commit()`` 으로 즉시 영속한다.
- read 함수(get/list/search)는 부작용이 없다(SELECT only).

본 module 범위 외
----------------
- 친구 활동 audit (FRIEND_REQUEST/ACCEPT/REMOVE) — ``server/api/friends_handlers.py`` 영역.
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
    """friends 단일 row 의 read-only 투영 — 7 column 정합.

    책임: SELECT 결과 tuple 을 이름 있는 필드로 감싸 호출자의 인덱스 접근(row[3] 등)을 차단한다.
    불변식: ``frozen=True`` 로 생성 후 변경 불가(repository 가 돌려준 스냅샷의 무결성 보장).
    필드 순서 = ``_GET_FRIEND`` SELECT 컬럼 순서와 1:1(``FriendRow(*row)`` 언패킹 정합).
    """

    id: int
    user_id: int
    friend_user_id: int
    status: str
    nickname: Optional[str]
    requested_at: datetime
    accepted_at: Optional[datetime]


@dataclass(frozen=True, slots=True)
class FriendWithProfile:
    """friends JOIN users — UI 표시용 통합 row(친구 행 + peer 프로필).

    책임: ``list_by_user``/``list_pending_requests`` 의 JOIN 결과를 담는다 — friends 7 column
    + peer 의 ``friend_username``·``friend_email_verified`` 를 합산해 UI 가 추가 조회 없이
    친구 목록 한 행을 그릴 수 있게 한다(N+1 query 회피).
    협력: ``friends_handlers.handle_list_friends`` 응답의 base. ``FriendRow`` 와 달리 프로필 2 필드 추가.
    불변식: 필드 순서 = ``_LIST_BY_USER``/``_LIST_BY_FRIEND`` SELECT 컬럼 순서와 1:1.
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
    "SELECT id, username, display_name, nickname, email_verified FROM users "
    "WHERE (username LIKE %s OR display_name LIKE %s OR nickname LIKE %s) "
    "AND status = 'active' "
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

    의도: 친구 요청 발신 시 호출 — 단방향 row 1건 삽입(역방향은 수락 시 호출자가 별도 삽입).

    Parameters
    ----------
    user_id : int
        관계 owner 사용자 PK(친구 요청 발신자).
    friend_user_id : int
        관계 peer 사용자 PK(요청 수신자). user_id != friend_user_id 는 호출자 검증 의무.
    status : str
        초기 상태 — pending / accepted / blocked. default pending.
    nickname : str | None
        owner 가 붙인 friend 별명 (Optional, NULL = username 폴백).

    Returns
    -------
    int
        신규 friends.id (AUTO_INCREMENT 결과).

    Raises
    ------
    Exception
        (user_id, friend_user_id) UNIQUE 제약 위반(중복 요청) 시 driver 가 IntegrityError 전파.

    부작용
    ------
    friends 테이블 INSERT + ``conn.commit()`` 즉시 영속.
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
    """단일 친구 관계 lookup. (user_id, friend_user_id) UNIQUE 라 0/1 건.

    의도: 요청 중복/현 상태 확인 등 분기 전 단건 조회. 부작용 없음(SELECT only).

    Returns
    -------
    FriendRow | None
        해당 단방향 관계 row, 부재 시 None.
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
    """user_id 의 친구 list — pending/accepted/blocked + peer username JOIN.

    의도: 친구 목록 화면 한 번에 그리기 — friends + users JOIN 으로 프로필까지 합산(N+1 회피).
    ``removed`` status 는 본 list 에서 제외(SQL ``status IN`` 3종) — 제거 history 조회는 별도 함수 영역.
    포함 = pending(발신 대기) + accepted(성립) + blocked(차단). 부작용 없음(SELECT only).

    Returns
    -------
    List[FriendWithProfile]
        status ASC → requested_at DESC 정렬. 부재 시 빈 list.
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
    """user_id 가 수신자인 pending 요청 list — friend_user_id = user_id 인 row.

    의도: "받은 친구 요청" 화면 — 내가 수락/거절할 대기 요청만. ``list_by_user`` 와 방향 반대
    (발신자 기준이 아니라 수신자 기준). 부작용 없음(SELECT only).

    Returns
    -------
    List[FriendWithProfile]
        requested_at DESC(최신 요청 우선). 부재 시 빈 list.
    """

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
    """pending → accepted 전환 + accepted_at = NOW(). rowcount 반환(0 = 대상 부재).

    의도: 받은 요청 수락. SQL WHERE 에 ``status = 'pending'`` 을 포함해 이미 처리된 요청의
    재수락(중복 전환)을 방지한다 — 그 경우 rowcount 0 으로 호출자가 "대상 없음"을 안다.
    방향: user_id = 수락자(원 요청의 friend_user_id), friend_user_id = 원 발신자.
    수락 후 호출자 의무 — 역방향(accepted) row 의 별도 INSERT(단방향 모델이라 자동 생성 부재).

    Returns
    -------
    int
        전환된 row 수(0 = pending 대상 부재 — 이미 수락/존재 안 함).

    부작용
    ------
    friends UPDATE + ``conn.commit()`` 즉시 영속.
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
    """status 갱신 — pending/accepted/blocked/removed 4 ENUM. rowcount 반환.

    의도: 차단(blocked)/제거(removed, soft delete) 등 임의 상태 전환의 범용 진입점.
    DDL ENUM 외 값은 DB 에 닿기 전 ValueError 로 조기 차단(잘못된 상태 영속 방지).

    Returns
    -------
    int
        갱신된 row 수(0 = 대상 부재).

    Raises
    ------
    ValueError
        new_status 가 4 ENUM(pending/accepted/blocked/removed) 외인 경우.

    부작용
    ------
    friends UPDATE + ``conn.commit()`` 즉시 영속(ValueError 시 DB 미접근).
    """

    if new_status not in ("pending", "accepted", "blocked", "removed"):
        # 한글 주석 — DDL ENUM 외 값 조기 차단(DB round-trip 전 fail-fast, 잘못된 상태 영속 방지)
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
    """친구 관계 row 의 hard delete. rowcount 반환(0 = 대상 부재).

    의도: row 물리 삭제. **production 권장은 soft delete**(``update_status`` 의 removed)다 —
    history 보존 + audit 추적을 위해. 본 함수의 hard delete 는 admin/test 정리용으로 한정한다.

    Returns
    -------
    int
        삭제된 row 수(0 = 대상 부재).

    부작용
    ------
    friends DELETE(복구 불가) + ``conn.commit()`` 즉시 영속.
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
    """username + display_name + nickname 부분 매칭 검색 (cycle 169.491 한글 확장).

    의도: 친구 추가 화면의 사용자 검색. 회귀 회수 근거 — 이전 cycle 은 username LIKE 만이라
    한글 nickname/display_name 으로는 검색되지 않던 결함을 cycle 169.491 에서 OR 3 column LIKE 로 확장.
    ``status = 'active'`` 만 노출(탈퇴/정지 계정 제외). 부작용 없음(SELECT only).

    Parameters
    ----------
    keyword : str
        검색어. 내부에서 ``%keyword%`` LIKE 패턴으로 wrap(부분 매칭).
    limit : int
        최대 결과 수(unbounded SELECT 차단). default 20.

    Returns
    -------
    List[dict]
        ``{"id": int, "username": str, "display_name": str, "nickname": str,
        "email_verified": bool}`` 의 list. UI 검색 결과 base.
    """

    # 한글 주석 — SQL injection 차단: keyword 는 parameterized(%s) 로 바인딩하고, LIKE 의
    # 와일드카드 % 만 코드에서 안전하게 wrap 한다(keyword 자체를 query 문자열에 넣지 않음).
    pattern = f"%{keyword}%"
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _SEARCH_USER_BY_USERNAME,
                (pattern, pattern, pattern, int(limit)),
            )
            rows = await cur.fetchall()
    return [
        {
            "id": int(row[0]),
            "username": str(row[1]),
            "display_name": str(row[2] or ""),
            "nickname": str(row[3] or ""),
            "email_verified": bool(row[4]),
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
    """owner 의 friend 별명 갱신. NULL = 별명 제거(username 폴백). rowcount 반환.

    의도: 친구 표시명 커스터마이즈. nickname=None 전달 시 컬럼을 NULL 로 — UI 는 별명 부재 시
    username 으로 폴백 표시한다(별명 "삭제"의 의미). 부작용: friends UPDATE + commit 즉시 영속.

    Returns
    -------
    int
        갱신된 row 수(0 = 대상 부재).
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _UPDATE_NICKNAME, (nickname, user_id, friend_user_id)
            )
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)
