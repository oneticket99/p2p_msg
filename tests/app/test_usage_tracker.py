# SPDX-License-Identifier: GPL-3.0-or-later
"""bot UsageTracker + UsageRecord + extract helpers unit — cycle 169.717 신설."""

from __future__ import annotations

import pytest


class TestUsageRecord:
    def test_valid_construct(self) -> None:
        from app.bot.usage_tracker import UsageRecord

        r = UsageRecord(user_id=10, provider="anthropic", model="claude-3",
                        input_tokens=100, output_tokens=50, timestamp_ms=1000)
        assert r.total_tokens == 150
        assert r.user_id == 10

    def test_zero_user_id_raises(self) -> None:
        from app.bot.usage_tracker import UsageRecord

        with pytest.raises(ValueError, match="user_id"):
            UsageRecord(user_id=0, provider="x", model="m",
                        input_tokens=0, output_tokens=0, timestamp_ms=0)

    def test_empty_provider_raises(self) -> None:
        from app.bot.usage_tracker import UsageRecord

        with pytest.raises(ValueError, match="provider"):
            UsageRecord(user_id=10, provider="", model="m",
                        input_tokens=0, output_tokens=0, timestamp_ms=0)

    def test_empty_model_raises(self) -> None:
        from app.bot.usage_tracker import UsageRecord

        with pytest.raises(ValueError, match="model"):
            UsageRecord(user_id=10, provider="x", model="",
                        input_tokens=0, output_tokens=0, timestamp_ms=0)

    def test_negative_input_tokens_raises(self) -> None:
        from app.bot.usage_tracker import UsageRecord

        with pytest.raises(ValueError, match="input_tokens"):
            UsageRecord(user_id=10, provider="x", model="m",
                        input_tokens=-1, output_tokens=0, timestamp_ms=0)


class TestUsageTracker:
    def test_record_increments_size(self) -> None:
        from app.bot.usage_tracker import UsageRecord, UsageTracker

        t = UsageTracker()
        t.record(UsageRecord(user_id=10, provider="x", model="m",
                              input_tokens=10, output_tokens=5, timestamp_ms=1))
        assert t.size() == 1

    def test_invalid_max_records_raises(self) -> None:
        from app.bot.usage_tracker import UsageTracker

        with pytest.raises(ValueError, match="max_records"):
            UsageTracker(max_records=-1)

    def test_ring_buffer_evicts_oldest(self) -> None:
        # 한글 주석 — maxlen 도달 → FIFO evict
        from app.bot.usage_tracker import UsageRecord, UsageTracker

        t = UsageTracker(max_records=2)
        for i in range(3):
            t.record(UsageRecord(user_id=10, provider="x", model="m",
                                  input_tokens=i, output_tokens=0, timestamp_ms=i))
        assert t.size() == 2
        # 한글 주석 — 0 evict → 1, 2 만 잔존
        all_records = t.all_records()
        assert all_records[0].input_tokens == 1
        assert all_records[1].input_tokens == 2

    def test_summarize_by_user(self) -> None:
        from app.bot.usage_tracker import UsageRecord, UsageTracker

        t = UsageTracker()
        t.record(UsageRecord(user_id=10, provider="x", model="m",
                              input_tokens=10, output_tokens=5, timestamp_ms=1))
        t.record(UsageRecord(user_id=10, provider="x", model="m",
                              input_tokens=20, output_tokens=10, timestamp_ms=2))
        t.record(UsageRecord(user_id=20, provider="x", model="m",
                              input_tokens=5, output_tokens=3, timestamp_ms=3))
        per = t.summarize_by_user()
        assert per[10].count == 2
        assert per[10].input_tokens == 30
        assert per[10].output_tokens == 15
        assert per[20].count == 1

    def test_summarize_by_provider(self) -> None:
        from app.bot.usage_tracker import UsageRecord, UsageTracker

        t = UsageTracker()
        t.record(UsageRecord(user_id=10, provider="anthropic", model="m",
                              input_tokens=10, output_tokens=5, timestamp_ms=1))
        t.record(UsageRecord(user_id=10, provider="openai", model="m",
                              input_tokens=20, output_tokens=10, timestamp_ms=2))
        per = t.summarize_by_provider()
        assert per["anthropic"].count == 1
        assert per["openai"].input_tokens == 20

    def test_summarize_by_period_invalid_raises(self) -> None:
        from app.bot.usage_tracker import UsageTracker

        with pytest.raises(ValueError, match="period"):
            UsageTracker().summarize_by_period("year")

    def test_total_empty(self) -> None:
        from app.bot.usage_tracker import UsageTracker

        s = UsageTracker().total()
        assert s.count == 0
        assert s.total_tokens == 0

    def test_clear_resets(self) -> None:
        from app.bot.usage_tracker import UsageRecord, UsageTracker

        t = UsageTracker()
        t.record(UsageRecord(user_id=10, provider="x", model="m",
                              input_tokens=10, output_tokens=5, timestamp_ms=1))
        t.clear()
        assert t.size() == 0


class TestExtractAnthropicUsage:
    def test_valid_body(self) -> None:
        from app.bot.usage_tracker import extract_anthropic_usage

        body = {"usage": {"input_tokens": 100, "output_tokens": 50}}
        assert extract_anthropic_usage(body) == (100, 50)

    def test_missing_usage_returns_zero(self) -> None:
        from app.bot.usage_tracker import extract_anthropic_usage

        assert extract_anthropic_usage({}) == (0, 0)

    def test_non_int_returns_zero(self) -> None:
        from app.bot.usage_tracker import extract_anthropic_usage

        body = {"usage": {"input_tokens": "abc", "output_tokens": None}}
        assert extract_anthropic_usage(body) == (0, 0)

    def test_negative_clamped_to_zero(self) -> None:
        # 한글 주석 — 음수 → max(0, x) clamp
        from app.bot.usage_tracker import extract_anthropic_usage

        body = {"usage": {"input_tokens": -5, "output_tokens": 10}}
        assert extract_anthropic_usage(body) == (0, 10)


class TestExtractOpenAIUsage:
    def test_valid_body(self) -> None:
        from app.bot.usage_tracker import extract_openai_usage

        body = {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
        result = extract_openai_usage(body)
        assert result[0] == 100
        assert result[1] == 50

    def test_missing_usage_returns_zero(self) -> None:
        from app.bot.usage_tracker import extract_openai_usage

        assert extract_openai_usage({}) == (0, 0)
