# SPDX-License-Identifier: GPL-3.0-or-later
"""read_states repository — 읽음 상태 추적 (cycle 169.447 신설).

역할
----
(user, room) 별 마지막 읽은 메시지 id(last_read_msg_id)를 영속해 unread 배지를 산출한다.

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = messages/chat 관련 REST handler(읽음 동기화·배지 fan-out).

invariant / 설계 결정
--------------------
- **단조 증가 보장** — upsert 는 ``GREATEST`` 로 기존값보다 작은 last_read 갱신을 무시(역행 차단).
  네트워크 재정렬로 과거 msg_id 가 늦게 도착해도 읽음 위치가 뒤로 가지 않는다.
- (user_id, room_id) UNIQUE KEY 전제 — ON DUPLICATE KEY UPDATE upsert 의 근거.
- unread count = ``msg.id > last_read`` AND ``sender != user``(내가 보낸 메시지는 제외).
- 4 공개 함수 — upsert_last_read + get_last_read + get_last_read_batch + get_unread_counts.

부작용
------
upsert_last_read 만 write(commit). 나머지 3 read 함수는 부작용 없음(SELECT only).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


async def upsert_last_read(
    pool: Any, *, user_id: int, room_id: int, last_read_msg_id: int,
) -> None:
    """(user, room) 의 last_read_msg_id UPSERT — GREATEST 로 역행 차단.

    의도: 메시지 읽음 시 읽음 위치 동기화. 기존값보다 작은 msg_id 가 들어와도 GREATEST 로
    무시해 읽음 위치 단조 증가를 보장한다(재정렬 도착 안전). 부작용: upsert + commit.

    Raises
    ------
    ValueError
        user_id/room_id 가 0 이하(양수 의무) 또는 last_read_msg_id 음수.
    """
    if user_id <= 0 or room_id <= 0:
        raise ValueError("user_id/room_id 양수 의무")
    if last_read_msg_id < 0:
        raise ValueError("last_read_msg_id 음수 차단")
    sql = (
        "INSERT INTO read_states (user_id, room_id, last_read_msg_id) "
        "VALUES (%s, %s, %s) "
        "ON DUPLICATE KEY UPDATE "
        "  last_read_msg_id = GREATEST(last_read_msg_id, VALUES(last_read_msg_id))"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, room_id, last_read_msg_id))
        await conn.commit()


async def get_last_read(
    pool: Any, *, user_id: int, room_id: int,
) -> int:
    """(user, room) 의 last_read_msg_id 반환. row 부재 시 0(아무것도 안 읽음).

    의도: 단일 방 진입 시 읽음 위치 복원. 부작용 없음(SELECT only).
    """
    sql = (
        "SELECT last_read_msg_id FROM read_states "
        "WHERE user_id = %s AND room_id = %s LIMIT 1"
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, (user_id, room_id))
            row = await cur.fetchone()
    return int(row[0]) if row else 0


async def get_last_read_batch(
    pool: Any, *, user_id: int, room_ids: List[int],
) -> Dict[int, int]:
    """여러 room 의 last_read_msg_id batch 조회 (cycle 169.470 — bubble set_read chain base).

    의도: chat_list 표시 시 방마다 개별 query(N+1) 대신 IN 절 1회로 일괄 조회. 빈 room_ids 면
    DB 미접근 즉시 빈 dict 반환. 조회 안 된 방은 0 으로 채워 반환(키 누락 방지). 부작용 없음.

    Returns
    -------
    Dict[int, int]
        room_id → last_read_msg_id (전 room_ids 키 보장, 미조회분 0).
    """
    if not room_ids:
        return {}
    placeholders = ",".join(["%s"] * len(room_ids))
    sql = (
        f"SELECT room_id, last_read_msg_id FROM read_states "
        f"WHERE user_id = %s AND room_id IN ({placeholders})"
    )
    params = (user_id, *room_ids)
    out: Dict[int, int] = {rid: 0 for rid in room_ids}
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    for r in rows:
        out[int(r[0])] = int(r[1])
    return out


async def get_unread_counts(
    pool: Any, *, user_id: int, room_ids: List[int],
) -> Dict[int, int]:
    """여러 room 의 unread count batch 조회 — chat_list 배지 fan-out.

    의도: 안 읽은 메시지 수를 방별로 한 번에 산출. SQL = messages LEFT JOIN read_states +
    COUNT(``m.id > COALESCE(last_read, 0)`` AND ``m.sender_id != user_id``) — 내가 보낸
    메시지는 unread 에서 제외하고, read_state row 부재 방은 COALESCE 로 전부 unread 처리.
    빈 room_ids 면 즉시 빈 dict. 미조회 방은 0 으로 채워 반환. 부작용 없음(SELECT only).

    Returns
    -------
    Dict[int, int]
        room_id → unread count (전 room_ids 키 보장, 미조회분 0).
    """
    if not room_ids:
        return {}
    placeholders = ",".join(["%s"] * len(room_ids))
    sql = (
        f"SELECT m.room_id, COUNT(*) AS unread "
        f"FROM messages m "
        f"LEFT JOIN read_states rs ON rs.user_id = %s AND rs.room_id = m.room_id "
        f"WHERE m.room_id IN ({placeholders}) "
        f"  AND m.sender_id != %s "
        f"  AND m.id > COALESCE(rs.last_read_msg_id, 0) "
        f"GROUP BY m.room_id"
    )
    params = (user_id, *room_ids, user_id)
    out: Dict[int, int] = {rid: 0 for rid in room_ids}
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
    for r in rows:
        out[int(r[0])] = int(r[1])
    return out
