# SPDX-License-Identifier: GPL-3.0-or-later
"""push token register/unregister chain E2E — cycle 169.672 신설.

chain:
1. POST register — 401 user_id 부재
2. POST register — 400 fcm_token 빈
3. POST register — 400 platform ENUM 미흡
4. POST register — 503 pool 부재
5. POST register — 201 success
6. DELETE unregister — 401 user_id 부재
7. DELETE unregister — 400 token_id non-int
8. DELETE unregister — 503 pool 부재
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.push_handlers import handle_register_token, handle_unregister_token


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        method: str,
        app: web.Application,
        *,
        user_id: int | None = None,
        token_id: str | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {}
        self.match_info = {"token_id": token_id} if token_id is not None else {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self.remote = "127.0.0.1"
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


class TestRegisterToken:
    @pytest.mark.asyncio
    async def test_no_auth_401(self) -> None:
        app = web.Application()
        req = _FakeRequest("POST", app, body={"fcm_token": "x", "platform": "macos"})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_register_token(req)

    @pytest.mark.asyncio
    async def test_empty_token_400(self) -> None:
        app = web.Application()
        req = _FakeRequest("POST", app, user_id=10,
                           body={"fcm_token": "  ", "platform": "macos"})
        with pytest.raises(web.HTTPBadRequest, match="fcm_token"):
            await handle_register_token(req)

    @pytest.mark.asyncio
    async def test_invalid_platform_400(self) -> None:
        app = web.Application()
        req = _FakeRequest("POST", app, user_id=10,
                           body={"fcm_token": "abc", "platform": "bsd"})
        with pytest.raises(web.HTTPBadRequest, match="platform"):
            await handle_register_token(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        # 한글 주석 — db_pool 미설정 → 503 DB_DISABLED
        req = _FakeRequest("POST", app, user_id=10,
                           body={"fcm_token": "abc", "platform": "macos"})
        resp = await handle_register_token(req)
        assert resp.status == 503
        assert json.loads(resp.body)["error"] == "DB_DISABLED"

    @pytest.mark.asyncio
    async def test_register_success_201(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = MagicMock()
        monkeypatch.setattr(
            "server.api.push_handlers._dt_repo.upsert_token",
            AsyncMock(return_value=99),
        )
        req = _FakeRequest("POST", app, user_id=10,
                           body={"fcm_token": "abc", "platform": "macos",
                                 "device_label": "my-mac"})
        resp = await handle_register_token(req)
        assert resp.status == 201
        assert json.loads(resp.body)["token_id"] == 99


class TestUnregisterToken:
    @pytest.mark.asyncio
    async def test_no_auth_401(self) -> None:
        app = web.Application()
        req = _FakeRequest("DELETE", app, token_id="1")
        with pytest.raises(web.HTTPUnauthorized):
            await handle_unregister_token(req)

    @pytest.mark.asyncio
    async def test_invalid_token_id_400(self) -> None:
        app = web.Application()
        req = _FakeRequest("DELETE", app, user_id=10, token_id="abc")
        with pytest.raises(web.HTTPBadRequest, match="token_id"):
            await handle_unregister_token(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest("DELETE", app, user_id=10, token_id="42")
        resp = await handle_unregister_token(req)
        assert resp.status == 503
