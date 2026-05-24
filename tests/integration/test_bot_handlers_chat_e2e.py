# SPDX-License-Identifier: GPL-3.0-or-later
"""bot_handlers chat chain E2E — cycle 169.730 신설.

chain:
1. 401 — user_id 부재
2. 401 — user_id bool edge
3. 429 — rate limit gate 차단
4. 400 — messages 배열 부재
5. 400 — messages 빈 list
6. 400 — messages 한도 초과
7. 200 — MockLLMProvider 성공
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from aiohttp import web

from app.bot.llm_proxy import MockLLMProvider, RateLimitGate
from server.api.bot_handlers import (
    APP_KEY_PROVIDER, APP_KEY_RATE_GATE, handle_bot_chat,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        user_id: Any = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "POST"
        self.headers = {}
        self.match_info = {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self.remote = "127.0.0.1"
        self._body = body

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


def _app(provider=None, gate=None) -> web.Application:
    app = web.Application()
    if provider is not None:
        app[APP_KEY_PROVIDER] = provider
    if gate is not None:
        app[APP_KEY_RATE_GATE] = gate
    return app


class TestAuthChain:
    @pytest.mark.asyncio
    async def test_no_user_id_401(self) -> None:
        req = _FakeRequest(_app(), user_id=None,
                           body={"messages": []})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_bool_user_id_401(self) -> None:
        # 한글 주석 — bool isinstance(int) edge case 차단
        req = _FakeRequest(_app(), user_id=True, body={"messages": []})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_bot_chat(req)


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_rate_limit_429(self) -> None:
        import time as _time

        gate = RateLimitGate(rate_per_minute=1)
        # 한글 주석 — 실 time.time() 기준 한도 소진 (handler 안 now_seconds=None → time.time())
        gate.allow(10, now_seconds=_time.time())
        app = _app(gate=gate)
        req = _FakeRequest(app, user_id=10,
                           body={"messages": [{"role": "user", "content": "hi", "timestamp_ms": 0}]})
        with pytest.raises(web.HTTPTooManyRequests):
            await handle_bot_chat(req)


class TestMessageValidation:
    @pytest.mark.asyncio
    async def test_messages_not_list_400(self) -> None:
        req = _FakeRequest(_app(), user_id=10, body={"messages": "notalist"})
        with pytest.raises(web.HTTPBadRequest, match="배열"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_empty_messages_400(self) -> None:
        req = _FakeRequest(_app(), user_id=10, body={"messages": []})
        with pytest.raises(web.HTTPBadRequest, match="빈 list"):
            await handle_bot_chat(req)

    @pytest.mark.asyncio
    async def test_messages_over_limit_400(self) -> None:
        # 한글 주석 — 33 message > _MAX_MESSAGES_PER_REQUEST(32)
        msgs = [
            {"role": "user", "content": "x", "timestamp_ms": 0}
            for _ in range(33)
        ]
        req = _FakeRequest(_app(), user_id=10, body={"messages": msgs})
        with pytest.raises(web.HTTPBadRequest, match="한도"):
            await handle_bot_chat(req)


class TestSuccessPath:
    @pytest.mark.asyncio
    async def test_mock_provider_success(self) -> None:
        app = _app(provider=MockLLMProvider())
        req = _FakeRequest(
            app, user_id=10,
            body={"messages": [
                {"role": "user", "content": "hello bot", "timestamp_ms": 0},
            ]},
        )
        resp = await handle_bot_chat(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        # 한글 주석 — MockLLMProvider echo [mock] prefix
        assert data["reply"]["role"] == "assistant"
        assert "[mock]" in data["reply"]["content"]
