# SPDX-License-Identifier: GPL-3.0-or-later
"""CustomerServiceConfig + truncate_history + helper unit test — cycle 169.702 신설."""

from __future__ import annotations

import pytest


class TestCustomerServiceConfig:
    def test_default_construct(self) -> None:
        from app.bot.customer_service_bot import default_customer_service_config

        c = default_customer_service_config()
        assert c.bot_user_id >= 1_000_000
        assert c.display_name == "Toonation 고객센터"
        assert c.max_history_turns == 5
        assert c.rate_limit_per_minute == 20
        assert c.rag_top_k == 3
        assert c.scan_jailbreak is False

    def test_bot_user_id_below_prefix_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="bot_user_id"):
            CustomerServiceConfig(bot_user_id=10, display_name="X")

    def test_empty_display_name_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="display_name"):
            CustomerServiceConfig(bot_user_id=1_000_001, display_name="")

    def test_empty_system_prompt_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="system_prompt"):
            CustomerServiceConfig(
                bot_user_id=1_000_001, display_name="X", system_prompt="",
            )

    def test_zero_max_history_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="max_history_turns"):
            CustomerServiceConfig(
                bot_user_id=1_000_001, display_name="X", max_history_turns=0,
            )

    def test_zero_rate_limit_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="rate_limit_per_minute"):
            CustomerServiceConfig(
                bot_user_id=1_000_001, display_name="X",
                rate_limit_per_minute=0,
            )

    def test_zero_rag_top_k_raises(self) -> None:
        from app.bot.customer_service_bot import CustomerServiceConfig

        with pytest.raises(ValueError, match="rag_top_k"):
            CustomerServiceConfig(
                bot_user_id=1_000_001, display_name="X", rag_top_k=0,
            )


class TestTruncateHistory:
    def test_under_cap_returns_all(self) -> None:
        from app.bot.customer_service_bot import truncate_history
        from app.bot.llm_proxy import BotMessage

        history = [BotMessage(role="user", content=f"msg{i}", timestamp_ms=i) for i in range(4)]
        result = truncate_history(history, max_turns=5)
        assert len(result) == 4

    def test_over_cap_keeps_recent(self) -> None:
        from app.bot.customer_service_bot import truncate_history
        from app.bot.llm_proxy import BotMessage

        # 한글 주석 — 20 msg + max_turns=5 → 10 cap, 최근 10
        history = [BotMessage(role="user", content=f"msg{i}", timestamp_ms=i) for i in range(20)]
        result = truncate_history(history, max_turns=5)
        assert len(result) == 10
        assert result[0].content == "msg10"

    def test_zero_max_turns_raises(self) -> None:
        from app.bot.customer_service_bot import truncate_history

        with pytest.raises(ValueError, match="max_turns"):
            truncate_history([], max_turns=0)


class TestToonationDispatchMatcher:
    def test_korean_keyword_match(self) -> None:
        from app.bot.customer_service_bot import _matches_toonation_dispatch

        assert _matches_toonation_dispatch("오늘 후원 통계 알려줘") is True

    def test_english_keyword_match(self) -> None:
        from app.bot.customer_service_bot import _matches_toonation_dispatch

        assert _matches_toonation_dispatch("show me the donation list") is True

    def test_no_match(self) -> None:
        from app.bot.customer_service_bot import _matches_toonation_dispatch

        assert _matches_toonation_dispatch("hello world") is False

    def test_empty_no_match(self) -> None:
        from app.bot.customer_service_bot import _matches_toonation_dispatch

        assert _matches_toonation_dispatch("") is False
