# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.main.build_app`` integration test — Phase 3 사이클 76.

`build_app()` 의 route 등록 + Bot proxy endpoint 의 BOT_ENABLED=1 시 활성 +
APP_KEY_PROVIDER + APP_KEY_RATE_GATE 등록 + 비활성 시 /api/bot/chat 404.
"""

from __future__ import annotations

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from app.bot.llm_proxy import OpenAIProvider
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
    """``BOT_ENABLED=1`` + OpenAI strict policy 정합 (cycle 169.345 swap, cycle 169.611 fixture refactor)."""

    @pytest.mark.asyncio
    async def test_openai_key_absent_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석 — cycle 169.611: OpenAI strict — OPENAI_API_KEY 부재 시점 RuntimeError raise 정합.
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setenv("DB_ENABLED", "0")
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            await build_app()

    @pytest.mark.asyncio
    async def test_openai_provider_with_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석 — cycle 169.611: OPENAI_API_KEY 활성 시 OpenAIProvider 등록 + route 활성.
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        monkeypatch.setenv("DB_ENABLED", "0")
        if not OpenAIProvider.is_available():
            pytest.skip("httpx 미설치 — OpenAIProvider 비활성")
        app = await build_app()
        assert APP_KEY_PROVIDER in app
        assert APP_KEY_RATE_GATE in app
        provider = app[APP_KEY_PROVIDER]
        assert isinstance(provider, OpenAIProvider)
        paths = {
            getattr(route.resource, "canonical", "")
            for route in app.router.routes()
        }
        assert "/api/bot/chat" in paths

    @pytest.mark.asyncio
    async def test_custom_rate_cap_honored(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석 — cycle 169.611: BOT_RATE_PER_MINUTE env 의 gate cap propagate.
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.setenv("BOT_RATE_PER_MINUTE", "5")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        monkeypatch.setenv("DB_ENABLED", "0")
        if not OpenAIProvider.is_available():
            pytest.skip("httpx 미설치 — OpenAIProvider 비활성")
        app = await build_app()
        gate = app[APP_KEY_RATE_GATE]
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
        # 한글 주석 — cycle 169.611: OpenAI strict env inject + auth_middleware Bearer 부재 401.
        monkeypatch.setenv("BOT_ENABLED", "1")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-openai")
        monkeypatch.setenv("DB_ENABLED", "0")
        if not OpenAIProvider.is_available():
            pytest.skip("httpx 미설치 — OpenAIProvider 비활성")
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
            assert resp.status == 401
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_bot_disabled_returns_404(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # 한글 주석 — cycle 169.611: BOT_ENABLED 비활성 — 라우트 미등록 / 404 검증.
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
            assert resp.status == 404
        finally:
            await client.close()
