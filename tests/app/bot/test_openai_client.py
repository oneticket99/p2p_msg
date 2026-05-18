# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.openai_client`` 단위 테스트.

serialize_messages (system inline 유지) + parse_response (choices[0].message)
+ OpenAIClient validation + chat mock transport + 4 종 예외 + retry/backoff +
retry-after + jitter + network error retry + from_env.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pytest

from app.bot.llm_proxy import BotMessage, BotRole
from app.bot.openai_client import (
    OpenAIAuthError,
    OpenAIClient,
    OpenAIError,
    OpenAIMalformedError,
    OpenAIRateLimitError,
    OpenAIServerError,
    from_env,
    parse_response,
    serialize_messages,
)


def _system(content: str) -> BotMessage:
    return BotMessage(role=BotRole.SYSTEM, content=content, timestamp_ms=0)


def _user(content: str) -> BotMessage:
    return BotMessage(role=BotRole.USER, content=content, timestamp_ms=0)


def _assistant(content: str) -> BotMessage:
    return BotMessage(role=BotRole.ASSISTANT, content=content, timestamp_ms=0)


class TestSerializeMessages:
    """``serialize_messages`` system inline 유지 + role 변환."""

    def test_empty(self) -> None:
        assert serialize_messages([]) == []

    def test_system_inline_not_separated(self) -> None:
        # OpenAI vs Anthropic — system role 의 messages 배열 inline 유지
        result = serialize_messages([_system("sys"), _user("u1")])
        assert result == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
        ]

    def test_user_assistant_chain(self) -> None:
        result = serialize_messages(
            [_user("u1"), _assistant("a1"), _user("u2")]
        )
        assert result == [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]

    def test_multiple_system_all_inline(self) -> None:
        # Anthropic 과 달리 합본 부재 — 각각 inline
        result = serialize_messages(
            [_system("s1"), _user("u1"), _system("s2")]
        )
        roles = [m["role"] for m in result]
        assert roles == ["system", "user", "system"]


class TestParseResponse:
    """``parse_response`` OpenAI choices[0].message 변환."""

    def test_happy(self) -> None:
        body = {
            "id": "chatcmpl-x",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "응답"},
                }
            ],
        }
        msg = parse_response(body)
        assert msg.role == BotRole.ASSISTANT
        assert msg.content == "응답"

    def test_missing_choices_raises(self) -> None:
        with pytest.raises(OpenAIMalformedError, match="choices"):
            parse_response({"id": "x"})

    def test_empty_choices_raises(self) -> None:
        with pytest.raises(OpenAIMalformedError, match="choices"):
            parse_response({"choices": []})

    def test_missing_message_raises(self) -> None:
        with pytest.raises(OpenAIMalformedError, match="message"):
            parse_response({"choices": [{"index": 0}]})

    def test_role_not_assistant_raises(self) -> None:
        body = {
            "choices": [
                {"message": {"role": "user", "content": "x"}}
            ]
        }
        with pytest.raises(OpenAIMalformedError, match="role"):
            parse_response(body)

    def test_empty_content_raises(self) -> None:
        body = {
            "choices": [{"message": {"role": "assistant", "content": ""}}]
        }
        with pytest.raises(OpenAIMalformedError, match="content"):
            parse_response(body)


class TestClientValidation:
    """``OpenAIClient`` __post_init__ 검증."""

    def test_empty_api_key_rejected(self) -> None:
        with pytest.raises(OpenAIAuthError, match="api_key"):
            OpenAIClient(api_key="")

    def test_default_fields(self) -> None:
        c = OpenAIClient(api_key="sk-x")
        assert c.model == "gpt-4o-mini"
        assert c.max_tokens == 1024
        assert c.base_url == "https://api.openai.com"

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="model"):
            OpenAIClient(api_key="sk-x", model="")

    def test_zero_max_tokens_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_tokens"):
            OpenAIClient(api_key="sk-x", max_tokens=0)

    def test_negative_max_retries_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_retries"):
            OpenAIClient(api_key="sk-x", max_retries=-1)


class TestBuildRequest:
    """``build_headers`` + ``build_body``."""

    def test_headers_bearer(self) -> None:
        c = OpenAIClient(api_key="sk-test")
        h = c.build_headers()
        assert h["Authorization"] == "Bearer sk-test"
        assert h["content-type"] == "application/json"

    def test_body_model_and_messages(self) -> None:
        c = OpenAIClient(api_key="sk-x", model="custom", max_tokens=512)
        b = c.build_body([_system("sys"), _user("u1")])
        assert b["model"] == "custom"
        assert b["max_tokens"] == 512
        assert b["messages"] == [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "u1"},
        ]


