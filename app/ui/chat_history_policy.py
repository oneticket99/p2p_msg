# SPDX-License-Identifier: GPL-3.0-or-later
"""ChatView 의 volatile + lazy load 정책 — 사이클 59.

memory `feedback_chat_accumulation_memory_release_mandatory.md` 정합. 누적
채팅 의 unbounded RAM 차단 의무 의 핵심 정책 layer:

- **volatile 정책 (사용자 directive 2026-05-21)** — 30 일 이상 경과 message =
  client RAM 의 휘발 처리. server DB 영속화 만 유지.
- **lazy load 정책** — scroll up 의 viewport top 도달 = 추가 1 개월 batch 의
  server fetch + 위 widget 의 prepend.

본 module 범위 (QWidget 부재 환경 의 unit test 의무):

- ``_MAX_VOLATILE_DAYS`` Final[int] = 30 (사용자 directive 의 정책 constant)
- ``MessageMetadata`` frozen dataclass — message_id + timestamp_ms + room_id
- ``LazyLoadRequest`` frozen dataclass — room_id + before_ts + limit_days
- ``volatile_threshold_ms`` — now_ms - days * 86 400 * 1000 의 cutoff 산출
- ``should_purge`` — meta.timestamp_ms < threshold 의 bool
- ``partition_volatile_active`` — (purge_list, keep_list) tuple
- ``next_load_request`` — scroll top 도달 시 의 LazyLoadRequest 산출
- ``estimate_purged_memory_kb`` — partition 결과 의 회수 memory 의 추산

본 cycle 의 범위 외 (별개 cycle):
- ChatView 의 add_message + scroll signal hook 의 의 통합 (QApplication 의무)
- server `list_messages_in_range(room_id, start_ts, end_ts)` 의 REST + WS 구현
- virtual scroll (별개 cycle — visible widget 만 render + spacer placeholder)
- 별개 thread 의 background lazy load + chunked render
- E2EE decrypt 의 lazy load 시점 의 caller responsibility
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, List, Optional, Tuple

# volatile threshold = 30 일 (사용자 directive 2026-05-21 "1개월 이상 휘발")
_MAX_VOLATILE_DAYS: Final[int] = 30
# 1 일 = 86 400 초 = 86 400 000 ms
_MS_PER_DAY: Final[int] = 86_400 * 1_000
# 단일 message widget 의 추산 memory (KB). 회수 memory 의 추산 의 의무.
# UI bubble + text + metadata 약 10 KB / message 의 추정 (사용자 directive
# memory release 의 trace 검증 의 별개 cycle 의 의무).
_ESTIMATED_KB_PER_MESSAGE: Final[float] = 10.0


@dataclass(frozen=True, slots=True)
class MessageMetadata:
    """ChatView 의 단일 message 의 metadata.

    Attributes
    ----------
    message_id : str
        message 고유 식별자 (server-side msg id 또는 local UUID).
    timestamp_ms : int
        message 시점 (UNIX epoch ms).
    room_id : int
        message 의 room 식별자 (lazy load 시 의 query 범위).
    """

    message_id: str
    timestamp_ms: int
    room_id: int

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ValueError("message_id 빈 문자열 불가")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms 음수 불가 — {self.timestamp_ms}")
        if self.room_id <= 0:
            raise ValueError(f"room_id 양수 의무 — {self.room_id}")


@dataclass(frozen=True, slots=True)
class LazyLoadRequest:
    """scroll top 도달 의 server fetch 요청.

    Attributes
    ----------
    room_id : int
        대상 room.
    before_ts : int
        cursor 시점 (UNIX epoch ms). 의 이전 의 message 만 의 query 의무.
    limit_days : int
        1 page 의 일 단위 (default 30 일 의무).
    """

    room_id: int
    before_ts: int
    limit_days: int = _MAX_VOLATILE_DAYS

    def __post_init__(self) -> None:
        if self.room_id <= 0:
            raise ValueError(f"room_id 양수 의무 — {self.room_id}")
        if self.before_ts <= 0:
            raise ValueError(f"before_ts 양수 의무 — {self.before_ts}")
        if self.limit_days <= 0:
            raise ValueError(f"limit_days 양수 의무 — {self.limit_days}")

    @property
    def start_ts(self) -> int:
        """before_ts - limit_days * 86 400 000 ms 의 fetch 범위 시작점."""

        return max(0, self.before_ts - self.limit_days * _MS_PER_DAY)


def volatile_threshold_ms(
    now_ms: int,
    days: int = _MAX_VOLATILE_DAYS,
) -> int:
    """volatile cutoff 산출 — now_ms - days * 86 400 000.

    Parameters
    ----------
    now_ms : int
        현재 시점 (UNIX epoch ms, caller responsibility).
    days : int
        volatile 기준 일 (default 30).

    Returns
    -------
    int
        cutoff ms. 본 ms 미만 의 timestamp 의 message = purge 대상.
    """

    if now_ms < 0:
        raise ValueError(f"now_ms 음수 불가 — {now_ms}")
    if days <= 0:
        raise ValueError(f"days 양수 의무 — {days}")
    return max(0, now_ms - days * _MS_PER_DAY)


def should_purge(
    meta: MessageMetadata,
    now_ms: int,
    days: int = _MAX_VOLATILE_DAYS,
) -> bool:
    """단일 meta 의 purge 대상 여부.

    Notes
    -----
    `meta.timestamp_ms < cutoff` 의 정확 비교. 정확 cutoff 시점 = keep (>=) 의무.
    """

    cutoff = volatile_threshold_ms(now_ms, days)
    return meta.timestamp_ms < cutoff


def partition_volatile_active(
    metas: List[MessageMetadata],
    now_ms: int,
    days: int = _MAX_VOLATILE_DAYS,
) -> Tuple[List[MessageMetadata], List[MessageMetadata]]:
    """metas → (purge_list, keep_list) 의 partition.

    Returns
    -------
    tuple[list, list]
        (purge_list, keep_list). 입력 순서 의 의무 보존.
    """

    cutoff = volatile_threshold_ms(now_ms, days)
    purge: List[MessageMetadata] = []
    keep: List[MessageMetadata] = []
    for meta in metas:
        if meta.timestamp_ms < cutoff:
            purge.append(meta)
        else:
            keep.append(meta)
    return (purge, keep)


def next_load_request(
    room_id: int,
    oldest_loaded_ts: int,
    days: int = _MAX_VOLATILE_DAYS,
) -> LazyLoadRequest:
    """scroll top 도달 시 의 다음 fetch 요청 의 산출.

    Parameters
    ----------
    room_id : int
        대상 room.
    oldest_loaded_ts : int
        client RAM 의 가장 오래된 message 의 timestamp_ms. 의 이전 의 추가 fetch.
    days : int
        1 page 의 일 단위 (default 30).

    Returns
    -------
    LazyLoadRequest
        before_ts = oldest_loaded_ts + limit_days = days.
    """

    return LazyLoadRequest(
        room_id=room_id,
        before_ts=oldest_loaded_ts,
        limit_days=days,
    )


def estimate_purged_memory_kb(
    purge_count: int,
    kb_per_message: float = _ESTIMATED_KB_PER_MESSAGE,
) -> float:
    """purge 의 message 의 의 회수 memory 의 추산 (KB).

    Notes
    -----
    실 회수 의 추산 = QWidget 의 add_message 의 차원 별개 cycle 의 tracemalloc
    검증 의무. 본 값 = 10 KB / message 의 추정 (RAM cap 산정 기준값).
    """

    if purge_count < 0:
        raise ValueError(f"purge_count 음수 불가 — {purge_count}")
    if kb_per_message <= 0:
        raise ValueError(f"kb_per_message 양수 의무 — {kb_per_message}")
    return purge_count * kb_per_message


def oldest_timestamp(metas: List[MessageMetadata]) -> Optional[int]:
    """metas 의 최소 timestamp_ms 산출. 빈 list = None."""

    if not metas:
        return None
    return min(m.timestamp_ms for m in metas)
