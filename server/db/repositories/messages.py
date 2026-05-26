# SPDX-License-Identifier: GPL-3.0-or-later
"""messages 테이블 repository — 텍스트/파일/시스템 메시지 history.

cycle 141 확장 — REST endpoint 의 message persistence + MESSAGE_SEND audit chain
prerequisite. cleartext body INSERT 는 임시 (Phase 5 본격 cycle 의 E2EE sealed
envelope chain 회수 의무 — [[project-phase2-remote-control-differentiator]] 외
별개 directive).

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = messages REST handler + signaling 영속화 bridge.
모든 함수 = pool dependency injection + parameterized SQL(injection 차단).

invariant / 설계 결정
--------------------
- MessageRow frozen dataclass — 호출자 row tuple unpacking 을 컬럼 순서 변경에 안전하게.
- **입력 fail-fast** — pool None / id·room_id·sender_id 비양수 / kind ENUM 위반 / kind별 body·file_id
  조합 위반은 DB 도달 전 ValueError 로 차단(잘못된 row 영속 방지).
- **unbounded SELECT 차단** — list_by_room(limit 1..500)·list_messages_in_range(limit 양수) 상한
  의무 ([[feedback-chat-accumulation-memory-release-mandatory]] 정합 — 메모리 누수 차단).
- **soft delete = body NULL tombstone** — 0001_init schema 에 deleted_at 컬럼 부재라 body 를 NULL 로
  비우는 임시 패턴. Phase 5 E2EE migration(0009+)에서 정식 deleted_at + sealed envelope 로 회수 예정.
- 11 공개 함수(실 심볼명 기준) — insert_message + insert_text_message + insert_file_message +
  insert_system_message + get_by_id + list_by_room + count_by_room + delete_by_id + soft_delete +
  list_recent + list_messages_in_range.

부작용
------
insert/delete/soft_delete 류는 write(commit). get/list/count 류는 부작용 없음(SELECT only).

본 module 범위 외
----------------
- WebRTC DataChannel 실 fan-out — ``server/signaling.py`` + Phase 5 mesh manager.
- E2EE sealed envelope encrypt/decrypt — Phase 5 본격 cycle(현 cleartext body INSERT 는 임시).
- batch INSERT 또는 message buffering — Phase 5+ 성능 최적화.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional


# ─── 도메인 객체 ────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class MessageRow:
    """messages 단일 row 의 read-only 투영 — 7 column 정합.

    불변식: frozen + 필드 순서 = messages SELECT 컬럼 1:1. ``kind`` = text/file/system,
    ``body`` = text/system 본문(file 시 None, soft delete 시 NULL tombstone),
    ``file_id`` = file kind 시 file_meta 참조(아니면 None).
    """

    id: int
    room_id: int
    sender_id: int
    kind: str
    body: Optional[str]
    file_id: Optional[str]
    created_at: datetime


# ─── insert / lookup / list SQL ────────────────────────────────────────────


_INSERT_TEXT = (
    "INSERT INTO messages (room_id, sender_id, kind, body) "
    "VALUES (%s, %s, 'text', %s)"
)

_INSERT_FILE = (
    "INSERT INTO messages (room_id, sender_id, kind, file_id) "
    "VALUES (%s, %s, 'file', %s)"
)

_INSERT_SYSTEM = (
    "INSERT INTO messages (room_id, sender_id, kind, body) "
    "VALUES (%s, %s, 'system', %s)"
)

_INSERT_GENERIC = (
    "INSERT INTO messages (room_id, sender_id, kind, body, file_id) "
    "VALUES (%s, %s, %s, %s, %s)"
)

_GET_BY_ID = (
    "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
    "FROM messages WHERE id = %s"
)

_LIST_BY_ROOM_PAGED = (
    "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
    "FROM messages WHERE room_id = %s "
    "ORDER BY created_at DESC, id DESC LIMIT %s OFFSET %s"
)

_COUNT_BY_ROOM = "SELECT COUNT(*) FROM messages WHERE room_id = %s"

_LIST_RECENT = (
    "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
    "FROM messages WHERE room_id = %s "
    "ORDER BY created_at DESC, id DESC LIMIT %s"
)

_LIST_RANGE = (
    "SELECT id, room_id, sender_id, kind, body, file_id, created_at "
    "FROM messages WHERE room_id = %s "
    "AND created_at >= %s AND created_at < %s "
    "ORDER BY created_at DESC, id DESC LIMIT %s"
)

_DELETE_BY_ID = "DELETE FROM messages WHERE id = %s"

# 한글 주석: schema 의 deleted_at column 부재 → body NULL 의 tombstone 패턴.
_SOFT_DELETE = "UPDATE messages SET body = NULL WHERE id = %s"


# ─── repository 함수 ────────────────────────────────────────────────────────


async def insert_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    kind: str,
    body: Optional[str] = None,
    file_id: Optional[str] = None,
) -> int:
    """generic message INSERT — kind 명시 + body/file_id 의 caller 책임.

    Parameters
    ----------
    pool : asyncmy.Pool
        DB pool. None 시 ValueError.
    room_id : int
        대상 룸 PK. 양수 의무.
    sender_id : int
        송신자 user PK. 양수 의무.
    kind : str
        ENUM('text','file','system') 중 1.
    body : Optional[str]
        kind=text/system 시 본문. kind=file 시 None.
    file_id : Optional[str]
        kind=file 시 file_meta.file_id 참조. kind=text/system 시 None.

    Returns
    -------
    int
        신규 row 의 AUTO_INCREMENT id.

    Raises
    ------
    ValueError
        pool None / room_id <= 0 / sender_id <= 0 / kind 무효 / body+file_id
        조합 무효.
    """

    if pool is None:
        raise ValueError("pool 의무 — caller 의 graceful skip 영역")
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    if sender_id <= 0:
        raise ValueError(f"sender_id 양수 의무 — {sender_id}")
    if kind not in ("text", "file", "system"):
        raise ValueError(f"kind ENUM 무효 — {kind!r}")
    if kind == "text" and not body:
        raise ValueError("kind=text 의 body 의무")
    if kind == "file" and not file_id:
        raise ValueError("kind=file 의 file_id 의무")
    if kind == "system" and not body:
        raise ValueError("kind=system 의 body 의무")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT_GENERIC, (room_id, sender_id, kind, body, file_id)
            )
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def insert_text_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> int:
    """텍스트 메시지 기록. kind=text + body 본문."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_INSERT_TEXT, (room_id, sender_id, body))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def insert_file_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    file_id: str,
) -> int:
    """파일 메시지 기록. kind=file + file_meta 참조."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_INSERT_FILE, (room_id, sender_id, file_id))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def insert_system_message(
    pool: Any,
    *,
    room_id: int,
    sender_id: int,
    body: str,
) -> int:
    """시스템 알림 (join/leave/owner change). sender_id = 작업 주체."""

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_INSERT_SYSTEM, (room_id, sender_id, body))
            new_id = cur.lastrowid
        await conn.commit()
    return int(new_id)


async def get_by_id(pool: Any, message_id: int) -> Optional[MessageRow]:
    """single message detail lookup (PK). 부재 = None."""

    if pool is None:
        raise ValueError("pool 의무")
    if message_id <= 0:
        raise ValueError(f"message_id 양수 의무 — {message_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_GET_BY_ID, (message_id,))
            row = await cur.fetchone()
    if row is None:
        return None
    return MessageRow(*row)


async def list_by_room(
    pool: Any,
    *,
    room_id: int,
    limit: int = 50,
    offset: int = 0,
) -> List[MessageRow]:
    """룸 paginated message list (limit + offset, 최신순).

    Parameters
    ----------
    pool : Any
        asyncmy pool.
    room_id : int
        대상 room.
    limit : int, default 50
        page size. 1 <= limit <= 500 의무.
    offset : int, default 0
        skip count. >= 0 의무.

    Returns
    -------
    list[MessageRow]
        created_at DESC + id DESC 정렬.
    """

    if pool is None:
        raise ValueError("pool 의무")
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")
    if limit <= 0 or limit > 500:
        raise ValueError(f"limit 의 1..500 의무 — {limit}")
    if offset < 0:
        raise ValueError(f"offset 음수 불가 — {offset}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_BY_ROOM_PAGED, (room_id, limit, offset))
            rows = await cur.fetchall()
    return [MessageRow(*row) for row in rows]


async def count_by_room(pool: Any, room_id: int) -> int:
    """룸의 전체 메시지 수 — paginated UI 의 total count. 부작용 없음(SELECT only)."""

    if pool is None:
        raise ValueError("pool 의무")
    if room_id <= 0:
        raise ValueError(f"room_id 양수 의무 — {room_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_COUNT_BY_ROOM, (room_id,))
            row = await cur.fetchone()
    if row is None:
        return 0
    return int(row[0])


async def delete_by_id(pool: Any, message_id: int) -> int:
    """hard DELETE — rowcount 반환 (0 = 부재, 1 = 삭제)."""

    if pool is None:
        raise ValueError("pool 의무")
    if message_id <= 0:
        raise ValueError(f"message_id 양수 의무 — {message_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_DELETE_BY_ID, (message_id,))
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def soft_delete(pool: Any, message_id: int) -> int:
    """body NULL 갱신 — row 보존 + content tombstone.

    schema 의 deleted_at column 부재 → body NULL sentinel 의 임시 패턴.
    Phase 5 E2EE cycle 의 schema migration (0009+) 의 의무 — sealed envelope
    chain + deleted_at 정식 column 추가 시 회수.

    Returns
    -------
    int
        rowcount (0 = 부재, 1 = tombstone 갱신).
    """

    if pool is None:
        raise ValueError("pool 의무")
    if message_id <= 0:
        raise ValueError(f"message_id 양수 의무 — {message_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SOFT_DELETE, (message_id,))
            rowcount = cur.rowcount or 0
        await conn.commit()
    return int(rowcount)


async def list_recent(
    pool: Any,
    *,
    room_id: int,
    limit: int = 100,
) -> List[MessageRow]:
    """룸의 최근 N건(default 100) timeline — created_at DESC. 부작용 없음(SELECT only).

    의도: 방 진입 시 최신 메시지 우선 로드. 과거 페이지는 list_messages_in_range 로 lazy fetch.
    """

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_RECENT, (room_id, limit))
            rows = await cur.fetchall()
    return [MessageRow(*row) for row in rows]


async def list_messages_in_range(
    pool: Any,
    *,
    room_id: int,
    start_ts: datetime,
    end_ts: datetime,
    limit: int = 1000,
) -> List[MessageRow]:
    """룸의 [start_ts, end_ts) 구간 timeline — ChatView lazy load 의 server-side (사이클 60).

    의도: 클라이언트가 스크롤 시 과거 메시지를 시간 구간 단위(default 30일 batch)로 lazy fetch 할 때의
    query source. limit 상한으로 unbounded SELECT 를 차단해 메모리 누수를 방지한다
    ([[feedback-chat-accumulation-memory-release-mandatory]] 정합). 부작용 없음(SELECT only).

    Parameters
    ----------
    pool : Any
        asyncmy pool(또는 mock).
    room_id : int
        대상 room.
    start_ts : datetime
        구간 시작(inclusive). tz(UTC/KST) 정합은 호출자 책임.
    end_ts : datetime
        구간 끝(exclusive). start_ts 초과 의무(아니면 ValueError).
    limit : int, default 1000
        page size 상한(unbounded 차단). 비양수 시 ValueError.

    Returns
    -------
    list[MessageRow]
        created_at DESC + id DESC 정렬(최신 → 과거). 화면 표시 순서로의 reverse 는 호출자 책임.

    Raises
    ------
    ValueError
        end_ts <= start_ts(역구간) 또는 limit 비양수.
    """

    if end_ts <= start_ts:
        raise ValueError(
            f"end_ts 의 start_ts 초과 의무 — start={start_ts} end={end_ts}"
        )
    if limit <= 0:
        raise ValueError(f"limit 양수 의무 — {limit}")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_LIST_RANGE, (room_id, start_ts, end_ts, limit))
            rows = await cur.fetchall()
    return [MessageRow(*row) for row in rows]
