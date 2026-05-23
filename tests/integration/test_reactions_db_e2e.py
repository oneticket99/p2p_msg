# SPDX-License-Identifier: GPL-3.0-or-later
"""reactions DB pool 활성 chain E2E — cycle 169.680 신설.

chain:
1. POST add — pool 활성 → INSERT + COUNT → total_count=3
2. POST add — pool exception → 500
3. GET list — pool 활성 → reactions list
4. GET list — pool exception → empty graceful
5. DELETE remove — pool 활성 → DELETE 200
6. DELETE remove — pool exception → 500
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.reactions_handlers import (
    handle_add_reaction, handle_list_reactions, handle_remove_reaction,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        method: str,
        app: web.Application,
        *,
        message_id: str,
        emoji: str | None = None,
        user_id: int | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.match_info = {"message_id": message_id}
        if emoji is not None:
            self.match_info["emoji"] = emoji
        self._state = {"user_id": user_id} if user_id is not None else {}
        self._body = body or {}

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        return self._body


def _build_pool(*, count_result: int = 0, list_result: list | None = None,
                raise_on_acquire: bool = False) -> MagicMock:
    """aiohttp + asyncmy 패턴 pool mock — acquire + cursor 2-level async context."""

    pool = MagicMock()

    if raise_on_acquire:
        pool.acquire = MagicMock(side_effect=RuntimeError("pool dead"))
        return pool

    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=(count_result,))
    cur.fetchall = AsyncMock(return_value=list_result or [])

    cur_ctx = MagicMock()
    cur_ctx.__aenter__ = AsyncMock(return_value=cur)
    cur_ctx.__aexit__ = AsyncMock(return_value=None)

    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cur_ctx)
    conn.commit = AsyncMock(return_value=None)

    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)

    pool.acquire = MagicMock(return_value=conn_ctx)
    return pool


class TestAddReactionDB:
    @pytest.mark.asyncio
    async def test_add_returns_count_3(self) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool(count_result=3)
        req = _FakeRequest("POST", app, message_id="42", user_id=10,
                           body={"emoji": "👍"})
        resp = await handle_add_reaction(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["ok"] is True
        assert data["emoji"] == "👍"
        assert data["total_count"] == 3

    @pytest.mark.asyncio
    async def test_add_exception_500(self) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool(raise_on_acquire=True)
        req = _FakeRequest("POST", app, message_id="42", user_id=10,
                           body={"emoji": "👍"})
        resp = await handle_add_reaction(req)
        assert resp.status == 500


class TestListReactionsDB:
    @pytest.mark.asyncio
    async def test_list_returns_two(self) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool(list_result=[("👍", 3), ("❤️", 1)])
        req = _FakeRequest("GET", app, message_id="42")
        resp = await handle_list_reactions(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert len(data["reactions"]) == 2
        assert data["reactions"][0]["emoji"] == "👍"
        assert data["reactions"][0]["count"] == 3

    @pytest.mark.asyncio
    async def test_list_exception_empty(self) -> None:
        # 한글 주석 — exception graceful → empty reactions
        app = web.Application()
        app["db_pool"] = _build_pool(raise_on_acquire=True)
        req = _FakeRequest("GET", app, message_id="42")
        resp = await handle_list_reactions(req)
        assert resp.status == 200
        assert json.loads(resp.body)["reactions"] == []


class TestRemoveReactionDB:
    @pytest.mark.asyncio
    async def test_remove_success(self) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool()
        req = _FakeRequest("DELETE", app, message_id="42", emoji="👍", user_id=10)
        resp = await handle_remove_reaction(req)
        assert resp.status == 200
        assert json.loads(resp.body)["ok"] is True

    @pytest.mark.asyncio
    async def test_remove_exception_500(self) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool(raise_on_acquire=True)
        req = _FakeRequest("DELETE", app, message_id="42", emoji="👍", user_id=10)
        resp = await handle_remove_reaction(req)
        assert resp.status == 500
