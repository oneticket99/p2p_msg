# SPDX-License-Identifier: GPL-3.0-or-later
"""``app.bot.anthropic_client`` 단위 테스트.

serialize_messages + parse_response + AnthropicClient validation + mock
transport 의 8 상태 + from_env 환경 변수.
"""

from __future__ import annotations

from typing import List, Tuple

import pytest

from app.bot.anthropic_client import (
    AnthropicAuthError,
    AnthropicClient,
    AnthropicError,
    AnthropicMalformedError,
    AnthropicRateLimitError,
    AnthropicServerError,
    from_env,
    parse_response,
    serialize_messages,
)
from app.bot.llm_proxy import BotMessage, BotRole


def _system(content: str) -> BotMessage:
    return BotMessage(role=BotRole.SYSTEM, content=content, timestamp_ms=0)


def _user(content: str) -> BotMessage:
    return BotMessage(role=BotRole.USER, content=content, timestamp_ms=0)


def _assistant(content: str) -> BotMessage:
    return BotMessage(role=BotRole.ASSISTANT, content=content, timestamp_ms=0)


class TestSerializeMessages:
    """``serialize_messages`` system 분리 + role 변환 검증."""

    def test_empty_chain(self) -> None:
        system_str, payload = serialize_messages([])
        assert system_str == ""
        assert payload == []

    def test_single_system_extracted(self) -> None:
        system_str, payload = serialize_messages([_system("sys"), _user("u1")])
        assert system_str == "sys"
        assert payload == [{"role": "user", "content": "u1"}]

    def test_multi_system_joined(self) -> None:
        system_str, _ = serialize_messages(
            [_system("a"), _user("u1"), _system("b")]
        )
        assert system_str == "a\n\nb"

    def test_user_assistant_order(self) -> None:
        _, payload = serialize_messages(
            [_user("u1"), _assistant("a1"), _user("u2")]
        )
        assert payload == [
            {"role": "user", "content": "u1"},
            {"role": "assistant", "content": "a1"},
            {"role": "user", "content": "u2"},
        ]

    def test_system_excluded_from_payload(self) -> None:
        _, payload = serialize_messages(
            [_system("sys"), _user("u1"), _assistant("a1")]
        )
        roles = [m["role"] for m in payload]
        assert "system" not in roles


class TestParseResponse:
    """``parse_response`` Anthropic 응답 schema 변환 + 오류 검증."""

    def test_happy_single_text_block(self) -> None:
        body = {
            "role": "assistant",
            "content": [{"type": "text", "text": "안녕하세요"}],
        }
        msg = parse_response(body)
        assert msg.role == BotRole.ASSISTANT
        assert msg.content == "안녕하세요"

    def test_multi_text_blocks_joined(self) -> None:
        body = {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "첫줄"},
                {"type": "text", "text": "둘째줄"},
            ],
        }
        msg = parse_response(body)
        assert msg.content == "첫줄\n둘째줄"

    def test_missing_content_raises(self) -> None:
        with pytest.raises(AnthropicMalformedError, match="content"):
            parse_response({"role": "assistant"})

    def test_role_not_assistant_raises(self) -> None:
        body = {
            "role": "user",
            "content": [{"type": "text", "text": "x"}],
        }
        with pytest.raises(AnthropicMalformedError, match="role"):
            parse_response(body)

    def test_text_block_missing_text_raises(self) -> None:
        body = {
            "role": "assistant",
            "content": [{"type": "text"}],
        }
        with pytest.raises(AnthropicMalformedError, match="text"):
            parse_response(body)

    def test_non_text_blocks_skipped(self) -> None:
        # tool_use 등 비-text block 은 skip + text block 만 반영
        body = {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "x"},
                {"type": "text", "text": "본문"},
            ],
        }
        msg = parse_response(body)
        assert msg.content == "본문"


class TestAnthropicClientValidation:
    """``AnthropicClient`` __post_init__ 검증."""

    def test_empty_api_key_rejected(self) -> None:
        with pytest.raises(AnthropicAuthError, match="api_key"):
            AnthropicClient(api_key="")

    def test_empty_model_rejected(self) -> None:
        with pytest.raises(ValueError, match="model"):
            AnthropicClient(api_key="sk-x", model="")

    def test_zero_max_tokens_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_tokens"):
            AnthropicClient(api_key="sk-x", max_tokens=0)

    def test_empty_base_url_rejected(self) -> None:
        with pytest.raises(ValueError, match="base_url"):
            AnthropicClient(api_key="sk-x", base_url="")

    def test_default_fields(self) -> None:
        client = AnthropicClient(api_key="sk-x")
        assert client.model == "claude-3-5-sonnet-latest"
        assert client.max_tokens == 1024
        assert client.base_url == "https://api.anthropic.com"


