# SPDX-License-Identifier: GPL-3.0-or-later
"""room invite + kick chain E2E — cycle 169.667 신설.

사용자 directive — group chat invite + kick state machine verify.

chain:
1. POST /api/rooms/{room_id}/invite — owner → member INSERT
2. POST invite — 자기 자신 400
3. POST invite — non-owner 403
4. POST invite — already_member 409
5. POST invite — room_not_found 404
6. POST /api/rooms/{room_id}/kick — owner → peer left_at UPDATE
7. POST kick — non-owner 403
8. POST kick — target_not_member 404
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.rooms_handlers import handle_invite_room, handle_kick_room


pytestmark = pytest.mark.integration


class _FakeRequest:
    """aiohttp Request 모방 — rooms_handlers 정합."""

    def __init__(
        self,
        method: str,
        app: web.Application,
        *,
        user_id: int,
        room_id: int,
        body: dict | None = None,
        ua: str = "pytest",
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {"User-Agent": ua, "Authorization": "Bearer fake"}
        self.match_info = {"room_id": str(room_id)}
        self._state = {"user_id": user_id}
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


def _make_room(room_id: int = 1, owner_id: int = 10, status: str = "active") -> MagicMock:
    room = MagicMock()
    room.id = room_id
    room.owner_id = owner_id
    room.status = status
    return room


class TestRoomInvite:
    @pytest.mark.asyncio
    async def test_invite_success(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — owner=10 invite user=20 → peer INSERT
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )
        insert_mock = AsyncMock(return_value=99)
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer", insert_mock
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=1, body={"user_id": 20})
        resp = await handle_invite_room(req)
        assert resp.status == 200
        assert insert_mock.await_count == 1
        assert insert_mock.await_args.kwargs["role"] == "member"

    @pytest.mark.asyncio
    async def test_invite_self_raises_400(self, app_with_pool) -> None:
        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=1, body={"user_id": 10})
        with pytest.raises(web.HTTPBadRequest):
            await handle_invite_room(req)

    @pytest.mark.asyncio
    async def test_invite_non_owner_403(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — owner=10 인 room 에 user=20 invite 시도 → forbidden
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=10)),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1, body={"user_id": 30})
        resp = await handle_invite_room(req)
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_invite_already_member_409(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=MagicMock()),
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=1, body={"user_id": 20})
        resp = await handle_invite_room(req)
        assert resp.status == 409

    @pytest.mark.asyncio
    async def test_invite_room_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=99, body={"user_id": 20})
        resp = await handle_invite_room(req)
        assert resp.status == 404


class TestRoomKick:
    @pytest.mark.asyncio
    async def test_kick_success(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — owner=10 kick user=20 → left_at UPDATE
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        kick_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left", kick_mock
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=1, body={"user_id": 20})
        resp = await handle_kick_room(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_kick_non_owner_403(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=10)),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1, body={"user_id": 30})
        resp = await handle_kick_room(req)
        assert resp.status == 403

    @pytest.mark.asyncio
    async def test_kick_target_not_member_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=0),
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, room_id=1, body={"user_id": 99})
        resp = await handle_kick_room(req)
        assert resp.status == 404
