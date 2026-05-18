# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.customer_service_bot`` 단위 테스트.

CustomerServiceConfig validation + default_system_prompt 의 5 영역 + history
trim cap + CustomerServiceBot 의 LLMProvider 호출 + rate limit 차단.
"""

from __future__ import annotations

from typing import List

import pytest

from app.bot.customer_service_bot import (
    CustomerServiceBot,
    CustomerServiceConfig,
    default_customer_service_config,
    default_system_prompt,
    truncate_history,
)
from app.bot.llm_proxy import BotMessage, BotRole, MockLLMProvider, RateLimitGate


def _user(content: str, ts: int = 1_000) -> BotMessage:
    return BotMessage(role=BotRole.USER, content=content, timestamp_ms=ts)


def _assistant(content: str, ts: int = 2_000) -> BotMessage:
    return BotMessage(role=BotRole.ASSISTANT, content=content, timestamp_ms=ts)


class TestDefaultSystemPrompt:
    """``default_system_prompt`` 5 영역 검증."""

    def test_returns_non_empty(self) -> None:
        prompt = default_system_prompt()
        assert prompt
        assert len(prompt) > 100

    def test_mentions_5_areas(self) -> None:
        prompt = default_system_prompt()
        assert "후원" in prompt
        assert "정산" in prompt
        assert "OBS" in prompt
        assert "사기 신고" in prompt
        assert "환불" in prompt

    def test_mentions_security_guard(self) -> None:
        prompt = default_system_prompt()
        assert "개인정보" in prompt
        assert "instruction override" in prompt

    def test_mentions_toonation_role(self) -> None:
        prompt = default_system_prompt()
        assert "Toonation" in prompt


class TestCustomerServiceConfigValidation:
    """``CustomerServiceConfig`` dataclass 검증."""

    def test_valid_default(self) -> None:
        config = default_customer_service_config()
        assert config.bot_user_id >= 1_000_000
        assert config.display_name == "Toonation 고객센터"
        assert config.max_history_turns == 5
        assert config.rate_limit_per_minute == 20

    def test_low_bot_user_id_rejected(self) -> None:
        with pytest.raises(ValueError, match="bot_user_id"):
            CustomerServiceConfig(
                bot_user_id=999_999,
                display_name="X",
                system_prompt="prompt",
            )

    def test_empty_display_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="display_name 빈 문자열 불가"):
            CustomerServiceConfig(
                bot_user_id=1_000_001,
                display_name="",
                system_prompt="prompt",
            )

    def test_empty_system_prompt_rejected(self) -> None:
        with pytest.raises(ValueError, match="system_prompt 빈 문자열 불가"):
            CustomerServiceConfig(
                bot_user_id=1_000_001,
                display_name="X",
                system_prompt="",
            )

    def test_zero_max_history_turns_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_history_turns 양수 의무"):
            CustomerServiceConfig(
                bot_user_id=1_000_001,
                display_name="X",
                system_prompt="p",
                max_history_turns=0,
            )

    def test_zero_rate_limit_rejected(self) -> None:
        with pytest.raises(ValueError, match="rate_limit_per_minute 양수 의무"):
            CustomerServiceConfig(
                bot_user_id=1_000_001,
                display_name="X",
                system_prompt="p",
                rate_limit_per_minute=0,
            )


class TestTruncateHistory:
    """``truncate_history`` cap 검증."""

    def test_empty_history(self) -> None:
        assert truncate_history([]) == []

    def test_under_cap_unchanged(self) -> None:
        history = [_user("a"), _assistant("b")]
        result = truncate_history(history, max_turns=5)
        assert result == history

    def test_at_cap_unchanged(self) -> None:
        # 5 turns = 10 messages
        history = [_user(f"u{i}") if i % 2 == 0 else _assistant(f"a{i}") for i in range(10)]
        result = truncate_history(history, max_turns=5)
        assert len(result) == 10

    def test_over_cap_trims_oldest(self) -> None:
        # 15 messages, max_turns=5 → keep 10 latest
        history = [_user(f"m{i}", ts=i) for i in range(15)]
        result = truncate_history(history, max_turns=5)
        assert len(result) == 10
        assert result[0].content == "m5"
        assert result[-1].content == "m14"

    def test_zero_max_turns_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_turns 양수 의무"):
            truncate_history([], max_turns=0)


class TestCustomerServiceBot:
    """``CustomerServiceBot.answer`` 검증."""

    @pytest.mark.asyncio
    async def test_basic_answer(self) -> None:
        config = default_customer_service_config()
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        reply = await bot.answer(user_id=42, user_message="후원 정산 주기?")
        assert reply.role == BotRole.ASSISTANT
        assert "[mock]" in reply.content
        assert "후원 정산 주기?" in reply.content

    @pytest.mark.asyncio
    async def test_zero_user_id_rejected(self) -> None:
        config = default_customer_service_config()
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        with pytest.raises(ValueError, match="user_id 양수 의무"):
            await bot.answer(user_id=0, user_message="x")

    @pytest.mark.asyncio
    async def test_empty_message_rejected(self) -> None:
        config = default_customer_service_config()
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        with pytest.raises(ValueError, match="user_message 빈 문자열 불가"):
            await bot.answer(user_id=42, user_message="")

    @pytest.mark.asyncio
    async def test_rate_limit_blocks(self) -> None:
        config = CustomerServiceConfig(
            bot_user_id=1_000_001,
            display_name="X",
            system_prompt="p",
            rate_limit_per_minute=2,
        )
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        await bot.answer(user_id=42, user_message="q1")
        await bot.answer(user_id=42, user_message="q2")
        with pytest.raises(ValueError, match="rate limit 초과"):
            await bot.answer(user_id=42, user_message="q3")

    @pytest.mark.asyncio
    async def test_history_passed_to_provider(self) -> None:
        config = default_customer_service_config()
        # provider 의 chat 호출 chain 검증 위 의 spy
        captured: List[List[BotMessage]] = []

        class SpyProvider:
            @classmethod
            def is_available(cls) -> bool:
                return True

            async def chat(self, messages: List[BotMessage]) -> BotMessage:
                captured.append(messages)
                return _assistant("reply")

        bot = CustomerServiceBot(config, provider=SpyProvider())
        history = [_user("prev_q"), _assistant("prev_a")]
        await bot.answer(user_id=42, user_message="next_q", history=history)
        # system + history (2) + new user = 4 messages
        assert len(captured) == 1
        chain = captured[0]
        assert chain[0].role == BotRole.SYSTEM
        assert chain[1].content == "prev_q"
        assert chain[2].content == "prev_a"
        assert chain[3].content == "next_q"

    @pytest.mark.asyncio
    async def test_history_trimmed_to_max_turns(self) -> None:
        config = CustomerServiceConfig(
            bot_user_id=1_000_001,
            display_name="X",
            system_prompt="p",
            max_history_turns=2,
        )
        captured: List[List[BotMessage]] = []

        class SpyProvider:
            @classmethod
            def is_available(cls) -> bool:
                return True

            async def chat(self, messages: List[BotMessage]) -> BotMessage:
                captured.append(messages)
                return _assistant("reply")

        bot = CustomerServiceBot(config, provider=SpyProvider())
        # 10 history messages (5 turns) → trim 의 4 messages (2 turns)
        history = [_user(f"m{i}", ts=i) for i in range(10)]
        await bot.answer(user_id=42, user_message="new", history=history)
        chain = captured[0]
        # system + 4 trimmed + 1 new = 6
        assert len(chain) == 6

    def test_remaining_calls(self) -> None:
        config = default_customer_service_config()
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        assert bot.remaining_calls(42) == 20

    def test_config_property(self) -> None:
        config = default_customer_service_config()
        bot = CustomerServiceBot(config, provider=MockLLMProvider())
        assert bot.config.display_name == "Toonation 고객센터"

    @pytest.mark.asyncio
    async def test_external_gate_injection(self) -> None:
        config = default_customer_service_config()
        gate = RateLimitGate(rate_per_minute=1)
        bot = CustomerServiceBot(config, provider=MockLLMProvider(), gate=gate)
        await bot.answer(user_id=42, user_message="q1")
        with pytest.raises(ValueError, match="rate limit 초과"):
            await bot.answer(user_id=42, user_message="q2")