class TestBuildRequest:
    """``build_headers`` + ``build_body`` API 요청 직렬화 검증."""

    def test_headers_contain_required_fields(self) -> None:
        client = AnthropicClient(api_key="sk-test")
        headers = client.build_headers()
        assert headers["x-api-key"] == "sk-test"
        assert headers["anthropic-version"] == "2023-06-01"
        assert headers["content-type"] == "application/json"

    def test_body_model_and_max_tokens(self) -> None:
        client = AnthropicClient(api_key="sk-x", model="custom", max_tokens=512)
        body = client.build_body([_user("u1")])
        assert body["model"] == "custom"
        assert body["max_tokens"] == 512

    def test_body_system_field_present(self) -> None:
        client = AnthropicClient(api_key="sk-x")
        body = client.build_body([_system("sys"), _user("u1")])
        assert body["system"] == "sys"

    def test_body_system_field_absent_when_no_system(self) -> None:
        client = AnthropicClient(api_key="sk-x")
        body = client.build_body([_user("u1")])
        assert "system" not in body


class TestChatWithMockTransport:
    """``chat`` 의 status code → 예외 매핑 검증."""

    @staticmethod
    def _make_transport(status: int, body: dict):
        async def _transport(
            url: str, headers: dict, json_body: dict
        ) -> Tuple[int, dict]:
            return (status, body)

        return _transport

    @pytest.mark.asyncio
    async def test_empty_messages_rejected(self) -> None:
        client = AnthropicClient(api_key="sk-x")
        with pytest.raises(ValueError, match="messages"):
            await client.chat([])

    @pytest.mark.asyncio
    async def test_status_200_happy(self) -> None:
        transport = self._make_transport(
            200,
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "응답"}],
            },
        )
        client = AnthropicClient(api_key="sk-x", transport=transport)
        msg = await client.chat([_user("질문")])
        assert msg.role == BotRole.ASSISTANT
        assert msg.content == "응답"

    @pytest.mark.asyncio
    async def test_status_401_auth_error(self) -> None:
        transport = self._make_transport(401, {"error": "invalid api key"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicAuthError):
            await client.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_status_403_auth_error(self) -> None:
        transport = self._make_transport(403, {"error": "forbidden"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicAuthError):
            await client.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_status_429_rate_limit(self) -> None:
        transport = self._make_transport(429, {"error": "rate_limited"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicRateLimitError):
            await client.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_status_500_server_error(self) -> None:
        transport = self._make_transport(500, {"error": "internal"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicServerError):
            await client.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_status_503_server_error(self) -> None:
        transport = self._make_transport(503, {"error": "unavailable"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicServerError):
            await client.chat([_user("u")])

    @pytest.mark.asyncio
    async def test_status_400_generic_error(self) -> None:
        transport = self._make_transport(400, {"error": "bad_request"})
        client = AnthropicClient(api_key="sk-x", transport=transport)
        with pytest.raises(AnthropicError) as exc_info:
            await client.chat([_user("u")])
        # auth/rate/server subclass 가 아닌 base 매칭
        assert not isinstance(
            exc_info.value,
            (AnthropicAuthError, AnthropicRateLimitError, AnthropicServerError),
        )

    @pytest.mark.asyncio
    async def test_transport_receives_url_and_body(self) -> None:
        # transport 의 호출 시 URL + headers + body 의 정합 검증
        captured: List[Tuple[str, dict, dict]] = []

        async def _spy(
            url: str, headers: dict, body: dict
        ) -> Tuple[int, dict]:
            captured.append((url, headers, body))
            return (
                200,
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "ok"}],
                },
            )

        client = AnthropicClient(api_key="sk-spy", transport=_spy)
        await client.chat([_system("S"), _user("U")])
        assert len(captured) == 1
        url, headers, body = captured[0]
        assert url == "https://api.anthropic.com/v1/messages"
        assert headers["x-api-key"] == "sk-spy"
        assert body["system"] == "S"
        assert body["messages"] == [{"role": "user", "content": "U"}]


class TestRetryAndBackoff:
    """retry/backoff 정책 검증 — 429 + 5xx 재시도, 지수 backoff delay, 예외 매핑."""

    @staticmethod
    def _sequence_transport(responses: List[Tuple[int, dict]]):
        # 호출 순서 의 응답 list 의 sequential 반환
        idx = {"i": 0}

        async def _t(url: str, headers: dict, body: dict) -> Tuple[int, dict]:
            i = idx["i"]
            idx["i"] = i + 1
            return responses[i] if i < len(responses) else responses[-1]

        return _t

    @staticmethod
    def _sleep_recorder():
        # 호출 시점 delay 의 기록 + 실 대기 부재
        delays: List[float] = []

        async def _sleep(seconds: float) -> None:
            delays.append(seconds)

        return delays, _sleep

    def test_max_retries_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="max_retries"):
            AnthropicClient(api_key="sk-x", max_retries=-1)

    def test_backoff_base_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="backoff_base_seconds"):
            AnthropicClient(api_key="sk-x", backoff_base_seconds=0)

    @pytest.mark.asyncio
    async def test_429_retry_then_succeeds(self) -> None:
        # 429 → 429 → 200 의 chain — 재시도 후 성공
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport(
            [
                (429, {"error": "rate"}),
                (429, {"error": "rate"}),
                (
                    200,
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "ok"}],
                    },
                ),
            ]
        )
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=3,
            backoff_base_seconds=1.0,
            sleep_fn=sleep_fn,
        )
        msg = await client.chat([_user("u")])
        assert msg.content == "ok"
        # 2번 sleep — attempt 0 + attempt 1
        assert delays == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_5xx_retry_then_succeeds(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport(
            [
                (503, {"error": "x"}),
                (
                    200,
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": "ok"}],
                    },
                ),
            ]
        )
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=2,
            sleep_fn=sleep_fn,
        )
        msg = await client.chat([_user("u")])
        assert msg.content == "ok"
        assert delays == [1.0]

    @pytest.mark.asyncio
    async def test_429_exhausted_raises_rate_limit(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport([(429, {"e": "x"})])
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=2,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(AnthropicRateLimitError, match="소진"):
            await client.chat([_user("u")])
        # max_retries=2 → 2번 sleep (attempt 0 + 1) + 최종 3번째 시도 의 실패
        assert delays == [1.0, 2.0]

    @pytest.mark.asyncio
    async def test_5xx_exhausted_raises_server_error(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport([(500, {"e": "x"})])
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=1,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(AnthropicServerError, match="소진"):
            await client.chat([_user("u")])
        assert delays == [1.0]

    @pytest.mark.asyncio
    async def test_401_no_retry(self) -> None:
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport([(401, {"e": "x"})])
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=3,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(AnthropicAuthError):
            await client.chat([_user("u")])
        # 401 = 재시도 없음
        assert delays == []

    @pytest.mark.asyncio
    async def test_max_retries_zero_default(self) -> None:
        # max_retries=0 (default) + 429 = 즉시 RateLimitError
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport([(429, {"e": "x"})])
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(AnthropicRateLimitError):
            await client.chat([_user("u")])
        assert delays == []

    @pytest.mark.asyncio
    async def test_exponential_backoff_progression(self) -> None:
        # backoff_base_seconds=0.5 + max_retries=4 + 항상 503 → delay 4번
        delays, sleep_fn = self._sleep_recorder()
        transport = self._sequence_transport([(503, {"e": "x"})])
        client = AnthropicClient(
            api_key="sk-x",
            transport=transport,
            max_retries=4,
            backoff_base_seconds=0.5,
            sleep_fn=sleep_fn,
        )
        with pytest.raises(AnthropicServerError):
            await client.chat([_user("u")])
        # 0.5 * 2^0, 0.5 * 2^1, 0.5 * 2^2, 0.5 * 2^3 = 0.5, 1.0, 2.0, 4.0
        assert delays == [0.5, 1.0, 2.0, 4.0]


class TestFromEnv:
    """``from_env`` ANTHROPIC_API_KEY 의 클라이언트 생성."""

    def test_no_env_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(AnthropicAuthError, match="ANTHROPIC_API_KEY"):
            from_env()

    def test_env_present_creates_client(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

        async def _stub(
            url: str, headers: dict, body: dict
        ) -> Tuple[int, dict]:
            return (200, {})

        client = from_env(transport=_stub)
        assert isinstance(client, AnthropicClient)
        assert client.api_key == "sk-env"

    def test_transport_override(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env")

        async def _custom(
            url: str, headers: dict, body: dict
        ) -> Tuple[int, dict]:
            return (200, {})

        client = from_env(transport=_custom)
        assert client.transport is _custom