class TestChatStatusMapping:
    """``chat`` status code → 예외 매핑."""

    @staticmethod
    def _transport(status: int, body: dict, headers: Optional[dict] = None):
        async def _t(url: str, h: dict, b: dict):
            return (status, headers or {}, body)

        return _t

    @pytest.mark.asyncio
    async def test_empty_messages_rejected(self) -> None:
        c = OpenAIClient(api_key="sk-x")
        with pytest.raises(ValueError, match="messages"):
            await c.chat([])

    @pytest.mark.asyncio
    async def test_200_happy(self) -> None:
        body = {
            "choices": [
                {"message": {"role": "assistant", "content": "응답"}}
            ]
        }
        c = OpenAIClient(api_key="sk-x", transport=self._transport(200, body))
        msg = await c.chat([_user("질문")])
        assert msg.content == "응답"

    @pytest.mark.asyncio
    async def test_401_auth_error(self) -> None:
        c = OpenAIClient(api_key="sk-x", transport=self._transport(401, {}))
        with pytest.raises(OpenAIAuthError):
            await c.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_429_rate_limit(self) -> None:
        c = OpenAIClient(api_key="sk-x", transport=self._transport(429, {}))
        with pytest.raises(OpenAIRateLimitError):
            await c.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_500_server_error(self) -> None:
        c = OpenAIClient(api_key="sk-x", transport=self._transport(500, {}))
        with pytest.raises(OpenAIServerError):
            await c.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_400_generic_error(self) -> None:
        c = OpenAIClient(api_key="sk-x", transport=self._transport(400, {}))
        with pytest.raises(OpenAIError) as ei:
            await c.chat([_user("u")])
        assert not isinstance(
            ei.value,
            (OpenAIAuthError, OpenAIRateLimitError, OpenAIServerError),
        )


class TestRetryAndBackoff:
    """retry/backoff + retry-after + jitter + network error."""

    @staticmethod
    def _sleep_recorder():
        delays: List[float] = []

        async def _sleep(seconds: float) -> None:
            delays.append(seconds)

        return delays, _sleep

    @staticmethod
    def _sequence(responses):
        idx = {"i": 0}

        async def _t(url, h, b):
            i = idx["i"]
            idx["i"] = i + 1
            return responses[i] if i < len(responses) else responses[-1]

        return _t

    @pytest.mark.asyncio
    async def test_429_retry_then_succeeds(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        ok_body = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}]
        }
        transport = self._sequence([(429, {}, {}), (200, {}, ok_body)])
        c = OpenAIClient(
            api_key="sk-x",
            transport=transport,
            max_retries=2,
            sleep_fn=sleep_fn,
        )
        msg = await c.chat([_user("u")])
        assert msg.content == "ok"
        assert delays == [1.0]

    @pytest.mark.asyncio
    async def test_retry_after_honored(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        ok_body = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}]
        }
        transport = self._sequence(
            [(429, {"retry-after": "5"}, {}), (200, {}, ok_body)]
        )
        c = OpenAIClient(
            api_key="sk-x",
            transport=transport,
            max_retries=2,
            sleep_fn=sleep_fn,
        )
        await c.chat([_user("u")])
        assert delays == [5.0]

    @pytest.mark.asyncio
    async def test_network_error_retry(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        ok_body = {
            "choices": [{"message": {"role": "assistant", "content": "ok"}}]
        }
        idx = {"i": 0}

        async def _t(url, h, b):
            i = idx["i"]
            idx["i"] = i + 1
            if i == 0:
                raise ConnectionError("refused")
            return (200, {}, ok_body)

        c = OpenAIClient(
            api_key="sk-x",
            transport=_t,
            max_retries=2,
            sleep_fn=sleep_fn,
        )
        msg = await c.chat([_user("u")])
        assert msg.content == "ok"
        assert delays == [1.0]

    @pytest.mark.asyncio
    async def test_429_exhausted(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence([(429, {}, {})])
        c = OpenAIClient(
            api_key="sk-x",
            transport=transport,
            max_retries=1,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(OpenAIRateLimitError, match="소진"):
            await c.chat([_user("u")])


class TestFromEnv:
    """``from_env`` OPENAI_API_KEY."""

    def test_no_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(OpenAIAuthError, match="OPENAI_API_KEY"):
            from_env()

    def test_env_present(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")

        async def _stub(url, h, b):
            return (200, {}, {})

        c = from_env(transport=_stub)
        assert isinstance(c, OpenAIClient)
        assert c.api_key == "sk-env"
