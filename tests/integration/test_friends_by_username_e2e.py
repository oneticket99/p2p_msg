# SPDX-License-Identifier: GPL-3.0-or-later
"""friends/by-username chain E2E — cycle 169.696 신설.

chain:
1. add 401 — user_id 부재
2. add 400 — username <3 자
3. add 503 — pool 부재
4. add 404 — username 부재
5. add 400 — 자기 자신
6. add 201 — success + room_id
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.friends_by_username_handler import handle_add_friend_by_username


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        user_id: int | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "POST"
        self.headers = {}
        self.match_info = {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


def _build_pool() -> MagicMock:
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=("alice",))
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


class TestAddByUsername:
    @pytest.mark.asyncio
    async def test_no_auth_401(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, body={"username": "bob"})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_add_friend_by_username(req)

    @pytest.mark.asyncio
    async def test_short_username_400(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, user_id=10, body={"username": "ab"})
        with pytest.raises(web.HTTPBadRequest, match="3자"):
            await handle_add_friend_by_username(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, user_id=10, body={"username": "alice"})
        resp = await handle_add_friend_by_username(req)
        assert resp.status == 503

    @pytest.mark.asyncio
    async def test_username_not_found_404(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool()
        monkeypatch.setattr(
            "server.db.repositories.users.get_user_by_username",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(app, user_id=10, body={"username": "ghost"})
        with pytest.raises(web.HTTPNotFound):
            await handle_add_friend_by_username(req)

    @pytest.mark.asyncio
    async def test_self_add_400(self, monkeypatch) -> None:
        app = web.Application()
        app["db_pool"] = _build_pool()
        # 한글 주석 — target.id == user_id → 자기 자신 차단
        monkeypatch.setattr(
            "server.db.repositories.users.get_user_by_username",
            AsyncMock(return_value=SimpleNamespace(id=10)),
        )
        req = _FakeRequest(app, user_id=10, body={"username": "myself"})
        with pytest.raises(web.HTTPBadRequest, match="자기 자신"):
            await handle_add_friend_by_username(req)

    @pytest.mark.asyncio
    async def test_add_success_201(self, monkeypatch) -> None:
        # cycle 169.832 — 요청/승인 모델 전환: username 추가 = pending 요청 생성.
        # 기존 친구/요청 부재(get_friend=None) → status=pending 신규 INSERT.
        # 양방향 accepted + DM room 은 수락(handle_accept_friend) 시점으로 이동했으므로
        # 본 응답엔 room_id 부재 + status=pending.
        app = web.Application()
        app["db_pool"] = _build_pool()
        monkeypatch.setattr(
            "server.db.repositories.users.get_user_by_username",
            AsyncMock(return_value=SimpleNamespace(id=20)),
        )
        monkeypatch.setattr(
            "server.db.repositories.friends.get_friend",
            AsyncMock(return_value=None),
        )
        insert_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.db.repositories.friends.insert_friend", insert_mock,
        )
        req = _FakeRequest(app, user_id=10, body={"username": "alice"})
        resp = await handle_add_friend_by_username(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["friend_user_id"] == 20
        assert data["username"] == "alice"
        assert data["status"] == "pending"
        assert "room_id" not in data
        # 한글 주석 — pending status 로 INSERT 됐는지 검증 (instant accepted 아님)
        assert insert_mock.await_args.kwargs.get("status") == "pending"
