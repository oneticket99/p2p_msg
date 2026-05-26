# SPDX-License-Identifier: GPL-3.0-or-later
"""bot_escalations 영속화 repository — 봇 상담 에스컬레이션 ticket (Phase 3 cycle 86).

역할
----
봇이 처리 못 한 문의를 사람 상담원에게 넘기는 ticket 의 생명주기(enqueue → assign → resolve/close)를
영속한다. 이전 in-memory queue 를 DB 영속으로 격상(서버 재시작에도 ticket 보존).

계층 위치 (정본 §E)
-------------------
server data 계층(repository). 호출자 = bot escalation handler + 상담원 console.
DDL 정합: ``server/db/migrations/0005_bot_escalations.sql``. pool DI + parameterized SQL.

invariant / 설계 결정
--------------------
- TicketStatus + EscalationReason ENUM = ``app.bot.escalation_queue`` 재사용(클라/서버 단일 정의).
- 상태 전이 — pending → assigned → resolved → closed. assign/resolve 는 WHERE 에 직전 상태를 둬
  부정합 전이를 차단(rowcount 0 으로 미적용 통지).
- 시각은 epoch ms(created_at_ms/resolved_at_ms) — tz 무관 정렬·retention 계산 일관.
- 8 공개 함수 — enqueue + assign + resolve + close_ticket + get + list_pending + list_by_user + evict_old.

부작용
------
enqueue/assign/resolve/close/evict 는 write(commit). get/list 류는 부작용 없음(SELECT only).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, List, Optional

from app.bot.escalation_queue import EscalationReason, TicketStatus


@dataclass(frozen=True, slots=True)
class EscalationRow:
    """bot_escalations row 도메인 객체."""

    id: int
    user_id: int
    reason: EscalationReason
    message: str
    status: TicketStatus
    agent_id: Optional[int]
    created_at_ms: int
    resolved_at_ms: Optional[int]


# ─── SQL ────────────────────────────────────────────────────────────────────

_INSERT = """
INSERT INTO bot_escalations
    (user_id, reason, message, status, created_at_ms)
VALUES
    (%s, %s, %s, 'pending', %s)
"""

_ASSIGN = """
UPDATE bot_escalations
    SET status = 'assigned', agent_id = %s
    WHERE id = %s AND status = 'pending'
"""

_RESOLVE = """
UPDATE bot_escalations
    SET status = 'resolved', resolved_at_ms = %s
    WHERE id = %s AND status = 'assigned'
"""

_CLOSE = """
UPDATE bot_escalations
    SET status = 'closed', resolved_at_ms = %s
    WHERE id = %s AND status != 'closed'
"""

_SELECT_BY_ID = """
SELECT id, user_id, reason, message, status, agent_id, created_at_ms, resolved_at_ms
    FROM bot_escalations WHERE id = %s
"""

_SELECT_PENDING = """
SELECT id, user_id, reason, message, status, agent_id, created_at_ms, resolved_at_ms
    FROM bot_escalations WHERE status = 'pending' ORDER BY created_at_ms ASC LIMIT %s
"""

_SELECT_BY_USER = """
SELECT id, user_id, reason, message, status, agent_id, created_at_ms, resolved_at_ms
    FROM bot_escalations WHERE user_id = %s ORDER BY created_at_ms DESC LIMIT %s
"""

_SELECT_BY_AGENT = """
SELECT id, user_id, reason, message, status, agent_id, created_at_ms, resolved_at_ms
    FROM bot_escalations WHERE agent_id = %s ORDER BY created_at_ms DESC LIMIT %s
"""

_EVICT_OLD = """
DELETE FROM bot_escalations
    WHERE status IN ('resolved', 'closed')
        AND resolved_at_ms IS NOT NULL
        AND resolved_at_ms < %s
