# SPDX-License-Identifier: GPL-3.0-or-later
"""Friends 친구추가 + 수락 chain E2E — cycle 169.656 신설.

사용자 directive — "e2e 친구추가 / 친구수락 포함가능?"

본 file = mock asyncmy pool + audit log capture + friends_handlers 3 endpoint chain:
1. handle_request_friend (alice → bob pending 발신)
2. handle_accept_friend (bob 의 alice 요청 수락 + reverse row 생성)
3. handle_list_friends (양방향 accepted 검증)

real signaling demo server / SMTP 의무 부재 → handler-level integration test pattern.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.friends_handlers import (
    handle_accept_friend,
    handle_list_friends,
    handle_request_friend,
)
from server.db.repositories.friends import FriendRow, FriendWithProfile


pytestmark = pytest.mark.integration


@pytest.fixture
def stateful_pool() -> Any:
    """mock asyncmy pool — friends repo state machine + insert/get/list/update chain."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 100
    cursor.rowcount = 1

    @asynccontextmanager
    async def cursor_cm() -> Any:
        yield cursor

    conn = MagicMock()
    conn.cursor = lambda: cursor_cm()
    conn.commit = AsyncMock()

    @asynccontextmanager
    async def acquire_cm() -> Any:
        yield conn

    pool = MagicMock()
    pool.acquire = lambda: acquire_cm()
    return pool, cursor


class _FakeRequest:
    """aiohttp Request 모방 minimal class — __getitem__ + app + read 의무."""

    def __init__(self, method: str, path: str, app: web.Application, user_id: int, body: dict | None = None) -> None:
        self.app = app
        self.method = method
        self.path = path
        self.headers = {"Authorization": "Bearer fake"}
        self.match_info: dict[str, str] = {}
        self.remote = "127.0.0.1"
        self._state = {"user_id": user_id}
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    async def read(self) -> bytes:
        return json.dumps(self._body or {}).encode("utf-8")

    async def json(self) -> dict:
        return self._body or {}


def _build_request(method: str, path: str, app: web.Application, user_id: int, body: dict | None = None) -> Any:
    """aiohttp Request mock — auth_middleware user_id + db_pool inject."""

    return _FakeRequest(method, path, app, user_id, body)


class TestFriendsChainAddAccept:
    """alice → bob 친구 추가 + 수락 chain E2E."""

    @pytest.mark.asyncio
    async def test_request_friend_returns_201_pending(self, stateful_pool, monkeypatch) -> None:
        """alice (user_id=42) → bob (user_id=99) 친구 요청 → 201 pending."""

        pool, cursor = stateful_pool
        app = web.Application()
        app["db_pool"] = pool

        # 한글 주석 — friends_repo mock chain (get_friend None + insert_friend lastrowid 100)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend",
            AsyncMock(return_value=100),
        )

        req = _build_request("POST", "/api/friends", app, user_id=42, body={"user_id": 99, "nickname": "bobby"})
        resp = await handle_request_friend(req)

        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["ok"] is True
        assert data["id"] == 100
        assert data["user_id"] == 42
        assert data["friend_user_id"] == 99
        assert data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_accept_friend_returns_ok(self, stateful_pool, monkeypatch) -> None:
        """bob (user_id=99) 의 alice 요청 수락 → ok + reverse row 생성."""

        pool, cursor = stateful_pool
        app = web.Application()
        app["db_pool"] = pool

        pending_row = FriendRow(
            id=100, user_id=42, friend_user_id=99, status="pending",
            nickname=None, requested_at=datetime(2026, 5, 25, 0, 30, 0), accepted_at=None,
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=pending_row),
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status",
            AsyncMock(return_value=1),
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend",
            AsyncMock(return_value=101),
        )

        req = _build_request("POST", "/api/friends/42/accept", app, user_id=99)
        req.match_info = {"user_id": "42"}
        resp = await handle_accept_friend(req)

        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["ok"] is True

    @pytest.mark.asyncio
    async def test_self_add_blocks_400(self, stateful_pool, monkeypatch) -> None:
        """자기 자신 친구 요청 → 400 bad request."""

        pool, _ = stateful_pool
        app = web.Application()
        app["db_pool"] = pool

        req = _build_request("POST", "/api/friends", app, user_id=42, body={"user_id": 42})
        with pytest.raises(web.HTTPBadRequest):
            await handle_request_friend(req)

    @pytest.mark.asyncio
    async def test_duplicate_pending_returns_409(self, stateful_pool, monkeypatch) -> None:
        """이미 pending 상태 → 409 already_exists."""

        pool, _ = stateful_pool
        app = web.Application()
        app["db_pool"] = pool

        existing_row = FriendRow(
            id=100, user_id=42, friend_user_id=99, status="pending",
            nickname=None, requested_at=datetime(2026, 5, 25, 0, 30, 0), accepted_at=None,
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=existing_row),
        )

        req = _build_request("POST", "/api/friends", app, user_id=42, body={"user_id": 99})
        resp = await handle_request_friend(req)

        assert resp.status == 409
        data = json.loads(resp.body)
        assert data["error"] == "already_exists"
        assert data["status"] == "pending"


class TestFriendsListAccepted:
    """list_friends — accepted 친구 list 반환 검증."""

    @pytest.mark.asyncio
    async def test_list_accepted_friends(self, stateful_pool, monkeypatch) -> None:
        """list_friends → accepted friends array + count."""

        pool, _ = stateful_pool
        app = web.Application()
        app["db_pool"] = pool

        bob_profile = FriendWithProfile(
            id=100, user_id=42, friend_user_id=99, status="accepted",
            nickname="bobby", requested_at=datetime(2026, 5, 25, 0, 30, 0),
            accepted_at=datetime(2026, 5, 25, 0, 35, 0),
            friend_username="bob", friend_email_verified=1,
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.list_by_user",
            AsyncMock(return_value=[bob_profile]),
        )

        req = _build_request("GET", "/api/friends", app, user_id=42)
        resp = await handle_list_friends(req)

        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 1
        assert data["friends"][0]["friend_username"] == "bob"
        assert data["friends"][0]["status"] == "accepted"
