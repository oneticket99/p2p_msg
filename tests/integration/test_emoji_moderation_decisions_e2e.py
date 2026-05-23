# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji_moderation_handlers approve/reject/dmca chain E2E — cycle 169.727 신설."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.emoji_moderation_handlers import (
    handle_approve, handle_dmca, handle_queue, handle_reject,
)


pytestmark = pytest.mark.integration

ADMIN_TOKEN = "admin-sekret-1234"


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        method: str = "POST",
        token: str | None = ADMIN_TOKEN,
        query: dict | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.match_info = {}
        self.query = query or {}
        self.remote = "127.0.0.1"
        self.content_length = 1 if body is not None else 0
        self._body = body or {}

    async def json(self) -> dict:
        return self._body


@pytest.fixture(autouse=True)
def admin_env(monkeypatch) -> None:
    monkeypatch.setenv("EMOJI_MODERATION_ADMIN_TOKEN", ADMIN_TOKEN)


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestAuthChain:
    @pytest.mark.asyncio
    async def test_admin_token_unset(self, monkeypatch, app_with_pool) -> None:
        monkeypatch.delenv("EMOJI_MODERATION_ADMIN_TOKEN", raising=False)
        req = _FakeRequest(app_with_pool, body={"pack_id": 1})
        resp = await handle_approve(req)
        assert resp.status == 401
        assert "unset" in json.loads(resp.body)["reason"]

    @pytest.mark.asyncio
    async def test_bearer_missing(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, token=None, body={"pack_id": 1})
        resp = await handle_approve(req)
        assert resp.status == 401
        assert "missing" in json.loads(resp.body)["reason"]

    @pytest.mark.asyncio
    async def test_token_mismatch(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, token="wrong", body={"pack_id": 1})
        resp = await handle_approve(req)
        assert resp.status == 401


class TestDecisions:
    @pytest.mark.asyncio
    async def test_approve_success(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_moderation_handlers.update_moderation_status",
            AsyncMock(return_value=1),
        )
        req = _FakeRequest(app_with_pool, body={"pack_id": 42})
        resp = await handle_approve(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["pack_id"] == 42
        assert data["moderation_status"] == "approved"

    @pytest.mark.asyncio
    async def test_reject_success(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_moderation_handlers.update_moderation_status",
            AsyncMock(return_value=1),
        )
        req = _FakeRequest(app_with_pool, body={"pack_id": 42})
        resp = await handle_reject(req)
        assert resp.status == 200
        assert json.loads(resp.body)["moderation_status"] == "rejected"

    @pytest.mark.asyncio
    async def test_dmca_success(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.emoji_moderation_handlers.update_moderation_status",
            AsyncMock(return_value=1),
        )
        req = _FakeRequest(app_with_pool, body={"pack_id": 42})
        resp = await handle_dmca(req)
        assert resp.status == 200
        assert json.loads(resp.body)["moderation_status"] == "dmca_takedown"

    @pytest.mark.asyncio
    async def test_invalid_pack_id_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, body={"pack_id": "abc"})
        resp = await handle_approve(req)
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_pool_absent_503(self, monkeypatch) -> None:
        app = web.Application()
        req = _FakeRequest(app, body={"pack_id": 42})
        resp = await handle_approve(req)
        assert resp.status == 503


class TestQueue:
    @pytest.mark.asyncio
    async def test_invalid_limit_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="GET", query={"limit": "xyz"},
        )
        resp = await handle_queue(req)
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_limit_cap_400(self, app_with_pool) -> None:
        # 한글 주석 — limit > 200 → 400
        req = _FakeRequest(
            app_with_pool, method="GET", query={"limit": "500"},
        )
        resp = await handle_queue(req)
        assert resp.status == 400

    @pytest.mark.asyncio
    async def test_negative_offset_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="GET", query={"offset": "-1"},
        )
        resp = await handle_queue(req)
        assert resp.status == 400
