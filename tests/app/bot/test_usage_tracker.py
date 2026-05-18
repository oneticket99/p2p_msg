# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.usage_tracker`` 단위 테스트.

UsageRecord validation + UsageSummary + UsageTracker (record + summarize +
per-user + per-provider + per-period) + Anthropic/OpenAI usage extract.
"""

from __future__ import annotations

import pytest

from app.bot.usage_tracker import (
    UsageRecord,
    UsageSummary,
    UsageTracker,
    extract_anthropic_usage,
    extract_openai_usage,
)


def _record(
    *,
    user_id: int = 7,
    provider: str = "anthropic",
    model: str = "claude-3-5-sonnet-latest",
    input_tokens: int = 100,
    output_tokens: int = 200,
    timestamp_ms: int = 1_700_000_000_000,
) -> UsageRecord:
    return UsageRecord(
        user_id=user_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp_ms=timestamp_ms,
    )


class TestUsageRecordValidation:
    """``UsageRecord`` validation 검증."""

    def test_valid(self) -> None:
        r = _record()
        assert r.total_tokens == 300

    def test_zero_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id"):
            _record(user_id=0)

    def test_negative_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="user_id"):
            _record(user_id=-1)

    def test_empty_provider_rejected(self) -> None:
        with pytest.raises(ValueError, match="provider"):
            _record(provider="")

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="model"):
            _record(model="")

    def test_negative_input_tokens_rejected(self) -> None:
        with pytest.raises(ValueError, match="input_tokens"):
            _record(input_tokens=-1)

    def test_negative_output_tokens_rejected(self) -> None:
        with pytest.raises(ValueError, match="output_tokens"):
            _record(output_tokens=-1)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms"):
            _record(timestamp_ms=-1)

    def test_zero_tokens_allowed(self) -> None:
        # 0 token 의 호출 가능 (cached / error 시점)
        r = _record(input_tokens=0, output_tokens=0)
        assert r.total_tokens == 0


class TestUsageSummary:
    """``UsageSummary`` total_tokens 검증."""

    def test_total(self) -> None:
        s = UsageSummary(count=5, input_tokens=100, output_tokens=200)
        assert s.total_tokens == 300

    def test_zero(self) -> None:
        s = UsageSummary(count=0, input_tokens=0, output_tokens=0)
        assert s.total_tokens == 0


class TestUsageTracker:
    """``UsageTracker`` record + summarize + clear."""

    def test_empty_size_zero(self) -> None:
        t = UsageTracker()
        assert t.size() == 0

    def test_record_increments_size(self) -> None:
        t = UsageTracker()
        t.record(_record())
        t.record(_record())
        assert t.size() == 2

    def test_clear_resets(self) -> None:
        t = UsageTracker()
        t.record(_record())
        t.clear()
        assert t.size() == 0

    def test_all_records_returns_copy(self) -> None:
        t = UsageTracker()
        t.record(_record())
        records = t.all_records()
        records.clear()  # mutation should not affect tracker
        assert t.size() == 1

    def test_summarize_by_user(self) -> None:
        t = UsageTracker()
        t.record(_record(user_id=1, input_tokens=10, output_tokens=20))
        t.record(_record(user_id=1, input_tokens=5, output_tokens=15))
        t.record(_record(user_id=2, input_tokens=100, output_tokens=200))
        s = t.summarize_by_user()
        assert s[1].count == 2
        assert s[1].input_tokens == 15
        assert s[1].output_tokens == 35
        assert s[2].count == 1
        assert s[2].total_tokens == 300

    def test_summarize_by_provider(self) -> None:
        t = UsageTracker()
        t.record(_record(provider="anthropic", input_tokens=10, output_tokens=20))
        t.record(_record(provider="anthropic", input_tokens=5, output_tokens=15))
        t.record(_record(provider="openai", input_tokens=100, output_tokens=200))
        s = t.summarize_by_provider()
        assert s["anthropic"].count == 2
        assert s["anthropic"].total_tokens == 50
        assert s["openai"].count == 1
        assert s["openai"].total_tokens == 300

    def test_summarize_by_minute(self) -> None:
        t = UsageTracker()
        # 1700000000000 ms — bucket = 1700000000000 - (1700000000000 % 60000)
        base = 1_700_000_000_000
        t.record(_record(timestamp_ms=base, input_tokens=10, output_tokens=20))
        t.record(_record(timestamp_ms=base + 5000, input_tokens=5, output_tokens=15))  # same minute
        t.record(_record(timestamp_ms=base + 65_000, input_tokens=100, output_tokens=200))  # next minute
        s = t.summarize_by_period("minute")
        # 2 buckets
        assert len(s) == 2

    def test_summarize_by_hour(self) -> None:
        t = UsageTracker()
        base = 1_700_000_000_000
        t.record(_record(timestamp_ms=base))
        t.record(_record(timestamp_ms=base + 3_600_000 + 1))  # next hour
        s = t.summarize_by_period("hour")
        assert len(s) == 2

    def test_summarize_by_day(self) -> None:
        t = UsageTracker()
        base = 1_700_000_000_000
        t.record(_record(timestamp_ms=base))
        t.record(_record(timestamp_ms=base + 86_400_000 + 1))  # next day
        s = t.summarize_by_period("day")
        assert len(s) == 2

    def test_summarize_period_invalid_rejected(self) -> None:
        t = UsageTracker()
        with pytest.raises(ValueError, match="period"):
            t.summarize_by_period("week")

    def test_total_aggregation(self) -> None:
        t = UsageTracker()
        t.record(_record(input_tokens=10, output_tokens=20))
        t.record(_record(input_tokens=30, output_tokens=40))
        total = t.total()
        assert total.count == 2
        assert total.input_tokens == 40
        assert total.output_tokens == 60
        assert total.total_tokens == 100

    def test_total_empty(self) -> None:
        t = UsageTracker()
        total = t.total()
        assert total.count == 0
        assert total.total_tokens == 0


class TestExtractAnthropicUsage:
    """``extract_anthropic_usage`` 응답 추출."""

    def test_happy(self) -> None:
        body = {
            "usage": {"input_tokens": 123, "output_tokens": 456},
            "content": [],
        }
        assert extract_anthropic_usage(body) == (123, 456)

    def test_missing_usage(self) -> None:
        assert extract_anthropic_usage({"content": []}) == (0, 0)

    def test_non_dict_body(self) -> None:
        assert extract_anthropic_usage(None) == (0, 0)  # type: ignore[arg-type]

    def test_non_int_values(self) -> None:
        body = {"usage": {"input_tokens": "100", "output_tokens": None}}
        assert extract_anthropic_usage(body) == (0, 0)

    def test_negative_clamped(self) -> None:
        body = {"usage": {"input_tokens": -5, "output_tokens": 10}}
        assert extract_anthropic_usage(body) == (0, 10)


class TestExtractOpenAIUsage:
    """``extract_openai_usage`` 응답 추출."""

    def test_happy(self) -> None:
        body = {
            "usage": {"prompt_tokens": 50, "completion_tokens": 80, "total_tokens": 130},
            "choices": [],
        }
        assert extract_openai_usage(body) == (50, 80)

    def test_missing_usage(self) -> None:
        assert extract_openai_usage({"choices": []}) == (0, 0)

    def test_bool_rejected(self) -> None:
        # True / False 의 isinstance(int)=True edge case 차단
        body = {"usage": {"prompt_tokens": True, "completion_tokens": 10}}
        assert extract_openai_usage(body) == (0, 10)


class TestUsageTrackerMaxRecords:
    """cycle 91 — UsageTracker ring buffer maxlen 검증 (P1-1 회수)."""

    def test_default_max_100k(self) -> None:
        t = UsageTracker()
        assert t.max_records == 100_000

    def test_negative_max_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_records"):
            UsageTracker(max_records=-1)

    def test_maxlen_evicts_oldest(self) -> None:
        # max_records=3 + 5 record → oldest 2 evict
        t = UsageTracker(max_records=3)
        for i in range(5):
            t.record(_record(timestamp_ms=1_700_000_000_000 + i))
        assert t.size() == 3
        records = t.all_records()
        # 최신 3 record (timestamp 2, 3, 4) 유지
        assert records[0].timestamp_ms == 1_700_000_000_002
        assert records[-1].timestamp_ms == 1_700_000_000_004

    def test_zero_max_unlimited(self) -> None:
        # max_records=0 = 무제한 (테스트 fixture)
        t = UsageTracker(max_records=0)
        for i in range(150_001):
            t.record(_record(timestamp_ms=1_700_000_000_000 + i))
        assert t.size() == 150_001
