# SPDX-License-Identifier: GPL-3.0-or-later
"""rooms + peers 테이블 repository — 룸/그룹 채팅 CRUD (cycle 135 확장).

역할
----
대화 컨테이너(room)와 참여자(peer)의 CRUD 를 캡슐화한다. 1:1 DM·그룹·채널·봇·저장한 메시지 방을
deterministic room_code 로 통합 관리한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = rooms/group 관리 handler + signaling 영속화 bridge.
DDL 정합: ``server/db/migrations/0001_init.sql``. 모든 함수 = pool DI + parameterized SQL.

invariant / 설계 결정
--------------------
- RoomRow + PeerRow frozen dataclass — 호출자의 row tuple unpacking 을 컬럼 순서 변경에 안전하게.
- **deterministic room_code** — DM=``dm-{min}-{max}``, bot=``bot-{user}``, saved=``saved-{user}`` —
  같은 입력은 항상 같은 코드라 find_or_create 가 중복 방 생성 없이 멱등하다.
- peers 는 soft-leave(left_at) — 활성 참여 = ``left_at IS NULL``(list/count/role/get 전부 이 filter).
- 15 공개 함수(실 심볼명 기준) — insert_room + get_room_by_id + get_room_by_code +
  find_or_create_dm_room + find_or_create_bot_room + find_or_create_saved_room +
  list_rooms_by_owner + list_rooms_by_member + close_room + insert_peer + update_peer_left +
  update_peer_role + count_active_peers + get_peer + list_active_peers.

부작용
------
insert/update/close 류는 write(commit). get/list/count + find_or_create(미존재 시 insert) 외 read 는 부작용 없음.

본 module 범위 외
----------------
- 그룹 채팅 메시지 fan-out — ``server/api/messages_handlers.py`` 영역.
- WebRTC SDP / ICE binding — ``server/signaling.py`` 영역.
- 실 mesh 토폴로지 manager — Phase 5+ 별개.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


# ─── 도메인 객체 ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RoomRow:
    """rooms 단일 row 의 read-only 투영 — 7 column 정합.

    불변식: frozen + 필드 순서 = rooms SELECT 컬럼 1:1. ``kind`` = direct/group/channel,
    ``status`` active/closed, ``closed_at`` None = 운영 중.
    """

    id: int
    room_code: str
    owner_id: int
    kind: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime]


@dataclass(frozen=True, slots=True)
class PeerRow:
    """peers 단일 row 의 read-only 투영 — 6 column 정합.

    불변식: frozen + 필드 순서 = peers SELECT 컬럼 1:1. ``left_at`` None = 현재 참여 중(soft-leave).
    """

    id: int
    room_id: int
    user_id: int
    role: str
    joined_at: datetime
    left_at: Optional[datetime]


# ─── rooms 의 SQL ───────────────────────────────────────────────────────────

_INSERT_ROOM = (
    "INSERT INTO rooms (room_code, owner_id, kind, name, description, avatar_ref, status) "
    "VALUES (%s, %s, %s, %s, %s, %s, 'active')"
)

_GET_ROOM_BY_ID = (
    "SELECT id, room_code, owner_id, kind, status, created_at, closed_at "
    "FROM rooms WHERE id = %s"
)

_GET_ROOM_BY_CODE = (
    "SELECT id, room_code, owner_id, kind, status, created_at, closed_at "
    "FROM rooms WHERE room_code = %s"
)

_LIST_ROOMS_BY_OWNER = (
    "SELECT id, room_code, owner_id, kind, status, created_at, closed_at "
    "FROM rooms WHERE owner_id = %s AND status = 'active' "
    "ORDER BY created_at DESC"
)

_LIST_ROOMS_BY_MEMBER = (
    "SELECT r.id, r.room_code, r.owner_id, r.kind, r.status, r.created_at, "
    "r.closed_at FROM rooms r "
    "INNER JOIN peers p ON p.room_id = r.id "
    "WHERE p.user_id = %s AND p.left_at IS NULL AND r.status = 'active' "
    "ORDER BY r.created_at DESC"
)

_CLOSE_ROOM = (
    "UPDATE rooms SET status = 'closed', closed_at = CURRENT_TIMESTAMP "
    "WHERE id = %s AND status = 'active'"
)


# ─── peers 의 SQL ───────────────────────────────────────────────────────────

_INSERT_PEER = (
    "INSERT INTO peers (room_id, user_id, role) VALUES (%s, %s, %s)"
)

_UPDATE_PEER_LEFT = (
    "UPDATE peers SET left_at = CURRENT_TIMESTAMP "
    "WHERE room_id = %s AND user_id = %s AND left_at IS NULL"
)

_UPDATE_PEER_ROLE = (
    "UPDATE peers SET role = %s "
    "WHERE room_id = %s AND user_id = %s AND left_at IS NULL"
)

_COUNT_ACTIVE_PEERS = (
    "SELECT COUNT(*) FROM peers WHERE room_id = %s AND left_at IS NULL"
)

_GET_PEER = (
    "SELECT id, room_id, user_id, role, joined_at, left_at FROM peers "
    "WHERE room_id = %s AND user_id = %s AND left_at IS NULL"
)

_LIST_ACTIVE_PEERS = (
    "SELECT id, room_id, user_id, role, joined_at, left_at "
    "FROM peers WHERE room_id = %s AND left_at IS NULL "
    "ORDER BY joined_at ASC"
)


# ─── rooms repository 함수 ──────────────────────────────────────────────────


async def insert_room(
    pool: Any,
    *,
    room_code: str,
    owner_id: int,
    kind: str = "direct",
    name: str = "",
    description: str = "",
    avatar_ref: str = "",
) -> int:
    """룸 신규 생성. kind = direct (1:1) / group (다자).

    cycle 169.852 — group/channel 생성 시 name/description/avatar_ref 동시 영속
    (0017 컬럼). direct kind = 빈값 의미. avatar_ref = `avatars/<sha256>.<ext>`
    (caller 가 실재 검증 후 전달, 빈값=이니셜 fallback).
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_ROOM,
                (room_code, owner_id, kind, name, description, avatar_ref),
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_room_by_id(pool: Any, room_id: int) -> Optional[RoomRow]:
    """room_id PK lookup. 부재 = None."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_ROOM_BY_ID, (room_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return RoomRow(*row)


async def get_room_by_code(pool: Any, room_code: str) -> Optional[RoomRow]:
    """room_code UNIQUE lookup. 부재 = None."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_ROOM_BY_CODE, (room_code,))
            row = await cur.fetchone()
    if row is None:
        return None
    return RoomRow(*row)