"""


def _row_to_dataclass(row: tuple) -> EscalationRow:
    return EscalationRow(
        id=int(row[0]),
        user_id=int(row[1]),
        reason=EscalationReason(row[2]),
        message=str(row[3]),
        status=TicketStatus(row[4]),
        agent_id=int(row[5]) if row[5] is not None else None,
        created_at_ms=int(row[6]),
        resolved_at_ms=int(row[7]) if row[7] is not None else None,
    )


# ─── repository 함수 ────────────────────────────────────────────────────────

async def enqueue(
    pool: Any,
    *,
    user_id: int,
    reason: EscalationReason,
    message: str,
    created_at_ms: Optional[int] = None,
) -> int:
    """신규 ticket INSERT — 반환값 = lastrowid (ticket id)."""

    if pool is None:
        raise ValueError("pool 의무")
    if user_id <= 0:
        raise ValueError(f"user_id 양수 의무 — {user_id}")
    if not message:
        raise ValueError("message 빈 차단")
    if len(message) > 16384:
        raise ValueError(f"message 16KB cap — 실 {len(message)}")
    ts_ms = created_at_ms if created_at_ms is not None else int(time.time() * 1000)
    if ts_ms < 0:
        raise ValueError(f"created_at_ms 음수 차단 — {ts_ms}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                _INSERT, (user_id, reason.value, message, ts_ms)
            )
            await conn.commit()
            return int(cur.lastrowid)


async def assign(pool: Any, *, ticket_id: int, agent_id: int) -> int:
    """pending → assigned. 반환값 = rowcount (0 = 미적용, 1 = 적용)."""

    if pool is None:
        raise ValueError("pool 의무")
    if ticket_id <= 0:
        raise ValueError(f"ticket_id 양수 의무 — {ticket_id}")
    if agent_id <= 0:
        raise ValueError(f"agent_id 양수 의무 — {agent_id}")

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_ASSIGN, (agent_id, ticket_id))
            await conn.commit()
            return int(cur.rowcount or 0)


async def resolve(
    pool: Any, *, ticket_id: int, resolved_at_ms: Optional[int] = None
) -> int:
    """assigned → resolved. 반환값 = rowcount."""

    if pool is None:
        raise ValueError("pool 의무")
    if ticket_id <= 0:
        raise ValueError(f"ticket_id 양수 의무 — {ticket_id}")
    ts_ms = resolved_at_ms if resolved_at_ms is not None else int(time.time() * 1000)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_RESOLVE, (ts_ms, ticket_id))
            await conn.commit()
            return int(cur.rowcount or 0)


async def close_ticket(
    pool: Any, *, ticket_id: int, resolved_at_ms: Optional[int] = None
) -> int:
    """모든 status → closed. 반환값 = rowcount."""

    if pool is None:
        raise ValueError("pool 의무")
    if ticket_id <= 0:
        raise ValueError(f"ticket_id 양수 의무 — {ticket_id}")
    ts_ms = resolved_at_ms if resolved_at_ms is not None else int(time.time() * 1000)

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_CLOSE, (ts_ms, ticket_id))
            await conn.commit()
            return int(cur.rowcount or 0)


async def get(pool: Any, ticket_id: int) -> Optional[EscalationRow]:
    """SELECT WHERE id — 없으면 None."""

    if pool is None:
        raise ValueError("pool 의무")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_BY_ID, (ticket_id,))
            row = await cur.fetchone()
            return _row_to_dataclass(row) if row else None


async def list_pending(pool: Any, *, limit: int = 100) -> List[EscalationRow]:
    """status=pending + 오래된 순. FIFO 처리 정합."""

    if pool is None:
        raise ValueError("pool 의무")
    if limit <= 0:
        raise ValueError(f"limit 양수 의무 — {limit}")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_PENDING, (limit,))
            rows = await cur.fetchall()
            return [_row_to_dataclass(r) for r in rows]


async def list_by_user(
    pool: Any, *, user_id: int, limit: int = 100
) -> List[EscalationRow]:
    """user_id 기준 + 최신 순."""

    if pool is None:
        raise ValueError("pool 의무")
    if user_id <= 0 or limit <= 0:
        raise ValueError("user_id + limit 양수 의무")
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_SELECT_BY_USER, (user_id, limit))
            rows = await cur.fetchall()
            return [_row_to_dataclass(r) for r in rows]


async def evict_old(pool: Any, *, retention_ms: int, now_ms: Optional[int] = None) -> int:
    """retention 초과 의 resolved/closed ticket evict. 반환값 = 삭제 row 수."""

    if pool is None:
        raise ValueError("pool 의무")
    if retention_ms < 0:
        raise ValueError(f"retention_ms 음수 차단 — {retention_ms}")
    now = now_ms if now_ms is not None else int(time.time() * 1000)
    cutoff = now - retention_ms

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(_EVICT_OLD, (cutoff,))
            await conn.commit()
            return int(cur.rowcount or 0)
