# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.api.bot_handlers`` 단위 테스트.

POST /api/bot/chat 의 schema validation + auth + rate limit + provider 호출 +
4 종 Anthropic 예외 → HTTP status 매핑.
"""

from __future__ import annotations

from typing import List, Optional
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from app.bot.anthropic_client import (
    AnthropicAuthError,
    AnthropicError,
    AnthropicMalformedError,
    AnthropicRateLimitError,
    AnthropicServerError,
)
from app.bot.llm_proxy import BotMessage, BotRole, RateLimitGate
from server.api.bot_handlers import (
    APP_KEY_PROVIDER,
    APP_KEY_RATE_GATE,
    _parse_messages,
    _parse_role,
    _reply_to_wire,
    handle_bot_chat,
)


def _make_request(
    *,
    user_id: Optional[int] = 7,
    body: Optional[dict] = None,
    provider: Optional[object] = None,
    rate_gate: Optional[RateLimitGate] = None,
    body_raises: bool = False,
) -> MagicMock:
    """aiohttp.web.Request mock — user_id + body + app context."""

    req = MagicMock()
    req.get = MagicMock(return_value=user_id)

    async def _json():
        if body_raises:
            raise ValueError("invalid json")
        return body if body is not None else {}

    req.json = _json
    app_data = {}
    if provider is not None:
        app_data[APP_KEY_PROVIDER] = provider
    if rate_gate is not None:
        app_data[APP_KEY_RATE_GATE] = rate_gate
    req.app = MagicMock()
    req.app.get = MagicMock(side_effect=lambda k, default=None: app_data.get(k, default))
    return req


class _MockProvider:
    """LLMProvider Protocol — chat 의 반환값 또는 raise 의 주입 가능."""

    def __init__(
        self,
        reply: Optional[BotMessage] = None,
        raise_exc: Optional[Exception] = None,
    ) -> None:
        self._reply = reply
        self._raise = raise_exc
        self.calls: List[List[BotMessage]] = []

    @classmethod
    def is_available(cls) -> bool:
        return True

    async def chat(self, messages: List[BotMessage]) -> BotMessage:
        self.calls.append(messages)
        if self._raise is not None:
            raise self._raise
        if self._reply is None:
            return BotMessage(
                role=BotRole.ASSISTANT, content="default", timestamp_ms=0
            )
        return self._reply


class TestParseRole:
    """``_parse_role`` role string → BotRole enum."""

    def test_user(self) -> None:
        assert _parse_role("user") == BotRole.USER

    def test_assistant(self) -> None:
        assert _parse_role("assistant") == BotRole.ASSISTANT

    def test_uppercase_accepted(self) -> None:
        assert _parse_role("USER") == BotRole.USER

    def test_system_rejected(self) -> None:
        # 보안 — 클라이언트 의 system role 주입 차단
        with pytest.raises(web.HTTPBadRequest, match="system role"):
            _parse_role("system")

    def test_unknown_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="unknown"):
            _parse_role("admin")


class TestParseMessages:
    """``_parse_messages`` 배열 schema 검증."""

    def test_non_list_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="배열"):
            _parse_messages({"role": "user"})

    def test_empty_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="빈"):
            _parse_messages([])

    def test_over_limit_rejected(self) -> None:
        items = [
            {"role": "user", "content": "x", "timestamp_ms": 0}
        ] * 33
        with pytest.raises(web.HTTPBadRequest, match="한도"):
            _parse_messages(items)

    def test_non_dict_item_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="dict"):
            _parse_messages(["x"])

    def test_missing_role_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="role"):
            _parse_messages([{"content": "x", "timestamp_ms": 0}])

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="content"):
            _parse_messages(
                [{"role": "user", "content": "", "timestamp_ms": 0}]
            )

    def test_negative_timestamp_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="timestamp"):
            _parse_messages(
                [{"role": "user", "content": "x", "timestamp_ms": -1}]
            )

    def test_oversize_content_rejected(self) -> None:
        big = "x" * (16 * 1024 + 1)
        with pytest.raises(web.HTTPBadRequest, match="16KB"):
            _parse_messages(
                [{"role": "user", "content": big, "timestamp_ms": 0}]
            )

    def test_system_role_rejected_with_index(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="messages\\[0\\]"):
            _parse_messages(
                [{"role": "system", "content": "x", "timestamp_ms": 0}]
            )

    def test_valid_user_assistant_chain(self) -> None:
        msgs = _parse_messages(
            [
                {"role": "user", "content": "안녕", "timestamp_ms": 100},
                {"role": "assistant", "content": "응답", "timestamp_ms": 200},
            ]
        )
        assert len(msgs) == 2
        assert msgs[0].role == BotRole.USER
        assert msgs[0].content == "안녕"
        assert msgs[1].role == BotRole.ASSISTANT


class TestReplyToWire:
    """``_reply_to_wire`` BotMessage → JSON dict."""

    def test_assistant_reply(self) -> None:
        msg = BotMessage(
            role=BotRole.ASSISTANT, content="ok", timestamp_ms=1234
        )
        wire = _reply_to_wire(msg)
        assert wire["role"] == "assistant"
        assert wire["content"] == "ok"
        assert wire["timestamp_ms"] == 1234


class TestHandleBotChat:
    """``handle_bot_chat`` endpoint 검증 — auth + rate + LLM + 예외 매핑."""

    @pytest.mark.asyncio
    async def test_missing_user_id_unauthorized(self) -> None:
        req = _make_request(user_id=None)
        with pytest.raises(web.HTTPUnauthorized):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_negative_user_id_unauthorized(self) -> None:
        req = _make_request(user_id=-1)
        with pytest.raises(web.HTTPUnauthorized):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_provider_missing_service_unavailable(self) -> None:
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=None,
        )
        with pytest.raises(web.HTTPServiceUnavailable, match="LLM provider"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_invalid_json_bad_request(self) -> None:
        req = _make_request(
            user_id=7, provider=_MockProvider(), body_raises=True
        )
        with pytest.raises(web.HTTPBadRequest, match="JSON"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_body_not_dict_bad_request(self) -> None:
        req = _make_request(user_id=7, body=["x"], provider=_MockProvider())
        with pytest.raises(web.HTTPBadRequest, match="object"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_rate_limit_blocks(self) -> None:
        gate = RateLimitGate(rate_per_minute=1)
        # 1회 소진
        gate.allow(7)
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=_MockProvider(),
            rate_gate=gate,
        )
        with pytest.raises(web.HTTPTooManyRequests):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_happy_path_returns_reply(self) -> None:
        reply = BotMessage(
            role=BotRole.ASSISTANT, content="응답입니다", timestamp_ms=999
        )
        provider = _MockProvider(reply=reply)
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "질문", "timestamp_ms": 100}
                ]
            },
            provider=provider,
        )
        resp = await handle_bot_chat(req)
        assert resp.status == 200
        import json

        payload = json.loads(resp.body.decode("utf-8"))
        assert payload["reply"]["role"] == "assistant"
        assert payload["reply"]["content"] == "응답입니다"
        assert payload["reply"]["timestamp_ms"] == 999

    @pytest.mark.asyncio
    async def test_auth_error_maps_to_500(self) -> None:
        # Anthropic auth 실패 — 서버 설정 문제 (클라이언트 노출 차단)
        provider = _MockProvider(raise_exc=AnthropicAuthError("bad key"))
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=provider,
        )
        with pytest.raises(web.HTTPInternalServerError, match="인증 실패"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_rate_limit_error_maps_to_503(self) -> None:
        provider = _MockProvider(
            raise_exc=AnthropicRateLimitError("upstream rate")
        )
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=provider,
        )
        with pytest.raises(web.HTTPServiceUnavailable, match="rate limit"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_server_error_maps_to_502(self) -> None:
        provider = _MockProvider(
            raise_exc=AnthropicServerError("upstream 500")
        )
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=provider,
        )
        with pytest.raises(web.HTTPBadGateway, match="upstream"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_malformed_error_maps_to_502(self) -> None:
        provider = _MockProvider(
            raise_exc=AnthropicMalformedError("bad schema")
        )
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=provider,
        )
        with pytest.raises(web.HTTPBadGateway, match="schema"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_generic_anthropic_error_maps_to_500(self) -> None:
        provider = _MockProvider(raise_exc=AnthropicError("unknown"))
        req = _make_request(
            user_id=7,
            body={
                "messages": [
                    {"role": "user", "content": "u", "timestamp_ms": 0}
                ]
            },
            provider=provider,
        )
        with pytest.raises(web.HTTPInternalServerError):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_bool_user_id_rejected(self) -> None:
        # bool 의 isinstance(int) is True — auth bypass 차단 (cycle 78 hardening)
        req = _make_request(user_id=True)
        with pytest.raises(web.HTTPUnauthorized, match="양수 int"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_float_user_id_rejected(self) -> None:
        # float 의 not isinstance(int) — 차단
        req = _make_request(user_id=3.14)
        with pytest.raises(web.HTTPUnauthorized, match="양수 int"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_string_user_id_rejected(self) -> None:
        req = _make_request(user_id="42")
        with pytest.raises(web.HTTPUnauthorized, match="양수 int"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_zero_user_id_rejected(self) -> None:
        req = _make_request(user_id=0)
        with pytest.raises(web.HTTPUnauthorized, match="양수 int"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_provider_receives_parsed_messages(self) -> None:
        provider = _MockProvider()
        req = _make_request(
            user_id=42,
            body={
                "messages": [
                    {"role": "user", "content": "u1", "timestamp_ms": 100},
                    {
                        "role": "assistant",
                        "content": "a1",
                        "timestamp_ms": 200,
                    },
                    {"role": "user", "content": "u2", "timestamp_ms": 300},
                ]
            },
            provider=provider,
        )
        await handle_bot_chat(req)
        assert len(provider.calls) == 1
        chain = provider.calls[0]
        assert len(chain) == 3
        assert chain[0].content == "u1"
        assert chain[1].role == BotRole.ASSISTANT
        assert chain[2].content == "u2"
