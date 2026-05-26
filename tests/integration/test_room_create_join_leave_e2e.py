# SPDX-License-Identifier: GPL-3.0-or-later
"""room create/join/leave chain E2E — cycle 169.674 신설.

chain:
1. POST /api/rooms — create 201 group
2. POST /api/rooms — create 400 invalid kind
3. POST /api/rooms/{room_id}/join — 200 success
4. POST /api/rooms/{room_id}/join — 404 not found
5. POST /api/rooms/{room_id}/join — 409 room closed
6. POST /api/rooms/{room_id}/join — 409 already member
7. POST /api/rooms/{room_id}/leave — 200 success
8. POST /api/rooms/{room_id}/leave — 404 not member
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.rooms_handlers import (
    handle_create_room, handle_join_room, handle_leave_room,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        method: str,
        app: web.Application,
        *,
        user_id: int,
        room_id: int | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {"User-Agent": "pytest"}
        self.match_info = {"room_id": str(room_id)} if room_id is not None else {}
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


def _make_room(owner_id: int = 10, status: str = "active") -> MagicMock:
    r = MagicMock()
    r.owner_id = owner_id
    r.status = status
    return r


class TestRoomCreate:
    @pytest.mark.asyncio
    async def test_create_group_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_room",
            AsyncMock(return_value=77),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            AsyncMock(return_value=1),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )
        req = _FakeRequest("POST", app_with_pool, user_id=10, body={"kind": "group"})
        resp = await handle_create_room(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["id"] == 77
        assert data["kind"] == "group"
        assert data["owner_id"] == 10

    @pytest.mark.asyncio
    async def test_create_invalid_kind_400(self, app_with_pool) -> None:
        req = _FakeRequest("POST", app_with_pool, user_id=10,
                           body={"kind": "channel"})
        with pytest.raises(web.HTTPBadRequest, match="kind"):
            await handle_create_room(req)

    @pytest.mark.asyncio
    async def test_create_with_avatar_ref_and_name_201(
        self, app_with_pool, monkeypatch
    ) -> None:
        # 한글 주석 — cycle 169.852 M4: group/channel 서버 room 생성 시 name+avatar_ref
        # 영속 + 응답 반환. avatar_exists(sync 디스크 gate)는 실재 True 로 mock.
        captured = {}

        async def _insert_room(pool, **kwargs):
            captured.update(kwargs)
            return 91

        ref = "avatars/" + ("a" * 64) + ".png"
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_room", _insert_room
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            AsyncMock(return_value=1),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers._avatars_repo.avatar_exists",
            MagicMock(return_value=True),
        )
        req = _FakeRequest(
            "POST", app_with_pool, user_id=10,
            body={"kind": "group", "name": "내 그룹", "avatar_ref": ref},
        )
        resp = await handle_create_room(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["avatar_ref"] == ref
        assert data["name"] == "내 그룹"
        # insert_room 에 name/avatar_ref 전달 확인
        assert captured.get("name") == "내 그룹"
        assert captured.get("avatar_ref") == ref

    @pytest.mark.asyncio
    async def test_create_nonexistent_avatar_ref_400(
        self, app_with_pool, monkeypatch
    ) -> None:
        # 한글 주석 — avatar_ref 미실재(위조/삭제) → 400 (avatar_exists False)
        monkeypatch.setattr(
            "server.api.rooms_handlers._avatars_repo.avatar_exists",
            MagicMock(return_value=False),
        )
        req = _FakeRequest(
            "POST", app_with_pool, user_id=10,
            body={"kind": "group", "avatar_ref": "avatars/" + ("b" * 64) + ".png"},
        )
        with pytest.raises(web.HTTPBadRequest, match="avatar_ref 미실재"):
            await handle_create_room(req)


class TestRoomJoin:
    @pytest.mark.asyncio
    async def test_join_success_200(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            AsyncMock(return_value=88),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1)
        resp = await handle_join_room(req)
        assert resp.status == 200
        assert json.loads(resp.body)["peer_id"] == 88

    @pytest.mark.asyncio
    async def test_join_room_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=99)
        resp = await handle_join_room(req)
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_join_room_closed_409(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(status="closed")),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1)
        resp = await handle_join_room(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "room_closed"

    @pytest.mark.asyncio
    async def test_join_already_member_409(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=MagicMock()),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1)
        resp = await handle_join_room(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "already_member"


class TestRoomLeave:
    @pytest.mark.asyncio
    async def test_leave_success_200(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=1),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.log_activity", AsyncMock(return_value=None)
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1)
        resp = await handle_leave_room(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_leave_not_member_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=0),
        )
        req = _FakeRequest("POST", app_with_pool, user_id=20, room_id=1)
        resp = await handle_leave_room(req)
        assert resp.status == 404
