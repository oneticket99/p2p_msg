# SPDX-License-Identifier: GPL-3.0-or-later
"""friend block + delete chain E2E — cycle 169.666 신설.

사용자 directive — friend block + delete state machine verify.

chain:
1. POST /api/friends/{user_id}/block — 기존 관계 부재 → blocked INSERT
2. POST /api/friends/{user_id}/block — 기존 관계 → blocked UPDATE
3. POST /api/friends/{user_id}/block — 자기 차단 400
4. DELETE /api/friends/{user_id} — 양방향 removed UPDATE
5. DELETE /api/friends/{user_id} — 부재 시 404
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.friends_handlers import handle_block_friend, handle_remove_friend


pytestmark = pytest.mark.integration


class _FakeRequest:
    """aiohttp Request 모방 — friends_handlers 정합."""

    def __init__(
        self,
        method: str,
        app: web.Application,
        *,
        user_id: int,
        target_id: int,
        ua: str = "pytest",
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {"User-Agent": ua, "Authorization": "Bearer fake"}
        self.match_info = {"user_id": str(target_id)}
        self._state = {"user_id": user_id}
        self.remote = "127.0.0.1"

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestFriendBlock:
    @pytest.mark.asyncio
    async def test_block_inserts_when_no_existing(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — 기존 관계 부재 → blocked 신규 INSERT path
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=None),
        )
        insert_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend", insert_mock
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.log_activity", AsyncMock(return_value=None)
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, target_id=20)
        resp = await handle_block_friend(req)
        assert resp.status == 200
        assert insert_mock.await_count == 1
        kwargs = insert_mock.await_args.kwargs
        assert kwargs["status"] == "blocked"
        assert kwargs["friend_user_id"] == 20

    @pytest.mark.asyncio
    async def test_block_updates_when_existing(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — 기존 관계 존재 → status UPDATE path
        existing = MagicMock(status="accepted")
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=existing),
        )
        update_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status", update_mock
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.log_activity", AsyncMock(return_value=None)
        )

        req = _FakeRequest("POST", app_with_pool, user_id=10, target_id=20)
        resp = await handle_block_friend(req)
        assert resp.status == 200
        assert update_mock.await_count == 1
        assert update_mock.await_args.kwargs["new_status"] == "blocked"

    @pytest.mark.asyncio
    async def test_self_block_raises_400(self, app_with_pool) -> None:
        req = _FakeRequest("POST", app_with_pool, user_id=10, target_id=10)
        with pytest.raises(web.HTTPBadRequest):
            await handle_block_friend(req)


class TestFriendRemove:
    @pytest.mark.asyncio
    async def test_remove_updates_bidirectional(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — 양방향 removed UPDATE — alice→bob + bob→alice
        update_mock = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status", update_mock
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.log_activity", AsyncMock(return_value=None)
        )

        req = _FakeRequest("DELETE", app_with_pool, user_id=10, target_id=20)
        resp = await handle_remove_friend(req)
        assert resp.status == 200
        assert update_mock.await_count == 2
        first_kwargs = update_mock.await_args_list[0].kwargs
        second_kwargs = update_mock.await_args_list[1].kwargs
        assert first_kwargs["new_status"] == "removed"
        assert second_kwargs["new_status"] == "removed"
        assert first_kwargs["user_id"] == 10
        assert second_kwargs["user_id"] == 20

    @pytest.mark.asyncio
    async def test_remove_returns_404_when_absent(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — rowcount=0 → friend_not_found
        update_mock = AsyncMock(return_value=0)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status", update_mock
        )

        req = _FakeRequest("DELETE", app_with_pool, user_id=10, target_id=99)
        resp = await handle_remove_friend(req)
        assert resp.status == 404
