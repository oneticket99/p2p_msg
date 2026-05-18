# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.main.build_app`` integration test — Phase 3 사이클 76.

`build_app()` 의 route 등록 + Bot proxy endpoint 의 BOT_ENABLED=1 시 활성 +
APP_KEY_PROVIDER + APP_KEY_RATE_GATE 등록 + 비활성 시 /api/bot/chat 404.
"""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.bot.llm_proxy import MockLLMProvider
from server.api.bot_handlers import APP_KEY_PROVIDER, APP_KEY_RATE_GATE
from server.main import build_app


class TestBuildAppBotDisabled:
    """``BOT_ENABLED`` 환경 변수 부재 시 /api/bot/chat 라우트 미등록 검증."""

    @pytest.mark.asyncio
    async def test_no_bot_route_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BOT_ENABLED", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        # route iteration — /api/bot/chat 부재 검증
        paths = {
            getattr(route.resource, "canonical", "")
            for route in app.router.routes()
        }
        assert "/api/bot/chat" not in paths
        # provider + gate 의 등록 부재
        assert APP_KEY_PROVIDER not in app
        assert APP_KEY_RATE_GATE not in app


class TestBuildAppBotEnabled:
    """``BOT_ENABLED=1`` + ANTHROPIC_API_KEY 부재 시 MockLLMProvider 폴백 + 라우트 등록."""

    @pytest.mark.asyncio
    async def test_mock_provider_fallback(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        # provider + gate 등록 확인
        assert APP_KEY_PROVIDER in app
        assert APP_KEY_RATE_GATE in app
        # MockLLMProvider 폴백
        provider = app[APP_KEY_PROVIDER]
        assert isinstance(provider, MockLLMProvider)
        # route 등록 확인
        paths = {
            getattr(route.resource, "canonical", "")
            for route in app.router.routes()
        }
        assert "/api/bot/chat" in paths

    @pytest.mark.asyncio
    async def test_custom_rate_cap_honored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.setenv("BOT_RATE_PER_MINUTE", "5")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        gate = app[APP_KEY_RATE_GATE]
        # gate 의 rate_per_minute = 5
        assert gate.remaining(user_id=1) == 5


class TestEndpointWithTestClient:
    """aiohttp TestClient 의 POST /api/bot/chat 실 호출 의 end-to-end 검증."""

    @staticmethod
    async def _make_client(app: web.Application) -> TestClient:
        # 직접 TestServer + TestClient 의 인스턴스화 — pytest-aiohttp fixture 의존성 회피
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        return client

    @pytest.mark.asyncio
    async def test_unauthorized_without_bearer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        client = await self._make_client(app)
        try:
            resp = await client.post(
                "/api/bot/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "u", "timestamp_ms": 0}
                    ]
                },
            )
            # auth_middleware 의 Bearer 부재 → 401
            assert resp.status == 401
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_happy_path_with_bearer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        # session_store 의 token → user_id mapping 의 의 inject
        app["session_store"]["test-token-xyz"] = 42
        client = await self._make_client(app)
        try:
            resp = await client.post(
                "/api/bot/chat",
                headers={"Authorization": "Bearer test-token-xyz"},
                json={
                    "messages": [
                        {"role": "user", "content": "안녕", "timestamp_ms": 0}
                    ]
                },
            )
            assert resp.status == 200
            payload = await resp.json()
            assert payload["reply"]["role"] == "assistant"
            # MockLLMProvider 의 echo — "안녕" 의 echo 포함
            assert "안녕" in payload["reply"]["content"]
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_bot_disabled_returns_404(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("BOT_ENABLED", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        app = await build_app()
        app["session_store"]["test-token"] = 42
        client = await self._make_client(app)
        try:
            resp = await client.post(
                "/api/bot/chat",
                headers={"Authorization": "Bearer test-token"},
                json={
                    "messages": [
                        {"role": "user", "content": "u", "timestamp_ms": 0}
                    ]
                },
            )
            # 라우트 미등록 = 404
            assert resp.status == 404
        finally:
            await client.close()
