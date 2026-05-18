# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 3 bot 사람 상담 escalation queue — 사이클 86.

memory `project_bot_framework.md` + bot-framework.md §10 의 "escalation 사람
상담 — queue + assign + handover" 별개 cycle entry.

본 module 범위
-------------
- ``TicketStatus`` Enum (PENDING / ASSIGNED / RESOLVED / CLOSED)
- ``EscalationReason`` Enum (USER_REQUEST / JAILBREAK / RATE_LIMIT /
  LOW_CONFIDENCE / LONG_RESPONSE / EXPLICIT)
- ``EscalationTicket`` frozen dataclass — ticket_id + user_id + reason +
  message + created_at_ms + status + agent_id (Optional) + resolved_at_ms
- ``EscalationQueue`` class — enqueue + assign + resolve + close + list_pending
  + list_assigned + get + size + clear
- ``next_ticket_id`` 자동 증가 helper (in-memory + monotonic)

본 cycle 의 범위 외 (별개 cycle):
- DB 영속화 (현 in-memory only — server restart 시 의 손실)
- agent assignment policy (round-robin + load balance + skill matching)
- SLA timer (PENDING → ASSIGNED 의 의 5분 cap + alert)
- notification (사용자 의 의 상담사 ETA 안내 + 의 의 push)
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Dict, List, Optional


class TicketStatus(Enum):
    """ticket 의 lifecycle 상태."""

    PENDING = "pending"  # 대기 (assigned 부재)
    ASSIGNED = "assigned"  # 상담사 배정 + 응답 중
    RESOLVED = "resolved"  # 응답 완료
    CLOSED = "closed"  # 사용자 의 종료 또는 timeout


class EscalationReason(Enum):
    """escalation 의 사유 — auto-routing + analytics 의 base."""

    USER_REQUEST = "user_request"  # 사용자 의 직접 요청
    JAILBREAK = "jailbreak"  # cycle 81 의 BLOCKED → 사람 검토
    RATE_LIMIT = "rate_limit"  # 분당 한도 초과 → 사람 backup
    LOW_CONFIDENCE = "low_confidence"  # bot 응답 의 의 정확도 의심
    LONG_RESPONSE = "long_response"  # 800자 한도 초과 의 escalation
    EXPLICIT = "explicit"  # caller 의 명시 (예: 사기 신고)


@dataclass(frozen=True, slots=True)
class EscalationTicket:
    """단일 escalation 의 ticket — immutable.

    Attributes
    ----------
    ticket_id : int
        고유 식별자 (양수).
    user_id : int
        대상 사용자 (양수).
    reason : EscalationReason
        escalation 의 사유.
    message : str
        사용자 의 마지막 메시지 또는 escalation 의 context (빈 차단).
    created_at_ms : int
        생성 시점 UNIX epoch ms (음수 차단).
    status : TicketStatus
        현 lifecycle 상태 (default PENDING).
    agent_id : int | None
        배정된 상담사 user_id (ASSIGNED 시 의무).
    resolved_at_ms : int | None
        RESOLVED / CLOSED 시점 의 timestamp.
    """

    ticket_id: int
    user_id: int
    reason: EscalationReason
    message: str
    created_at_ms: int
    status: TicketStatus = TicketStatus.PENDING
    agent_id: Optional[int] = None
    resolved_at_ms: Optional[int] = None

    def __post_init__(self) -> None:
        if self.ticket_id <= 0:
            raise ValueError(f"ticket_id 양수 의무 — {self.ticket_id}")
        if self.user_id <= 0:
            raise ValueError(f"user_id 양수 의무 — {self.user_id}")
        if not self.message:
            raise ValueError("message 빈 문자열 불가")
        if self.created_at_ms < 0:
            raise ValueError(
                f"created_at_ms 음수 차단 — {self.created_at_ms}"
            )
        if self.agent_id is not None and self.agent_id <= 0:
            raise ValueError(f"agent_id 양수 의무 — {self.agent_id}")
        if self.resolved_at_ms is not None and self.resolved_at_ms < 0:
            raise ValueError(
                f"resolved_at_ms 음수 차단 — {self.resolved_at_ms}"
            )


