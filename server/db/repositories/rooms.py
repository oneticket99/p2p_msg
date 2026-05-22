# SPDX-License-Identifier: GPL-3.0-or-later
"""rooms + peers 테이블 repository — 그룹 채팅 CRUD (cycle 135 확장).

DDL 정합: ``server/db/migrations/0001_init.sql``.
모든 함수 = pool dependency injection 패턴 + asyncmy execute + parameterized SQL.

설계 결정
---------
- RoomRow + PeerRow frozen dataclass — caller 가 row tuple unpacking 안전.
- 10 SQL — insert_room + get_by_id + get_by_code + list_by_owner +
  list_by_member + insert_peer + update_peer_left + count_active_peers +
  get_peer + update_peer_role.
- list_by_member = peers join + left_at IS NULL filter (활성 참여 만).
- update_peer_role = owner 의 권한 위임 등 prerequisite.
- get_peer = role check (kick / leave) 직전 의 lookup helper.
- close_room (기존) + mark_peer_left (peers.py 의 기존) 의 정합 유지.

본 module 범위 외
----------------
- 그룹 채팅 메시지 fan-out — server/api/messages_handlers.py 영역.
- WebRTC SDP / ICE binding — server/signaling.py 영역.
- 실 mesh 토폴로지 manager — Phase 5+ 별개.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


# ─── 도메인 객체 ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class RoomRow:
    """rooms row dataclass — 7 column 정합."""

    id: int
    room_code: str
    owner_id: int
    kind: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime]


@dataclass(frozen=True, slots=True)
class PeerRow:
    """peers row dataclass — 6 column 정합."""

    id: int
    room_id: int
    user_id: int
    role: str
    joined_at: datetime
    left_at: Optional[datetime]


# ─── rooms 의 SQL ───────────────────────────────────────────────────────────

_INSERT_ROOM = (
    "INSERT INTO rooms (room_code, owner_id, kind, status) "
    "VALUES (%s, %s, %s, 'active')"
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
) -> int:
    """룸 신규 생성. kind = direct (1:1) / group (다자)."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_INSERT_ROOM, (room_code, owner_id, kind))
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
    """cycle 169.222 — 1:1 DM room 의 의 lookup or insert chain.

    user_a + user_b sorted tuple → room_code `dm-{min}-{max}` deterministic 생성.
    rooms 안 kind="direct" + room_code unique 기준 retrieve 또는 신설.
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
    """룸 의 활성 참여자 수 (left_at IS NULL)."""

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
    """활성 peer lookup (left_at IS NULL). role check 직전 helper."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_PEER, (room_id, user_id))
            row = await cur.fetchone()
    if row is None:
        return None
    return PeerRow(*row)


async def list_active_peers(pool: Any, room_id: int) -> List[PeerRow]:
    """룸 의 활성 참여자 list (joined_at ASC)."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_ACTIVE_PEERS, (room_id,))
            rows = await cur.fetchall()
    return [PeerRow(*row) for row in rows]
