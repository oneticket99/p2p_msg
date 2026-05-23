# SPDX-License-Identifier: GPL-3.0-or-later
"""remote_handlers + bot_directory_handlers chain E2E — cycle 169.719 신설."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.bot_directory_handlers import (
    handle_create_bot, handle_get_bot, handle_list_public_bots,
)
from server.api.remote_handlers import (
    handle_remote_grant, handle_remote_request, handle_remote_revoke,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        method: str = "POST",
        user_id: int | None = None,
        match_info: dict | None = None,
        query: dict | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {}
        self.match_info = match_info or {}
        self.query = query or {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self.remote = "127.0.0.1"
        self.content_length = 1 if body is not None else 0
        self._body = body or {}

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestRemoteRequest:
    @pytest.mark.asyncio
    async def test_request_returns_pending(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.remote_handlers._audit_remote",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"target_user_id": 20, "pattern": "help"},
        )
        resp = await handle_remote_request(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["status"] == "pending"
        assert data["pattern"] == "help"

    @pytest.mark.asyncio
    async def test_grant_returns_granted(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.remote_handlers._audit_remote",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, user_id=20,
            body={"request_id": 99, "requester_user_id": 10},
        )
        resp = await handle_remote_grant(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["status"] == "granted"
        assert data["request_id"] == 99

    @pytest.mark.asyncio
    async def test_revoke_returns_revoked(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.remote_handlers._audit_remote",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"session_id": 42, "target_user_id": 20},
        )
        resp = await handle_remote_revoke(req)
        assert resp.status == 200
        assert json.loads(resp.body)["session_id"] == 42


class TestListPublicBots:
    @pytest.mark.asyncio
    async def test_pool_absent_empty(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, method="GET")
        resp = await handle_list_public_bots(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["bots"] == []
        assert data["count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_limit_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="GET", query={"limit": "abc"},
        )
        with pytest.raises(web.HTTPBadRequest, match="limit"):
            await handle_list_public_bots(req)

    @pytest.mark.asyncio
    async def test_returns_payload(self, app_with_pool, monkeypatch) -> None:
        from types import SimpleNamespace
        from datetime import datetime, timezone

        bot = SimpleNamespace(
            id=1, owner_user_id=10, name="HelperBot", username="helperbot",
            description="x", webhook_url=None, inline_enabled=False,
            is_public=True, is_active=True, status="active",
            created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        )
        monkeypatch.setattr(
            "server.api.bot_directory_handlers._bots_repo.list_public_bots",
            AsyncMock(return_value=[bot]),
        )
        req = _FakeRequest(app_with_pool, method="GET")
        resp = await handle_list_public_bots(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 1
        assert data["bots"][0]["username"] == "helperbot"


class TestGetBot:
    @pytest.mark.asyncio
    async def test_missing_username_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="GET", match_info={"username": ""},
        )
        with pytest.raises(web.HTTPBadRequest, match="username"):
            await handle_get_bot(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest(
            app, method="GET", match_info={"username": "helper"},
        )
        with pytest.raises(web.HTTPServiceUnavailable):
            await handle_get_bot(req)

    @pytest.mark.asyncio
    async def test_bot_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.bot_directory_handlers._bots_repo.get_bot_by_username",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, method="GET", match_info={"username": "ghost"},
        )
        with pytest.raises(web.HTTPNotFound):
            await handle_get_bot(req)


class TestCreateBot:
    @pytest.mark.asyncio
    async def test_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, body={"name": "B", "username": "bot"})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_create_bot(req)

    @pytest.mark.asyncio
    async def test_empty_name_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"name": "", "username": "helperbot"},
        )
        with pytest.raises(web.HTTPBadRequest, match="name"):
            await handle_create_bot(req)

    @pytest.mark.asyncio
    async def test_invalid_username_format_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"name": "B", "username": "1invalid"},
        )
        with pytest.raises(web.HTTPBadRequest, match="username"):
            await handle_create_bot(req)

    @pytest.mark.asyncio
    async def test_invalid_webhook_url_400(self, app_with_pool) -> None:
        # 한글 주석 — HTTPS strict 의무
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"name": "B", "username": "helperbot",
                  "webhook_url": "http://insecure.example.com/hook"},
        )
        with pytest.raises(web.HTTPBadRequest, match="webhook_url"):
            await handle_create_bot(req)
