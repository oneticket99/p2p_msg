# SPDX-License-Identifier: GPL-3.0-or-later
"""friends list/pending/search chain E2E — cycle 169.684 신설.

chain:
1. GET /api/friends — list_by_user → count=2 + friends payload
2. GET /api/friends/pending — list_pending → count=1 + pending payload
3. GET /api/friends/search — keyword <2 자 → 400
4. GET /api/friends/search — keyword OK + limit cap 50
5. GET /api/friends/search — 자기 PK 제외 filter
6. GET /api/friends/search — limit non-int → 400
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.friends_handlers import (
    handle_list_friends, handle_list_pending, handle_search_user,
)
from server.db.repositories.friends import FriendWithProfile


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        user_id: int,
        query: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "GET"
        self.headers = {}
        self.match_info = {}
        self._state = {"user_id": user_id}
        self.query = query or {}
        self.remote = "127.0.0.1"

    def __getitem__(self, key: str) -> Any:
        return self._state[key]


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


def _make_friend(friend_id: int = 20, status: str = "accepted") -> FriendWithProfile:
    return FriendWithProfile(
        id=1, user_id=10, friend_user_id=friend_id, status=status,
        nickname=None,
        requested_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        accepted_at=datetime(2026, 5, 24, tzinfo=timezone.utc) if status == "accepted" else None,
        friend_username=f"user-{friend_id}",
        friend_email_verified=1,
    )


class TestListFriends:
    @pytest.mark.asyncio
    async def test_list_returns_count(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.list_by_user",
            AsyncMock(return_value=[_make_friend(20), _make_friend(30)]),
        )
        req = _FakeRequest(app_with_pool, user_id=10)
        resp = await handle_list_friends(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 2
        assert len(data["friends"]) == 2


class TestListPending:
    @pytest.mark.asyncio
    async def test_pending_returns_count(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.list_pending_requests",
            AsyncMock(return_value=[_make_friend(40, status="pending")]),
        )
        req = _FakeRequest(app_with_pool, user_id=10)
        resp = await handle_list_pending(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 1


class TestSearchUser:
    @pytest.mark.asyncio
    async def test_keyword_too_short_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10, query={"q": "a"})
        with pytest.raises(web.HTTPBadRequest, match="2자 이상"):
            await handle_search_user(req)

    @pytest.mark.asyncio
    async def test_invalid_limit_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10,
                           query={"q": "abc", "limit": "xyz"})
        with pytest.raises(web.HTTPBadRequest, match="limit"):
            await handle_search_user(req)

    @pytest.mark.asyncio
    async def test_self_pk_filtered(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — 자기 자신 결과 제외
        results = [
            {"id": 10, "username": "myself"},
            {"id": 20, "username": "other"},
        ]
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.search_users_by_username",
            AsyncMock(return_value=results),
        )
        req = _FakeRequest(app_with_pool, user_id=10, query={"q": "abc"})
        resp = await handle_search_user(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 1
        assert data["results"][0]["id"] == 20

    @pytest.mark.asyncio
    async def test_limit_capped_50(self, app_with_pool, monkeypatch) -> None:
        capture = {}

        async def _search(pool, *, keyword, limit):
            capture["limit"] = limit
            return []

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.search_users_by_username",
            _search,
        )
        req = _FakeRequest(app_with_pool, user_id=10,
                           query={"q": "abc", "limit": "999"})
        await handle_search_user(req)
        assert capture["limit"] == 50
