# SPDX-License-Identifier: GPL-3.0-or-later
"""read_handlers chain E2E — cycle 169.731 신설.

chain:
1. mark_read 401 / 400 room_id / 400 last_read / 503 / 200
2. unread_counts 401 / empty room_ids / 100 cap / count
3. last_read_batch 401 / cap / batch
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.read_handlers import (
    handle_last_read_batch, handle_mark_read, handle_unread_counts,
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
        self._body = body

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestMarkRead:
    @pytest.mark.asyncio
    async def test_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, match_info={"room_id": "1"},
                           body={"last_read_msg_id": 5})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_mark_read(req)

    @pytest.mark.asyncio
    async def test_invalid_room_id_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10,
                           match_info={"room_id": "abc"},
                           body={"last_read_msg_id": 5})
        with pytest.raises(web.HTTPBadRequest, match="room_id"):
            await handle_mark_read(req)

    @pytest.mark.asyncio
    async def test_invalid_last_read_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10,
                           match_info={"room_id": "1"},
                           body={"last_read_msg_id": -1})
        with pytest.raises(web.HTTPBadRequest, match="last_read"):
            await handle_mark_read(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, user_id=10, match_info={"room_id": "1"},
                           body={"last_read_msg_id": 5})
        resp = await handle_mark_read(req)
        assert resp.status == 503

    @pytest.mark.asyncio
    async def test_mark_read_success(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.read_handlers._rs_repo.upsert_last_read",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(app_with_pool, user_id=10,
                           match_info={"room_id": "1"},
                           body={"last_read_msg_id": 42})
        resp = await handle_mark_read(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["last_read_msg_id"] == 42


class TestUnreadCounts:
    @pytest.mark.asyncio
    async def test_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, method="GET")
        with pytest.raises(web.HTTPUnauthorized):
            await handle_unread_counts(req)

    @pytest.mark.asyncio
    async def test_empty_room_ids_returns_empty(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, method="GET", user_id=10,
                           query={"room_ids": ""})
        resp = await handle_unread_counts(req)
        assert json.loads(resp.body)["counts"] == {}

    @pytest.mark.asyncio
    async def test_over_100_cap_400(self, app_with_pool) -> None:
        ids = ",".join(str(i) for i in range(101))
        req = _FakeRequest(app_with_pool, method="GET", user_id=10,
                           query={"room_ids": ids})
        with pytest.raises(web.HTTPBadRequest, match="100"):
            await handle_unread_counts(req)

    @pytest.mark.asyncio
    async def test_count_returned(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.read_handlers._rs_repo.get_unread_counts",
            AsyncMock(return_value={1: 3, 2: 0}),
        )
        req = _FakeRequest(app_with_pool, method="GET", user_id=10,
                           query={"room_ids": "1,2"})
        resp = await handle_unread_counts(req)
        data = json.loads(resp.body)
        assert data["counts"]["1"] == 3


class TestLastReadBatch:
    @pytest.mark.asyncio
    async def test_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, method="GET")
        with pytest.raises(web.HTTPUnauthorized):
            await handle_last_read_batch(req)

    @pytest.mark.asyncio
    async def test_batch_returned(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.read_handlers._rs_repo.get_last_read_batch",
            AsyncMock(return_value={1: 50, 2: 30}),
        )
        req = _FakeRequest(app_with_pool, method="GET", user_id=10,
                           query={"room_ids": "1,2"})
        resp = await handle_last_read_batch(req)
        data = json.loads(resp.body)
        assert data["last_read"]["1"] == 50