async def find_or_create_dm_room(pool: Any, user_a: int, user_b: int) -> int:
    """1:1 DM room lookup-or-create — 멱등 (cycle 169.222). room_id 반환.

    의도: 두 사용자의 DM 방을 한 번에 보장. (user_a, user_b) 정렬 후 ``dm-{min}-{max}`` 코드를
    deterministic 생성 → 이미 있으면 그 id, 없으면 신설(owner=작은 user_id). 같은 쌍은 항상 한 방.
    부작용: 미존재 시 rooms INSERT(존재 시 read-only).

    Raises
    ------
    ValueError
        user_a == user_b (자기 자신과의 DM 불가).
    """
    if user_a == user_b:
        raise ValueError("DM room user_a == user_b 불가")
    small, large = sorted((user_a, user_b))
    room_code = f"dm-{small}-{large}"
    existing = await get_room_by_code(pool, room_code)
    if existing:
        return existing.id
    # 신설 — owner = 작은 user_id (deterministic)
    return await insert_room(pool, room_code=room_code, owner_id=small, kind="direct")


async def find_or_create_bot_room(pool: Any, user_id: int) -> int:
    """cycle 169.441 — bot chat room 의 lookup or insert chain.

    사용자 directive 모든 채팅방 history persist — 고객센터 봇 대화도 server retain 의무.
    room_code = `bot-{user_id}` deterministic. kind="direct" retain (1:1 user↔bot).
    """
    if user_id <= 0:
        raise ValueError("bot room user_id 양수 의무")
    room_code = f"bot-{user_id}"
    existing = await get_room_by_code(pool, room_code)
    if existing:
        return existing.id
    return await insert_room(pool, room_code=room_code, owner_id=user_id, kind="direct")


