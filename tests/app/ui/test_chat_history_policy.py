# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.ui.chat_history_policy`` 단위 테스트.

volatile + lazy load 정책 의 cutoff + partition + LazyLoadRequest +
memory 추산 + oldest_timestamp.
"""

from __future__ import annotations

import pytest

from app.ui.chat_history_policy import (
    LazyLoadRequest,
    MessageMetadata,
    estimate_purged_memory_kb,
    next_load_request,
    oldest_timestamp,
    partition_volatile_active,
    should_purge,
    volatile_threshold_ms,
)

# 30 일 ms = 30 * 86_400_000
_30_DAYS_MS = 30 * 86_400 * 1_000
# 임의 baseline now = 2026-05-21 00:00 UTC ms 등가
_BASE_NOW_MS = 1_779_062_400_000


def _meta(ts_ms: int, msg_id: str = "m1", room_id: int = 1) -> MessageMetadata:
    """test fixture — 단일 metadata."""

    return MessageMetadata(message_id=msg_id, timestamp_ms=ts_ms, room_id=room_id)


class TestMessageMetadataValidation:
    """``MessageMetadata`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        meta = _meta(ts_ms=100)
        assert meta.message_id == "m1"
        assert meta.timestamp_ms == 100

    def test_empty_message_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="message_id 빈 문자열 불가"):
            MessageMetadata(message_id="", timestamp_ms=1, room_id=1)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            MessageMetadata(message_id="m", timestamp_ms=-1, room_id=1)

    def test_zero_room_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="room_id 양수 의무"):
            MessageMetadata(message_id="m", timestamp_ms=1, room_id=0)


class TestLazyLoadRequestValidation:
    """``LazyLoadRequest`` dataclass 검증."""

    def test_valid_construction(self) -> None:
        req = LazyLoadRequest(room_id=1, before_ts=_BASE_NOW_MS, limit_days=30)
        assert req.limit_days == 30

    def test_default_limit_days(self) -> None:
        req = LazyLoadRequest(room_id=1, before_ts=_BASE_NOW_MS)
        assert req.limit_days == 30

    def test_zero_room_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="room_id 양수 의무"):
            LazyLoadRequest(room_id=0, before_ts=100)

    def test_zero_before_ts_rejected(self) -> None:
        with pytest.raises(ValueError, match="before_ts 양수 의무"):
            LazyLoadRequest(room_id=1, before_ts=0)

    def test_zero_limit_days_rejected(self) -> None:
        with pytest.raises(ValueError, match="limit_days 양수 의무"):
            LazyLoadRequest(room_id=1, before_ts=100, limit_days=0)

    def test_start_ts_property(self) -> None:
        req = LazyLoadRequest(room_id=1, before_ts=_BASE_NOW_MS, limit_days=30)
        assert req.start_ts == _BASE_NOW_MS - _30_DAYS_MS

    def test_start_ts_clamped_to_zero(self) -> None:
        # before_ts = 1 day, limit = 30 days → start = clamped to 0
        req = LazyLoadRequest(
            room_id=1, before_ts=86_400_000, limit_days=30
        )
        assert req.start_ts == 0


class TestVolatileThreshold:
    """``volatile_threshold_ms`` 검증."""

    def test_basic_30_days(self) -> None:
        cutoff = volatile_threshold_ms(_BASE_NOW_MS, days=30)
        assert cutoff == _BASE_NOW_MS - _30_DAYS_MS

    def test_default_days_30(self) -> None:
        cutoff = volatile_threshold_ms(_BASE_NOW_MS)
        assert cutoff == _BASE_NOW_MS - _30_DAYS_MS

    def test_custom_7_days(self) -> None:
        cutoff = volatile_threshold_ms(_BASE_NOW_MS, days=7)
        assert cutoff == _BASE_NOW_MS - 7 * 86_400_000

    def test_clamped_to_zero(self) -> None:
        # now_ms < 30 일 = clamp 0
        cutoff = volatile_threshold_ms(1_000_000, days=30)
        assert cutoff == 0

    def test_negative_now_rejected(self) -> None:
        with pytest.raises(ValueError, match="now_ms 음수 불가"):
            volatile_threshold_ms(-1)

    def test_zero_days_rejected(self) -> None:
        with pytest.raises(ValueError, match="days 양수 의무"):
            volatile_threshold_ms(_BASE_NOW_MS, days=0)


class TestShouldPurge:
    """``should_purge`` 경계 검증."""

    def test_old_message_purged(self) -> None:
        # 31 일 경과
        old = _meta(ts_ms=_BASE_NOW_MS - 31 * 86_400_000)
        assert should_purge(old, _BASE_NOW_MS) is True

    def test_recent_message_kept(self) -> None:
        recent = _meta(ts_ms=_BASE_NOW_MS - 10 * 86_400_000)
        assert should_purge(recent, _BASE_NOW_MS) is False

    def test_boundary_exact_30_days_kept(self) -> None:
        # 정확 cutoff 시점 = keep (>= 의 정합)
        boundary = _meta(ts_ms=_BASE_NOW_MS - _30_DAYS_MS)
        assert should_purge(boundary, _BASE_NOW_MS) is False

    def test_boundary_30_days_plus_1ms_purged(self) -> None:
        purge = _meta(ts_ms=_BASE_NOW_MS - _30_DAYS_MS - 1)
        assert should_purge(purge, _BASE_NOW_MS) is True


class TestPartitionVolatileActive:
    """``partition_volatile_active`` 검증."""

    def test_empty_metas(self) -> None:
        purge, keep = partition_volatile_active([], _BASE_NOW_MS)
        assert purge == []
        assert keep == []

    def test_all_kept(self) -> None:
        metas = [
            _meta(ts_ms=_BASE_NOW_MS - 1, msg_id="a"),
            _meta(ts_ms=_BASE_NOW_MS - 1000, msg_id="b"),
        ]
        purge, keep = partition_volatile_active(metas, _BASE_NOW_MS)
        assert purge == []
        assert len(keep) == 2

    def test_all_purged(self) -> None:
        metas = [
            _meta(ts_ms=1, msg_id="a"),
            _meta(ts_ms=100, msg_id="b"),
        ]
        purge, keep = partition_volatile_active(metas, _BASE_NOW_MS)
        assert len(purge) == 2
        assert keep == []

    def test_split_correctly(self) -> None:
        metas = [
            _meta(ts_ms=_BASE_NOW_MS - 31 * 86_400_000, msg_id="old"),
            _meta(ts_ms=_BASE_NOW_MS - 10 * 86_400_000, msg_id="recent"),
            _meta(ts_ms=_BASE_NOW_MS - 60 * 86_400_000, msg_id="very_old"),
        ]
        purge, keep = partition_volatile_active(metas, _BASE_NOW_MS)
        assert {m.message_id for m in purge} == {"old", "very_old"}
        assert {m.message_id for m in keep} == {"recent"}

    def test_order_preserved(self) -> None:
        metas = [
            _meta(ts_ms=_BASE_NOW_MS - 1, msg_id="newest"),
            _meta(ts_ms=_BASE_NOW_MS - 2, msg_id="mid"),
            _meta(ts_ms=_BASE_NOW_MS - 3, msg_id="oldest"),
        ]
        _, keep = partition_volatile_active(metas, _BASE_NOW_MS)
        assert [m.message_id for m in keep] == ["newest", "mid", "oldest"]


class TestNextLoadRequest:
    """``next_load_request`` 검증."""

    def test_default_30_days(self) -> None:
        req = next_load_request(room_id=42, oldest_loaded_ts=_BASE_NOW_MS)
        assert req.room_id == 42
        assert req.before_ts == _BASE_NOW_MS
        assert req.limit_days == 30

    def test_custom_7_days(self) -> None:
        req = next_load_request(room_id=1, oldest_loaded_ts=_BASE_NOW_MS, days=7)
        assert req.limit_days == 7

    def test_start_ts_chain(self) -> None:
        # cursor → before_ts → start_ts = before_ts - 30 days
        req = next_load_request(room_id=1, oldest_loaded_ts=_BASE_NOW_MS)
        assert req.start_ts == _BASE_NOW_MS - _30_DAYS_MS


class TestEstimatePurgedMemory:
    """``estimate_purged_memory_kb`` 검증."""

    def test_zero_count(self) -> None:
        assert estimate_purged_memory_kb(0) == 0.0

    def test_default_10kb_per_message(self) -> None:
        # 1000 message * 10 KB = 10 MB
        assert estimate_purged_memory_kb(1000) == 10_000.0

    def test_custom_kb_per_message(self) -> None:
        # 100 message * 5 KB = 500 KB
        assert estimate_purged_memory_kb(100, kb_per_message=5.0) == 500.0

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="purge_count 음수 불가"):
            estimate_purged_memory_kb(-1)

    def test_zero_kb_per_message_rejected(self) -> None:
        with pytest.raises(ValueError, match="kb_per_message 양수 의무"):
            estimate_purged_memory_kb(10, kb_per_message=0)


class TestOldestTimestamp:
    """``oldest_timestamp`` 검증."""

    def test_empty_returns_none(self) -> None:
        assert oldest_timestamp([]) is None

    def test_single_message(self) -> None:
        metas = [_meta(ts_ms=100)]
        assert oldest_timestamp(metas) == 100

    def test_unordered_metas(self) -> None:
        metas = [
            _meta(ts_ms=300, msg_id="c"),
            _meta(ts_ms=100, msg_id="a"),
            _meta(ts_ms=200, msg_id="b"),
        ]
        assert oldest_timestamp(metas) == 100
