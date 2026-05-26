# SPDX-License-Identifier: GPL-3.0-or-later
"""peers 테이블 repository — 룸 참여자 join/leave 영속화.

역할
----
room 과 user 의 n:n 참여 관계(peers)를 영속한다. 참여자 등록·퇴장 표시·활성 목록 조회.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = signaling 영속화 bridge / rooms·group 관리 handler.
하위(asyncmy pool)에만 의존하고 상위(handler)를 모른다.

의존성
------
asyncmy connection ``pool`` dependency injection(모든 함수 첫 인자). DDL 정합: peers 테이블.

invariant / 설계 결정
--------------------
- **soft-leave 모델** — 퇴장은 row 삭제가 아니라 ``left_at`` 타임스탬프 기록. 참여 history 보존
  (재입장·audit·통계). 활성 참여자 = ``left_at IS NULL`` 인 row 만.
- role = owner / member (그룹 권한 분기). 모든 SQL parameterized(injection 차단).
- 3 공개 함수 — insert_peer + mark_peer_left + list_active_peers.

부작용
------
write(insert_peer/mark_peer_left)는 ``conn.commit()`` 즉시 영속. read(list_active_peers)는 부작용 없음.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


@dataclass(frozen=True, slots=True)
class PeerRow:
    """peers 단일 row 의 read-only 투영 — 6 column 정합.

    책임: SELECT 결과를 이름 있는 필드로 감싼다. 불변식: frozen(생성 후 불변) +
    필드 순서 = ``list_active_peers`` SELECT 컬럼 순서와 1:1(``PeerRow(*row)`` 정합).
    ``left_at`` None = 현재 참여 중, 값 존재 = 퇴장 시각(soft-leave).
    """

    id: int
    room_id: int
    user_id: int
    role: str
    joined_at: datetime
    left_at: Optional[datetime]


async def insert_peer(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
    role: str = "member",
) -> int:
    """참여자 등록 — room 에 user 를 role 로 join. 신규 peers.id 반환.

    의도: 룸 입장/그룹 멤버 추가 시 호출. 부작용: peers INSERT + commit 즉시 영속.

    Parameters
    ----------
    room_id : int
        대상 room PK.
    user_id : int
        참여 user PK.
    role : str
        owner / member. default member(권한 분기 — owner 만 멤버 추방 등).

    Returns
    -------
    int
        신규 peers.id (AUTO_INCREMENT).
    """

    sql = (
        "INSERT INTO peers (room_id, user_id, role) "
        "VALUES (%s, %s, %s)"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, user_id, role))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def mark_peer_left(pool: Any, room_id: int, user_id: int) -> None:
    """참여자 퇴장 표시 — left_at = CURRENT_TIMESTAMP (soft-leave, history 보존).

    의도: 룸 퇴장/멤버 제거. row 를 삭제하지 않고 left_at 만 기록해 참여 이력을 남긴다.
    WHERE 에 ``left_at IS NULL`` 을 둬 이미 퇴장한 row 의 재갱신(퇴장 시각 덮어쓰기)을 방지한다.
    부작용: peers UPDATE + commit 즉시 영속(대상 부재 시 0 row 갱신, 무반환).
    """

    sql = (
        "UPDATE peers SET left_at = CURRENT_TIMESTAMP "
        "WHERE room_id = %s AND user_id = %s AND left_at IS NULL"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id, user_id))
        await conn.commit()


async def list_active_peers(pool: Any, room_id: int) -> List[PeerRow]:
    """룸의 현재 활성 참여자 list — left_at IS NULL 인 row 만.

    의도: 멤버 목록 화면·broadcast 대상 산출. 퇴장자(left_at 존재)는 제외하고 입장 순(joined_at ASC)
    정렬. 부작용 없음(SELECT only).

    Returns
    -------
    List[PeerRow]
        활성 참여자(부재 시 빈 list).
    """

    sql = (
        "SELECT id, room_id, user_id, role, joined_at, left_at "
        "FROM peers WHERE room_id = %s AND left_at IS NULL "
        "ORDER BY joined_at ASC"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (room_id,))
            rows = await cur.fetchall()
    return [PeerRow(*row) for row in rows]
