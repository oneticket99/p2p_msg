# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 125 — bot_escalations repository 검증.

Phase 3 cycle 86 in-memory EscalationQueue 의 DB 영속화 wiring.
enqueue / assign / resolve / close / get / list_pending / list_by_user /
evict_old 의 SQL parameter assertion + validation.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot.escalation_queue import EscalationReason, TicketStatus
from server.db.repositories.bot_escalations import (
    assign,
    close_ticket,
    enqueue,
    evict_old,
    get,
    list_by_user,
    list_pending,
    resolve,
)


def _mock_pool(*, lastrowid: int = 1, rowcount: int = 1, fetchone_row: Any = None,
               fetchall_rows: list | None = None) -> Any:
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = lastrowid
    cursor.rowcount = rowcount
    cursor.fetchone = AsyncMock(return_value=fetchone_row)
    cursor.fetchall = AsyncMock(return_value=fetchall_rows or [])

    @asynccontextmanager
    async def cursor_cm() -> Any:
        yield cursor

    conn = MagicMock()
    conn.cursor = lambda: cursor_cm()
    conn.commit = AsyncMock()

    @asynccontextmanager
    async def acquire_cm() -> Any:
        yield conn

    pool = MagicMock()
    pool.acquire = lambda: acquire_cm()
    return pool, cursor


class TestEnqueueValidation:
    @pytest.mark.asyncio
    async def test_pool_none(self) -> None:
        with pytest.raises(ValueError, match="pool"):
            await enqueue(
                None,
                user_id=1,
                reason=EscalationReason.USER_REQUEST,
                message="hi",
            )

    @pytest.mark.asyncio
    async def test_zero_user_id(self) -> None:
        pool, _ = _mock_pool()
        with pytest.raises(ValueError, match="user_id 양수"):
            await enqueue(
                pool,
                user_id=0,
                reason=EscalationReason.JAILBREAK,
                message="x",
            )

    @pytest.mark.asyncio
    async def test_empty_message(self) -> None:
        pool, _ = _mock_pool()
        with pytest.raises(ValueError, match="message"):
            await enqueue(
                pool,
                user_id=1,
                reason=EscalationReason.JAILBREAK,
                message="",
            )

    @pytest.mark.asyncio
    async def test_message_over_16kb(self) -> None:
        pool, _ = _mock_pool()
        with pytest.raises(ValueError, match="16KB"):
            await enqueue(
                pool,
                user_id=1,
                reason=EscalationReason.JAILBREAK,
                message="x" * 16385,
            )


class TestEnqueueExecution:
    @pytest.mark.asyncio
    async def test_insert_params(self) -> None:
        pool, cursor = _mock_pool(lastrowid=42)
        new_id = await enqueue(
            pool,
            user_id=7,
            reason=EscalationReason.USER_REQUEST,
            message="help me",
            created_at_ms=1_700_000_000_000,
        )
        assert new_id == 42
        sql, params = cursor.execute.call_args.args
        assert "INSERT INTO bot_escalations" in sql
        assert params == (7, "user_request", "help me", 1_700_000_000_000)


class TestAssign:
    @pytest.mark.asyncio
    async def test_assign_params(self) -> None:
        pool, cursor = _mock_pool(rowcount=1)
        affected = await assign(pool, ticket_id=42, agent_id=99)
        assert affected == 1
        sql, params = cursor.execute.call_args.args
        assert "assigned" in sql
        assert params == (99, 42)

    @pytest.mark.asyncio
    async def test_zero_agent_rejected(self) -> None:
        pool, _ = _mock_pool()
        with pytest.raises(ValueError, match="agent_id"):
            await assign(pool, ticket_id=1, agent_id=0)


class TestResolve:
    @pytest.mark.asyncio
    async def test_resolve_with_explicit_ts(self) -> None:
        pool, cursor = _mock_pool(rowcount=1)
        affected = await resolve(pool, ticket_id=42, resolved_at_ms=1_700_000_001_000)
        assert affected == 1
        sql, params = cursor.execute.call_args.args
        assert "resolved" in sql
        assert params == (1_700_000_001_000, 42)


class TestCloseTicket:
    @pytest.mark.asyncio
    async def test_close_any_status(self) -> None:
        pool, cursor = _mock_pool(rowcount=1)
        affected = await close_ticket(pool, ticket_id=42, resolved_at_ms=1_700_000_002_000)
        assert affected == 1
        sql, params = cursor.execute.call_args.args
        assert "closed" in sql
        assert params == (1_700_000_002_000, 42)


class TestGet:
    @pytest.mark.asyncio
    async def test_existing_row(self) -> None:
        row = (
            42,
            7,
            "user_request",
            "help me",
            "pending",
            None,
            1_700_000_000_000,
            None,
        )
        pool, _ = _mock_pool(fetchone_row=row)
        result = await get(pool, 42)
        assert result is not None
        assert result.id == 42
        assert result.user_id == 7
        assert result.reason == EscalationReason.USER_REQUEST
        assert result.status == TicketStatus.PENDING
        assert result.agent_id is None
        assert result.resolved_at_ms is None

    @pytest.mark.asyncio
    async def test_none_when_missing(self) -> None:
        pool, _ = _mock_pool(fetchone_row=None)
        result = await get(pool, 999)
        assert result is None


class TestListPending:
    @pytest.mark.asyncio
    async def test_returns_rows(self) -> None:
        rows = [
            (1, 7, "user_request", "msg1", "pending", None, 100, None),
            (2, 8, "jailbreak", "msg2", "pending", None, 200, None),
        ]
        pool, cursor = _mock_pool(fetchall_rows=rows)
        result = await list_pending(pool, limit=10)
        assert len(result) == 2
        assert result[0].id == 1
        assert result[1].reason == EscalationReason.JAILBREAK
        sql, params = cursor.execute.call_args.args
        assert "pending" in sql
        assert "ORDER BY created_at_ms ASC" in sql
        assert params == (10,)


class TestListByUser:
    @pytest.mark.asyncio
    async def test_user_filter(self) -> None:
        rows = [(1, 7, "user_request", "m", "resolved", 99, 100, 200)]
        pool, cursor = _mock_pool(fetchall_rows=rows)
        result = await list_by_user(pool, user_id=7, limit=5)
        assert len(result) == 1
        assert result[0].status == TicketStatus.RESOLVED
        assert result[0].agent_id == 99
        sql, params = cursor.execute.call_args.args
        assert params == (7, 5)


class TestEvictOld:
    @pytest.mark.asyncio
    async def test_retention_cutoff(self) -> None:
        pool, cursor = _mock_pool(rowcount=3)
        deleted = await evict_old(pool, retention_ms=60_000, now_ms=1_700_000_000_000)
        assert deleted == 3
        sql, params = cursor.execute.call_args.args
        assert "DELETE FROM bot_escalations" in sql
        assert params == (1_699_999_940_000,)

    @pytest.mark.asyncio
    async def test_negative_retention_rejected(self) -> None:
        pool, _ = _mock_pool()
        with pytest.raises(ValueError, match="retention_ms"):
            await evict_old(pool, retention_ms=-1)
