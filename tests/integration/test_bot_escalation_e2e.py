# SPDX-License-Identifier: GPL-3.0-or-later
"""bot escalation queue chain E2E — cycle 169.675 신설.

chain:
1. enqueue 신규 → PENDING + ticket_id 1
2. enqueue 2nd → ticket_id 2 (monotonic)
3. list_pending → 2건
4. assign → ASSIGNED + agent_id 검증
5. assign PENDING 외 차단 → ValueError
6. resolve ASSIGNED → RESOLVED + resolved_at_ms
7. resolve ASSIGNED 외 차단 → ValueError
8. close any → CLOSED
9. close 의 중복 차단 → ValueError
10. evict_old RESOLVED + retention 경과 → count
"""

from __future__ import annotations

import pytest

from app.bot.escalation_queue import (
    EscalationQueue, EscalationReason, TicketStatus,
)


pytestmark = pytest.mark.integration


class TestEscalationLifecycle:
    def test_enqueue_assigns_monotonic_id(self) -> None:
        q = EscalationQueue()
        t1 = q.enqueue(user_id=10, reason=EscalationReason.RATE_LIMIT,
                       message="too many", created_at_ms=1000)
        t2 = q.enqueue(user_id=11, reason=EscalationReason.JAILBREAK,
                       message="bypass", created_at_ms=1100)
        assert t1.ticket_id == 1
        assert t2.ticket_id == 2
        assert t1.status == TicketStatus.PENDING
        assert t2.reason == EscalationReason.JAILBREAK

    def test_list_pending_returns_two(self) -> None:
        q = EscalationQueue()
        q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                  message="help", created_at_ms=1000)
        q.enqueue(user_id=20, reason=EscalationReason.LOW_CONFIDENCE,
                  message="ambiguous", created_at_ms=1100)
        pending = q.list_pending()
        assert len(pending) == 2
        assert all(t.status == TicketStatus.PENDING for t in pending)

    def test_assign_transitions_to_assigned(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="help", created_at_ms=1000)
        u = q.assign(t.ticket_id, agent_id=99)
        assert u.status == TicketStatus.ASSIGNED
        assert u.agent_id == 99

    def test_assign_non_pending_raises(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        q.assign(t.ticket_id, agent_id=99)
        # 한글 주석 — 두번째 assign 차단
        with pytest.raises(ValueError, match="PENDING 외"):
            q.assign(t.ticket_id, agent_id=88)

    def test_resolve_assigned_transitions_to_resolved(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        q.assign(t.ticket_id, agent_id=99)
        r = q.resolve(t.ticket_id, resolved_at_ms=2000)
        assert r.status == TicketStatus.RESOLVED
        assert r.resolved_at_ms == 2000

    def test_resolve_non_assigned_raises(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        # 한글 주석 — PENDING 상태 resolve 차단
        with pytest.raises(ValueError, match="ASSIGNED 외"):
            q.resolve(t.ticket_id, resolved_at_ms=2000)

    def test_close_from_any_state(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        c = q.close(t.ticket_id, closed_at_ms=3000)
        assert c.status == TicketStatus.CLOSED
        assert c.resolved_at_ms == 3000

    def test_close_duplicate_raises(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        q.close(t.ticket_id, closed_at_ms=3000)
        with pytest.raises(ValueError, match="CLOSED"):
            q.close(t.ticket_id, closed_at_ms=4000)

    def test_evict_old_resolved_retention(self) -> None:
        q = EscalationQueue()
        t = q.enqueue(user_id=10, reason=EscalationReason.USER_REQUEST,
                      message="x", created_at_ms=1000)
        q.assign(t.ticket_id, agent_id=99)
        q.resolve(t.ticket_id, resolved_at_ms=2000)
        # 한글 주석 — retention=500 + now=3000 → cutoff=2500 → 2000 < 2500 evict
        evicted = q.evict_old(now_ms=3000, retention_ms=500)
        assert evicted == 1
        assert q.get(t.ticket_id) is None
