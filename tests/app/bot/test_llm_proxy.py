# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.llm_proxy`` 단위 테스트.

BotMessage 검증 + MockLLMProvider deterministic echo + AnthropicProvider
placeholder graceful + select_llm_provider factory + RateLimitGate token bucket.
"""

from __future__ import annotations

import os

import pytest

from app.bot.llm_proxy import (
    AnthropicProvider,
    BotMessage,
    BotRole,
    MockLLMProvider,
    RateLimitGate,
    select_llm_provider,
)


def _user_msg(content: str = "안녕", ts: int = 1_000) -> BotMessage:
    return BotMessage(role=BotRole.USER, content=content, timestamp_ms=ts)


def _system_msg(content: str = "투네이션 고객센터 봇") -> BotMessage:
    return BotMessage(role=BotRole.SYSTEM, content=content, timestamp_ms=0)


class TestBotMessageValidation:
    """``BotMessage`` dataclass 검증."""

    def test_valid_user(self) -> None:
        msg = _user_msg(content="hello", ts=100)
        assert msg.role == BotRole.USER
        assert msg.content == "hello"

    def test_valid_korean_content(self) -> None:
        msg = BotMessage(role=BotRole.USER, content="한글 메시지", timestamp_ms=0)
        assert msg.content == "한글 메시지"

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(ValueError, match="content 빈 문자열 불가"):
            BotMessage(role=BotRole.USER, content="", timestamp_ms=0)

    def test_oversized_content_rejected(self) -> None:
        big = "x" * 17_000  # > 16 KB
        with pytest.raises(ValueError, match="content 길이 초과"):
            BotMessage(role=BotRole.USER, content=big, timestamp_ms=0)

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timestamp_ms 음수 불가"):
            BotMessage(role=BotRole.USER, content="x", timestamp_ms=-1)


class TestMockLLMProvider:
    """``MockLLMProvider`` echo 검증."""

    def test_is_available_always_true(self) -> None:
        assert MockLLMProvider.is_available() is True

    @pytest.mark.asyncio
    async def test_echo_last_user(self) -> None:
        provider = MockLLMProvider()
        messages = [
            _system_msg(),
            _user_msg(content="투네이션 후원 정산 방법?"),
        ]
        reply = await provider.chat(messages)
        assert reply.role == BotRole.ASSISTANT
        assert "투네이션 후원 정산 방법?" in reply.content
        assert reply.content.startswith("[mock]")

    @pytest.mark.asyncio
    async def test_empty_messages_rejected(self) -> None:
        provider = MockLLMProvider()
        with pytest.raises(ValueError, match="messages 빈 list 불가"):
            await provider.chat([])

    @pytest.mark.asyncio
    async def test_no_user_message_rejected(self) -> None:
        provider = MockLLMProvider()
        with pytest.raises(ValueError, match="user role message 부재"):
            await provider.chat([_system_msg()])

    @pytest.mark.asyncio
    async def test_picks_last_user_in_chain(self) -> None:
        provider = MockLLMProvider()
        messages = [
            _user_msg(content="first", ts=1),
            BotMessage(role=BotRole.ASSISTANT, content="[mock] first", timestamp_ms=2),
            _user_msg(content="second", ts=3),
        ]
        reply = await provider.chat(messages)
        assert "second" in reply.content


class TestAnthropicProvider:
    """``AnthropicProvider`` placeholder 검증."""

    def test_is_available_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert AnthropicProvider.is_available() is False

    @pytest.mark.asyncio
    async def test_chat_raises_not_implemented(self) -> None:
        provider = AnthropicProvider()
        with pytest.raises(NotImplementedError, match="httpx \\+ Messages API binding"):
            await provider.chat([_user_msg()])


class TestSelectLLMProvider:
    """``select_llm_provider`` factory 검증."""

    def test_mock_explicit(self) -> None:
        cls = select_llm_provider("mock")
        assert cls is MockLLMProvider

    def test_anthropic_explicit(self) -> None:
        cls = select_llm_provider("anthropic")
        assert cls is AnthropicProvider

    def test_openai_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="openai provider"):
            select_llm_provider("openai")

    def test_gemini_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="gemini provider"):
            select_llm_provider("gemini")

    def test_unknown_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="unknown provider name"):
            select_llm_provider("xai-grok")

    def test_auto_detect_fallback_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        cls = select_llm_provider(None)
        assert cls is MockLLMProvider


class TestRateLimitGate:
    """``RateLimitGate`` token bucket 검증."""

    def test_zero_rate_rejected(self) -> None:
        with pytest.raises(ValueError, match="rate_per_minute 양수 의무"):
            RateLimitGate(rate_per_minute=0)

    def test_zero_user_id_rejected(self) -> None:
        gate = RateLimitGate()
        with pytest.raises(ValueError, match="user_id 양수 의무"):
            gate.allow(0, now_seconds=100.0)

    def test_under_limit_allows(self) -> None:
        gate = RateLimitGate(rate_per_minute=3)
        assert gate.allow(1, now_seconds=100.0) is True
        assert gate.allow(1, now_seconds=101.0) is True
        assert gate.allow(1, now_seconds=102.0) is True

    def test_over_limit_rejects(self) -> None:
        gate = RateLimitGate(rate_per_minute=2)
        assert gate.allow(1, now_seconds=100.0) is True
        assert gate.allow(1, now_seconds=101.0) is True
        assert gate.allow(1, now_seconds=102.0) is False

    def test_prune_after_minute(self) -> None:
        gate = RateLimitGate(rate_per_minute=2)
        gate.allow(1, now_seconds=100.0)
        gate.allow(1, now_seconds=101.0)
        # 60 초 + 1 ms 경과 = 이전 2건 prune + 신규 허용
        assert gate.allow(1, now_seconds=161.5) is True

    def test_per_user_independent(self) -> None:
        gate = RateLimitGate(rate_per_minute=1)
        assert gate.allow(1, now_seconds=100.0) is True
        # user 2 = 별개 bucket
        assert gate.allow(2, now_seconds=100.0) is True
        # user 1 의 cap 초과
        assert gate.allow(1, now_seconds=100.5) is False

    def test_remaining_count(self) -> None:
        gate = RateLimitGate(rate_per_minute=5)
        assert gate.remaining(1, now_seconds=100.0) == 5
        gate.allow(1, now_seconds=100.0)
        gate.allow(1, now_seconds=101.0)
        assert gate.remaining(1, now_seconds=102.0) == 3

    def test_remaining_after_prune(self) -> None:
        gate = RateLimitGate(rate_per_minute=3)
        gate.allow(1, now_seconds=100.0)
        gate.allow(1, now_seconds=101.0)
        # 60 초 후 = 모두 prune
        assert gate.remaining(1, now_seconds=162.0) == 3