async def find_or_create_saved_room(pool: Any, user_id: int) -> int:
    """cycle 169.411 — 저장한 메시지 room 의 lookup or insert chain.

    self DM room (single owner = user_id). room_code = `saved-{user_id}` deterministic.
    kind="direct" retain 但 단일 peer 의 (sender == receiver == user_id) saved messages.
    """
    if user_id <= 0:
        raise ValueError("saved room user_id 양수 의무")
    room_code = f"saved-{user_id}"
    existing = await get_room_by_code(pool, room_code)
    if existing:
        return existing.id
    return await insert_room(pool, room_code=room_code, owner_id=user_id, kind="direct")


async def list_rooms_by_owner(pool: Any, owner_id: int) -> List[RoomRow]:
    """owner_id 의 활성 룸 list (status=active, 최신순)."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_ROOMS_BY_OWNER, (owner_id,))
            rows = await cur.fetchall()
    return [RoomRow(*row) for row in rows]


async def list_rooms_by_member(pool: Any, user_id: int) -> List[RoomRow]:
    """user_id 의 활성 참여 룸 list (peers JOIN + left_at IS NULL, 최신순)."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_ROOMS_BY_MEMBER, (user_id,))
            rows = await cur.fetchall()
    return [RoomRow(*row) for row in rows]


async def close_room(pool: Any, room_id: int) -> None:
    """룸 종료 — status=closed + closed_at=NOW()."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_CLOSE_ROOM, (room_id,))
        await conn.commit()


# ─── peers repository 함수 ──────────────────────────────────────────────────


async def insert_peer(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
    role: str = "member",
) -> int:
    """peers row 신규 생성. role = owner / member."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_INSERT_PEER, (room_id, user_id, role))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def update_peer_left(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
) -> int:
    """peers leave — left_at=NOW() 갱신. rowcount 반환 (0 = 활성 부재)."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_UPDATE_PEER_LEFT, (room_id, user_id))
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def update_peer_role(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
    role: str,
) -> int:
    """peers role 갱신 — owner 권한 위임 등. rowcount 반환."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_UPDATE_PEER_ROLE, (role, room_id, user_id))
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def count_active_peers(pool: Any, room_id: int) -> int:
    """룸의 활성 참여자 수 — left_at IS NULL COUNT. 부작용 없음(SELECT only).

    의도: 그룹 인원 표시·빈 방 정리 판정. 퇴장자(left_at 존재)는 제외.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_COUNT_ACTIVE_PEERS, (room_id,))
            row = await cur.fetchone()
    if row is None:
        return 0
    return int(row[0])


async def get_peer(
    pool: Any,
    *,
    room_id: int,
    user_id: int,
) -> Optional[PeerRow]:
    """활성 peer 단건 lookup — left_at IS NULL. 부재 시 None. 부작용 없음(SELECT only).

    의도: 추방/퇴장/권한 변경 직전 대상의 현 role 확인(권한 검사의 근거). 퇴장한 peer 는 None.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_PEER, (room_id, user_id))
            row = await cur.fetchone()
    if row is None:
        return None
    return PeerRow(*row)


async def list_active_peers(pool: Any, room_id: int) -> List[PeerRow]:
    """룸의 활성 참여자 list — left_at IS NULL, 입장 순(joined_at ASC). 부작용 없음(SELECT only).

    의도: 멤버 목록 화면·broadcast 대상 산출. peers.py 의 동명 함수와 등가(rooms 통합 진입점).
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_ACTIVE_PEERS, (room_id,))
            rows = await cur.fetchall()
    return [PeerRow(*row) for row in rows]
