# SPDX-License-Identifier: GPL-3.0-or-later
"""message reactions add/remove chain E2E — cycle 169.671 신설.

chain:
1. POST add — 400 emoji 부재
2. POST add — 401 Authorization 부재
3. POST add — pool 부재 graceful 200
4. GET list — pool 부재 empty
5. DELETE remove — 401 Authorization 부재
6. DELETE remove — pool 부재 graceful 200
"""

from __future__ import annotations

import json
from typing import Any

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
        self.headers = {}
        self.match_info = {"message_id": message_id}
        if emoji is not None:
            self.match_info["emoji"] = emoji
        self._state = {"user_id": user_id} if user_id is not None else {}
        self.remote = "127.0.0.1"
        self._body = body or {}

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        return self._body


@pytest.fixture
def empty_app() -> web.Application:
    # 한글 주석 — pool 부재 graceful path 정합
    return web.Application()


class TestAddReaction:
    @pytest.mark.asyncio
    async def test_missing_emoji_400(self, empty_app) -> None:
        req = _FakeRequest("POST", empty_app, message_id="1", user_id=10,
                           body={"emoji": "   "})
        resp = await handle_add_reaction(req)
        assert resp.status == 400
        assert "emoji" in json.loads(resp.body)["error"]

    @pytest.mark.asyncio
    async def test_no_auth_401(self, empty_app) -> None:
        req = _FakeRequest("POST", empty_app, message_id="1",
                           body={"emoji": "👍"})
        resp = await handle_add_reaction(req)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_pool_absent_graceful_200(self, empty_app) -> None:
        # 한글 주석 — pool=None graceful → ok + total_count=1 mock
        req = _FakeRequest("POST", empty_app, message_id="42", user_id=10,
                           body={"emoji": "❤️"})
        resp = await handle_add_reaction(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["ok"] is True
        assert data["emoji"] == "❤️"
        assert data["total_count"] == 1


class TestListReactions:
    @pytest.mark.asyncio
    async def test_pool_absent_empty(self, empty_app) -> None:
        req = _FakeRequest("GET", empty_app, message_id="42")
        resp = await handle_list_reactions(req)
        assert resp.status == 200
        assert json.loads(resp.body)["reactions"] == []


class TestRemoveReaction:
    @pytest.mark.asyncio
    async def test_no_auth_401(self, empty_app) -> None:
        req = _FakeRequest("DELETE", empty_app, message_id="1", emoji="👍")
        resp = await handle_remove_reaction(req)
        assert resp.status == 401

    @pytest.mark.asyncio
    async def test_pool_absent_graceful_200(self, empty_app) -> None:
        req = _FakeRequest("DELETE", empty_app, message_id="1",
                           emoji="❤️", user_id=10)
        resp = await handle_remove_reaction(req)
        assert resp.status == 200
        assert json.loads(resp.body)["ok"] is True
