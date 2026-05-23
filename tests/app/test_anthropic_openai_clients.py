# SPDX-License-Identifier: GPL-3.0-or-later
"""bot anthropic + openai serialize/parse + error hierarchy unit — cycle 169.718 신설."""

from __future__ import annotations

import pytest


class TestAnthropicSerialize:
    def test_system_separated(self) -> None:
        from app.bot.anthropic_client import serialize_messages
        from app.bot.llm_proxy import BotMessage, BotRole

        msgs = [
            BotMessage(role=BotRole.SYSTEM, content="be polite", timestamp_ms=1),
            BotMessage(role=BotRole.USER, content="hello", timestamp_ms=2),
            BotMessage(role=BotRole.ASSISTANT, content="hi", timestamp_ms=3),
        ]
        system_str, payload = serialize_messages(msgs)
        # 한글 주석 — system 분리 + payload 의 user/assistant 만
        assert system_str == "be polite"
        assert len(payload) == 2
        assert payload[0]["role"] == "user"
        assert payload[1]["role"] == "assistant"

    def test_multiple_system_joined(self) -> None:
        from app.bot.anthropic_client import serialize_messages
        from app.bot.llm_proxy import BotMessage, BotRole

        msgs = [
            BotMessage(role=BotRole.SYSTEM, content="rule1", timestamp_ms=1),
            BotMessage(role=BotRole.SYSTEM, content="rule2", timestamp_ms=2),
            BotMessage(role=BotRole.USER, content="hi", timestamp_ms=3),
        ]
        system_str, payload = serialize_messages(msgs)
        assert "rule1" in system_str
        assert "rule2" in system_str
        assert len(payload) == 1


class TestAnthropicParse:
    def test_valid_text_block(self) -> None:
        from app.bot.anthropic_client import parse_response
        from app.bot.llm_proxy import BotRole

        body = {
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello"}],
        }
        msg = parse_response(body)
        assert msg.role == BotRole.ASSISTANT
        assert msg.content == "Hello"

    def test_multiple_text_blocks_joined(self) -> None:
        from app.bot.anthropic_client import parse_response

        body = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Hi"},
                {"type": "text", "text": "there"},
            ],
        }
        msg = parse_response(body)
        assert "Hi" in msg.content
        assert "there" in msg.content

    def test_missing_content_raises(self) -> None:
        from app.bot.anthropic_client import AnthropicMalformedError, parse_response

        with pytest.raises(AnthropicMalformedError, match="content"):
            parse_response({"role": "assistant"})

    def test_wrong_role_raises(self) -> None:
        from app.bot.anthropic_client import AnthropicMalformedError, parse_response

        with pytest.raises(AnthropicMalformedError, match="assistant"):
            parse_response({
                "role": "user",
                "content": [{"type": "text", "text": "x"}],
            })

    def test_no_text_blocks_raises(self) -> None:
        # 한글 주석 — type=tool_use 만 — text 추출 빈 → malformed
        from app.bot.anthropic_client import AnthropicMalformedError, parse_response

        with pytest.raises(AnthropicMalformedError):
            parse_response({
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "x"}],
            })


class TestAnthropicErrorHierarchy:
    def test_4_subclasses(self) -> None:
        from app.bot.anthropic_client import (
            AnthropicAuthError, AnthropicError, AnthropicMalformedError,
            AnthropicRateLimitError, AnthropicServerError,
        )

        for cls in (AnthropicAuthError, AnthropicRateLimitError,
                    AnthropicServerError, AnthropicMalformedError):
            assert issubclass(cls, AnthropicError)


class TestOpenAISerialize:
    def test_3_role_mapping(self) -> None:
        from app.bot.llm_proxy import BotMessage, BotRole
        from app.bot.openai_client import serialize_messages

        msgs = [
            BotMessage(role=BotRole.SYSTEM, content="sys", timestamp_ms=1),
            BotMessage(role=BotRole.USER, content="usr", timestamp_ms=2),
            BotMessage(role=BotRole.ASSISTANT, content="ast", timestamp_ms=3),
        ]
        payload = serialize_messages(msgs)
        # 한글 주석 — OpenAI = system role retain (분리 부재)
        assert len(payload) == 3
        assert payload[0]["role"] == "system"
        assert payload[1]["role"] == "user"
        assert payload[2]["role"] == "assistant"


class TestOpenAIParse:
    def test_valid_choice(self) -> None:
        from app.bot.llm_proxy import BotRole
        from app.bot.openai_client import parse_response

        body = {
            "choices": [
                {"message": {"role": "assistant", "content": "hello"}},
            ],
        }
        msg = parse_response(body)
        assert msg.role == BotRole.ASSISTANT
        assert msg.content == "hello"

    def test_missing_choices_raises(self) -> None:
        from app.bot.openai_client import OpenAIMalformedError, parse_response

        with pytest.raises(OpenAIMalformedError, match="choices"):
            parse_response({})

    def test_missing_message_raises(self) -> None:
        from app.bot.openai_client import OpenAIMalformedError, parse_response

        with pytest.raises(OpenAIMalformedError, match="message"):
            parse_response({"choices": [{}]})

    def test_wrong_role_raises(self) -> None:
        from app.bot.openai_client import OpenAIMalformedError, parse_response

        with pytest.raises(OpenAIMalformedError, match="assistant"):
            parse_response({
                "choices": [{"message": {"role": "user", "content": "x"}}],
            })

    def test_empty_content_raises(self) -> None:
        from app.bot.openai_client import OpenAIMalformedError, parse_response

        with pytest.raises(OpenAIMalformedError, match="content"):
            parse_response({
                "choices": [{"message": {"role": "assistant", "content": ""}}],
            })


class TestOpenAIErrorHierarchy:
    def test_4_subclasses(self) -> None:
        from app.bot.openai_client import (
            OpenAIAuthError, OpenAIError, OpenAIMalformedError,
            OpenAIRateLimitError, OpenAIServerError,
        )

        for cls in (OpenAIAuthError, OpenAIRateLimitError,
                    OpenAIServerError, OpenAIMalformedError):
            assert issubclass(cls, OpenAIError)
