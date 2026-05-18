# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.escalation_queue`` 단위 테스트.

TicketStatus/EscalationReason Enum + EscalationTicket validation +
EscalationQueue (enqueue/assign/resolve/close/list/get/clear/size).
"""

from __future__ import annotations

import pytest

from app.bot.escalation_queue import (
    EscalationQueue,
    EscalationReason,
    EscalationTicket,
    TicketStatus,
)


def _ticket(
    *,
    ticket_id: int = 1,
    user_id: int = 42,
    reason: EscalationReason = EscalationReason.USER_REQUEST,
    message: str = "도움 필요",
    created_at_ms: int = 1_700_000_000_000,
    status: TicketStatus = TicketStatus.PENDING,
) -> EscalationTicket:
    return EscalationTicket(
        ticket_id=ticket_id,
        user_id=user_id,
        reason=reason,
        message=message,
        created_at_ms=created_at_ms,
        status=status,
    )


class TestTicketValidation:
    """``EscalationTicket`` __post_init__ 검증."""

    def test_valid(self) -> None:
        t = _ticket()
        assert t.status == TicketStatus.PENDING

    def test_zero_ticket_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="ticket_id"):
            _ticket(ticket_id=0)

    def test_negative_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id"):
            _ticket(user_id=-1)

    def test_empty_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="message"):
            _ticket(message="")

    def test_negative_created_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="created_at_ms"):
            _ticket(created_at_ms=-1)

    def test_zero_agent_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="agent_id"):
            EscalationTicket(
                ticket_id=1,
                user_id=42,
                reason=EscalationReason.USER_REQUEST,
                message="x",
                created_at_ms=0,
                agent_id=0,
            )

    def test_negative_resolved_at_rejected(self) -> None:
        with pytest.raises(ValueError, match="resolved_at_ms"):
            EscalationTicket(
                ticket_id=1,
                user_id=42,
                reason=EscalationReason.USER_REQUEST,
                message="x",
                created_at_ms=0,
                resolved_at_ms=-1,
            )


class TestEnqueue:
    """enqueue + ticket_id 자동 증가 + PENDING default."""

    def test_enqueue_assigns_id_1(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="후원 환불",
            created_at_ms=1_700_000_000_000,
        )
        assert t.ticket_id == 1
        assert t.status == TicketStatus.PENDING

    def test_enqueue_monotonic_ids(self) -> None:
        q = EscalationQueue()
        a = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        b = q.enqueue(
            user_id=2,
            reason=EscalationReason.JAILBREAK,
            message="y",
            created_at_ms=0,
        )
        assert a.ticket_id == 1
        assert b.ticket_id == 2

    def test_size_after_enqueue(self) -> None:
        q = EscalationQueue()
        q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.enqueue(
            user_id=2,
            reason=EscalationReason.RATE_LIMIT,
            message="y",
            created_at_ms=0,
        )
        assert q.size() == 2


class TestAssign:
    """assign — PENDING → ASSIGNED."""

    def test_assign_happy(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        updated = q.assign(t.ticket_id, agent_id=100)
        assert updated.status == TicketStatus.ASSIGNED
        assert updated.agent_id == 100

    def test_assign_unknown_ticket_raises(self) -> None:
        q = EscalationQueue()
        with pytest.raises(KeyError):
            q.assign(999, agent_id=1)

    def test_assign_already_assigned_rejected(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.assign(t.ticket_id, agent_id=100)
        with pytest.raises(ValueError, match="PENDING 외"):
            q.assign(t.ticket_id, agent_id=200)

    def test_assign_zero_agent_rejected(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        with pytest.raises(ValueError, match="agent_id"):
            q.assign(t.ticket_id, agent_id=0)


class TestResolve:
    """resolve — ASSIGNED → RESOLVED."""

    def test_resolve_happy(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.assign(t.ticket_id, agent_id=100)
        updated = q.resolve(t.ticket_id, resolved_at_ms=1_700_000_001_000)
        assert updated.status == TicketStatus.RESOLVED
        assert updated.resolved_at_ms == 1_700_000_001_000

    def test_resolve_pending_rejected(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        with pytest.raises(ValueError, match="ASSIGNED 외"):
            q.resolve(t.ticket_id, resolved_at_ms=100)

    def test_resolve_negative_ts_rejected(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.assign(t.ticket_id, agent_id=100)
        with pytest.raises(ValueError, match="resolved_at_ms"):
            q.resolve(t.ticket_id, resolved_at_ms=-1)


class TestClose:
    """close — PENDING / ASSIGNED / RESOLVED → CLOSED."""

    def test_close_from_pending(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        updated = q.close(t.ticket_id, closed_at_ms=100)
        assert updated.status == TicketStatus.CLOSED

    def test_close_from_assigned(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.assign(t.ticket_id, agent_id=100)
        updated = q.close(t.ticket_id, closed_at_ms=200)
        assert updated.status == TicketStatus.CLOSED

    def test_close_duplicate_rejected(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=42,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.close(t.ticket_id, closed_at_ms=100)
        with pytest.raises(ValueError, match="CLOSED"):
            q.close(t.ticket_id, closed_at_ms=200)


class TestListAndLookup:
    """list_pending + list_assigned + list_by_user + list_by_agent + get."""

    def test_list_pending_fifo(self) -> None:
        q = EscalationQueue()
        a = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="a",
            created_at_ms=200,
        )
        b = q.enqueue(
            user_id=2,
            reason=EscalationReason.USER_REQUEST,
            message="b",
            created_at_ms=100,
        )
        result = q.list_pending()
        # b 의 created_at 의 의 더 이전 → 먼저
        assert result[0].ticket_id == b.ticket_id
        assert result[1].ticket_id == a.ticket_id

    def test_list_assigned(self) -> None:
        q = EscalationQueue()
        t1 = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="a",
            created_at_ms=0,
        )
        t2 = q.enqueue(
            user_id=2,
            reason=EscalationReason.USER_REQUEST,
            message="b",
            created_at_ms=0,
        )
        q.assign(t1.ticket_id, agent_id=100)
        result = q.list_assigned()
        assert len(result) == 1
        assert result[0].ticket_id == t1.ticket_id

    def test_list_by_user(self) -> None:
        q = EscalationQueue()
        q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="a",
            created_at_ms=0,
        )
        q.enqueue(
            user_id=2,
            reason=EscalationReason.USER_REQUEST,
            message="b",
            created_at_ms=0,
        )
        q.enqueue(
            user_id=1,
            reason=EscalationReason.JAILBREAK,
            message="c",
            created_at_ms=100,
        )
        result = q.list_by_user(1)
        assert len(result) == 2

    def test_list_by_agent(self) -> None:
        q = EscalationQueue()
        t1 = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="a",
            created_at_ms=0,
        )
        t2 = q.enqueue(
            user_id=2,
            reason=EscalationReason.USER_REQUEST,
            message="b",
            created_at_ms=0,
        )
        q.assign(t1.ticket_id, agent_id=100)
        q.assign(t2.ticket_id, agent_id=200)
        assert len(q.list_by_agent(100)) == 1
        assert len(q.list_by_agent(200)) == 1
        assert len(q.list_by_agent(999)) == 0

    def test_get_existing(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="a",
            created_at_ms=0,
        )
        assert q.get(t.ticket_id) is not None

    def test_get_missing_none(self) -> None:
        q = EscalationQueue()
        assert q.get(999) is None


class TestClearAndId:
    """clear + next_ticket_id."""

    def test_clear_resets_ids(self) -> None:
        q = EscalationQueue()
        q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=0,
        )
        q.clear()
        # next_ticket_id 의 1 reset
        next_t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="y",
            created_at_ms=0,
        )
        assert next_t.ticket_id == 1
        assert q.size() == 1

    def test_next_ticket_id_increments(self) -> None:
        q = EscalationQueue()
        assert q.next_ticket_id() == 1
        assert q.next_ticket_id() == 2
        assert q.next_ticket_id() == 3


class TestEvictOld:
    """cycle 91 — RESOLVED / CLOSED ticket 의 N일 경과 evict 검증 (P1-1 회수)."""

    def test_retention_zero_rejected(self) -> None:
        q = EscalationQueue()
        with pytest.raises(ValueError, match="retention_ms"):
            q.evict_old(now_ms=1_700_000_000_000, retention_ms=0)

    def test_evict_old_resolved(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=100,
        )
        q.assign(t.ticket_id, agent_id=100)
        q.resolve(t.ticket_id, resolved_at_ms=200)
        # now=1_000_000 + retention=500_000 → cutoff=500_000 → resolved_at=200 < cutoff → evict
        n = q.evict_old(now_ms=1_000_000, retention_ms=500_000)
        assert n == 1
        assert q.size() == 0

    def test_evict_old_closed(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=100,
        )
        q.close(t.ticket_id, closed_at_ms=200)
        n = q.evict_old(now_ms=1_000_000, retention_ms=500_000)
        assert n == 1
        assert q.size() == 0

    def test_pending_not_evicted(self) -> None:
        q = EscalationQueue()
        q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=100,
        )
        # PENDING = evict 부재 (resolved_at_ms None)
        n = q.evict_old(now_ms=1_000_000, retention_ms=500_000)
        assert n == 0
        assert q.size() == 1

    def test_assigned_not_evicted(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=100,
        )
        q.assign(t.ticket_id, agent_id=100)
        n = q.evict_old(now_ms=1_000_000, retention_ms=500_000)
        assert n == 0  # ASSIGNED 의 resolved_at_ms 부재 → evict 부재
        assert q.size() == 1

    def test_within_retention_not_evicted(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(
            user_id=1,
            reason=EscalationReason.USER_REQUEST,
            message="x",
            created_at_ms=100,
        )
        q.assign(t.ticket_id, agent_id=100)
        q.resolve(t.ticket_id, resolved_at_ms=900_000)
        # cutoff=500_000 → resolved_at=900_000 ≥ cutoff → 유지
        n = q.evict_old(now_ms=1_000_000, retention_ms=500_000)
        assert n == 0
        assert q.size() == 1
