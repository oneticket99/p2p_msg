# SPDX-License-Identifier: GPL-3.0-or-later
"""llm_proxy BotMessage + MockLLMProvider + RateLimitGate + select_llm_provider unit — cycle 169.703 신설."""

from __future__ import annotations

import time

import pytest


class TestBotMessage:
    def test_valid_construct(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole

        m = BotMessage(role=BotRole.USER, content="hello", timestamp_ms=1000)
        assert m.role == BotRole.USER
        assert m.content == "hello"

    def test_empty_content_raises(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole

        with pytest.raises(ValueError, match="content"):
            BotMessage(role=BotRole.USER, content="", timestamp_ms=1000)

    def test_negative_timestamp_raises(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole

        with pytest.raises(ValueError, match="timestamp_ms"):
            BotMessage(role=BotRole.USER, content="x", timestamp_ms=-1)

    def test_oversize_content_raises(self) -> None:
        # 한글 주석 — 16KB 초과 차단
        from app.bot.llm_proxy import BotMessage, BotRole

        with pytest.raises(ValueError, match="content"):
            BotMessage(role=BotRole.USER, content="x" * (17 * 1024),
                       timestamp_ms=1)


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_echo_with_mock_prefix(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole, MockLLMProvider

        msgs = [BotMessage(role=BotRole.USER, content="hello", timestamp_ms=1)]
        p = MockLLMProvider()
        reply = await p.chat(msgs)
        assert reply.role == BotRole.ASSISTANT
        assert reply.content == "[mock] hello"

    @pytest.mark.asyncio
    async def test_empty_messages_raises(self) -> None:
        from app.bot.llm_proxy import MockLLMProvider

        with pytest.raises(ValueError, match="messages"):
            await MockLLMProvider().chat([])

    @pytest.mark.asyncio
    async def test_no_user_message_raises(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole, MockLLMProvider

        msgs = [BotMessage(role=BotRole.SYSTEM, content="sys", timestamp_ms=1)]
        with pytest.raises(ValueError, match="user role"):
            await MockLLMProvider().chat(msgs)

    def test_is_available_true(self) -> None:
        from app.bot.llm_proxy import MockLLMProvider

        assert MockLLMProvider.is_available() is True


class TestRateLimitGate:
    def test_default_rate_20(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate()
        assert g.rate_per_minute == 20

    def test_invalid_rate_raises(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        with pytest.raises(ValueError, match="rate_per_minute"):
            RateLimitGate(rate_per_minute=0)

    def test_allow_under_limit(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate(rate_per_minute=3)
        assert g.allow(user_id=10, now_seconds=100.0) is True
        assert g.allow(user_id=10, now_seconds=101.0) is True
        assert g.allow(user_id=10, now_seconds=102.0) is True

    def test_reject_at_limit(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate(rate_per_minute=2)
        g.allow(user_id=10, now_seconds=100.0)
        g.allow(user_id=10, now_seconds=101.0)
        # 한글 주석 — 3번째 = reject
        assert g.allow(user_id=10, now_seconds=102.0) is False

    def test_prune_stale_after_minute(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate(rate_per_minute=2)
        g.allow(user_id=10, now_seconds=100.0)
        # 한글 주석 — 1분+1초 경과 → cutoff = 161 → 100 stale
        assert g.allow(user_id=10, now_seconds=161.0) is True
        assert g.remaining(user_id=10, now_seconds=161.0) == 1

    def test_invalid_user_id_raises(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate()
        with pytest.raises(ValueError, match="user_id"):
            g.allow(user_id=0)

    def test_remaining_full_when_empty(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate(rate_per_minute=5)
        assert g.remaining(user_id=10) == 5

    def test_prune_stale_evicts_keys(self) -> None:
        from app.bot.llm_proxy import RateLimitGate

        g = RateLimitGate(rate_per_minute=2)
        g.allow(user_id=10, now_seconds=100.0)
        g.allow(user_id=20, now_seconds=100.0)
        # 한글 주석 — 200초 경과 → 모든 100 stale → 2 key evict
        evicted = g.prune_stale(now_seconds=200.0)
        assert evicted == 2


class TestSelectLLMProvider:
    def test_explicit_mock(self) -> None:
        from app.bot.llm_proxy import MockLLMProvider, select_llm_provider

        assert select_llm_provider("mock") is MockLLMProvider

    def test_unknown_raises(self) -> None:
        from app.bot.llm_proxy import select_llm_provider

        with pytest.raises(ValueError):
            select_llm_provider("bogus-provider")

    def test_gemini_not_implemented(self) -> None:
        from app.bot.llm_proxy import select_llm_provider

        with pytest.raises(NotImplementedError):
            select_llm_provider("gemini")

    def test_auto_fallback_to_mock(self, monkeypatch) -> None:
        # 한글 주석 — Anthropic + OpenAI 부재 → mock fallback
        from app.bot.llm_proxy import (
            AnthropicProvider, MockLLMProvider, OpenAIProvider,
            select_llm_provider,
        )

        monkeypatch.setattr(AnthropicProvider, "is_available",
                            classmethod(lambda cls: False))
        monkeypatch.setattr(OpenAIProvider, "is_available",
                            classmethod(lambda cls: False))
        assert select_llm_provider() is MockLLMProvider