class EscalationQueue:
    """in-memory ticket queue + lifecycle 관리.

    Notes
    -----
    thread-safety 미보장 — async single event loop 의 가정. DB 영속화 부재 +
    server restart 시 의 손실. ticket_id 자동 증가 (1 부터 시작).

    cycle 91 — RESOLVED / CLOSED 의 ticket 의 N일 경과 시 evict 의 unbounded
    memory growth 차단 (reviewer P1-1). caller 가 주기 `evict_old` 호출.
    """

    def __init__(self) -> None:
        self._tickets: Dict[int, EscalationTicket] = {}
        self._next_id: int = 1

    def evict_old(self, now_ms: int, retention_ms: int) -> int:
        """RESOLVED / CLOSED 상태 + resolved_at_ms + retention_ms 경과 ticket evict.

        Parameters
        ----------
        now_ms : int
            현 시점 UNIX epoch ms.
        retention_ms : int
            보존 기간 (예: 30일 = 30 * 86_400_000).

        Returns
        -------
        int
            evict 된 ticket 수.
        """

        if retention_ms <= 0:
            raise ValueError(f"retention_ms 양수 의무 — {retention_ms}")
        cutoff = now_ms - retention_ms
        terminal = {TicketStatus.RESOLVED, TicketStatus.CLOSED}
        targets = [
            tid
            for tid, t in self._tickets.items()
            if t.status in terminal
            and t.resolved_at_ms is not None
            and t.resolved_at_ms < cutoff
        ]
        for tid in targets:
            del self._tickets[tid]
        return len(targets)

    def next_ticket_id(self) -> int:
        """다음 ticket_id 의 monotonic 증가 + 반환."""

        tid = self._next_id
        self._next_id += 1
        return tid

    def enqueue(
        self,
        *,
        user_id: int,
        reason: EscalationReason,
        message: str,
        created_at_ms: int,
    ) -> EscalationTicket:
        """신규 ticket 의 PENDING 상태 의 enqueue.

        Returns
        -------
        EscalationTicket
            자동 할당 된 ticket_id 의 ticket.
        """

        tid = self.next_ticket_id()
        ticket = EscalationTicket(
            ticket_id=tid,
            user_id=user_id,
            reason=reason,
            message=message,
            created_at_ms=created_at_ms,
        )
        self._tickets[tid] = ticket
        return ticket

    def get(self, ticket_id: int) -> Optional[EscalationTicket]:
        """ticket_id → ticket 의 lookup (부재 시 None)."""

        return self._tickets.get(ticket_id)

    def assign(
        self, ticket_id: int, agent_id: int
    ) -> EscalationTicket:
        """PENDING ticket 의 상담사 배정 + ASSIGNED 전환.

        Raises
        ------
        KeyError
            ticket_id 부재.
        ValueError
            PENDING 외 상태 의 의 assign 또는 agent_id invalid.
        """

        if agent_id <= 0:
            raise ValueError(f"agent_id 양수 의무 — {agent_id}")
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError(f"ticket_id 부재 — {ticket_id}")
        if ticket.status != TicketStatus.PENDING:
            raise ValueError(
                f"PENDING 외 상태 의 assign 차단 — 실 {ticket.status.value}"
            )
        updated = replace(
            ticket, status=TicketStatus.ASSIGNED, agent_id=agent_id
        )
        self._tickets[ticket_id] = updated
        return updated

    def resolve(
        self, ticket_id: int, resolved_at_ms: int
    ) -> EscalationTicket:
        """ASSIGNED ticket 의 RESOLVED 전환.

        Raises
        ------
        KeyError, ValueError
            동일 의무.
        """

        if resolved_at_ms < 0:
            raise ValueError(
                f"resolved_at_ms 음수 차단 — {resolved_at_ms}"
            )
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError(f"ticket_id 부재 — {ticket_id}")
        if ticket.status != TicketStatus.ASSIGNED:
            raise ValueError(
                f"ASSIGNED 외 상태 의 resolve 차단 — 실 {ticket.status.value}"
            )
        updated = replace(
            ticket,
            status=TicketStatus.RESOLVED,
            resolved_at_ms=resolved_at_ms,
        )
        self._tickets[ticket_id] = updated
        return updated

    def close(
        self, ticket_id: int, closed_at_ms: int
    ) -> EscalationTicket:
        """ticket 의 CLOSED 전환 — PENDING / ASSIGNED / RESOLVED 의 의 모두 허용.

        사용자 종료 또는 timeout 시 강제 종료.
        """

        if closed_at_ms < 0:
            raise ValueError(f"closed_at_ms 음수 차단 — {closed_at_ms}")
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError(f"ticket_id 부재 — {ticket_id}")
        if ticket.status == TicketStatus.CLOSED:
            raise ValueError("CLOSED 의 의 close 중복 차단")
        updated = replace(
            ticket,
            status=TicketStatus.CLOSED,
            resolved_at_ms=closed_at_ms,
        )
        self._tickets[ticket_id] = updated
        return updated

    def list_pending(self) -> List[EscalationTicket]:
        """PENDING 상태 ticket — created_at_ms ASC 정렬 (FIFO)."""

        return sorted(
            [t for t in self._tickets.values() if t.status == TicketStatus.PENDING],
            key=lambda t: t.created_at_ms,
        )

    def list_assigned(self) -> List[EscalationTicket]:
        """ASSIGNED 상태 ticket — created_at_ms ASC."""

        return sorted(
            [t for t in self._tickets.values() if t.status == TicketStatus.ASSIGNED],
            key=lambda t: t.created_at_ms,
        )

    def list_by_user(self, user_id: int) -> List[EscalationTicket]:
        """특정 사용자 의 모든 ticket — created_at_ms ASC."""

        return sorted(
            [t for t in self._tickets.values() if t.user_id == user_id],
            key=lambda t: t.created_at_ms,
        )

    def list_by_agent(self, agent_id: int) -> List[EscalationTicket]:
        """특정 상담사 의 배정 ticket — created_at_ms ASC."""

        return sorted(
            [t for t in self._tickets.values() if t.agent_id == agent_id],
            key=lambda t: t.created_at_ms,
        )

    def size(self) -> int:
        """누적 ticket 수 (모든 status)."""

        return len(self._tickets)

    def clear(self) -> None:
        """전수 reset — _next_id 도 1 로 reset."""

        self._tickets.clear()
        self._next_id = 1
