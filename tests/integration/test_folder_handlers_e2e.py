# SPDX-License-Identifier: GPL-3.0-or-later
"""folder handlers chain E2E — cycle 169.694 신설.

chain:
1. create — 201 success + folder_pk
2. create — 401 user_id 부재
3. create — 400 folder_id/name 부재
4. create — 400 color_hex format 부재
5. list — folders payload
6. update — 200 success
7. update — 404 not found / no permission
8. update — 400 empty name
9. delete — 200 success
10. delete — 404 not found
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.folder_handlers import (
    handle_create_folder, handle_delete_folder, handle_list_folders,
    handle_update_folder,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        method: str = "POST",
        user_id: int | None = None,
        folder_id: str | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {}
        self.match_info = {"folder_id": folder_id} if folder_id else {}
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


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestCreateFolder:
    @pytest.mark.asyncio
    async def test_create_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.insert_folder_with_chats",
            AsyncMock(return_value=99),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"folder_id": "fav", "name": "Favorites",
                  "color_name": "blue", "color_hex": "#1A2B3C",
                  "included_chats": [], "excluded_chats": []},
        )
        resp = await handle_create_folder(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["folder_id"] == "fav"
        assert data["id"] == 99

    @pytest.mark.asyncio
    async def test_create_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, body={"folder_id": "f", "name": "N"})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_create_folder(req)

    @pytest.mark.asyncio
    async def test_create_missing_name_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10,
                           body={"folder_id": "fav", "name": "  "})
        with pytest.raises(web.HTTPBadRequest, match="name"):
            await handle_create_folder(req)

    @pytest.mark.asyncio
    async def test_create_invalid_color_hex_400(self, app_with_pool) -> None:
        # 한글 주석 — #RRGGBB 형식 부재 차단
        req = _FakeRequest(app_with_pool, user_id=10,
                           body={"folder_id": "fav", "name": "N",
                                 "color_hex": "FF0000"})
        with pytest.raises(web.HTTPBadRequest, match="color_hex"):
            await handle_create_folder(req)


class TestListFolders:
    @pytest.mark.asyncio
    async def test_list_returns_payload(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — SimpleNamespace = JSON 직렬화 차단 부재 (MagicMock 회피)
        from types import SimpleNamespace

        row = SimpleNamespace(
            folder_id="fav", name="Favorites", color_name="blue",
            color_hex="#1A2B3C", chat_count=2, id=1,
        )
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.list_folders",
            AsyncMock(return_value=[row]),
        )
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.list_folder_chats",
            AsyncMock(return_value={"included_chats": [], "excluded_chats": []}),
        )
        req = _FakeRequest(app_with_pool, method="GET", user_id=10)
        resp = await handle_list_folders(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert len(data["folders"]) == 1
        assert data["folders"][0]["folder_id"] == "fav"

    @pytest.mark.asyncio
    async def test_list_no_auth_401(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, method="GET")
        with pytest.raises(web.HTTPUnauthorized):
            await handle_list_folders(req)


class TestUpdateFolder:
    @pytest.mark.asyncio
    async def test_update_200(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.update_folder_with_chats",
            AsyncMock(return_value=True),
        )
        req = _FakeRequest(
            app_with_pool, method="PATCH", user_id=10, folder_id="fav",
            body={"name": "Updated"},
        )
        resp = await handle_update_folder(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_update_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.update_folder_with_chats",
            AsyncMock(return_value=False),
        )
        req = _FakeRequest(
            app_with_pool, method="PATCH", user_id=10, folder_id="ghost",
            body={"name": "X"},
        )
        with pytest.raises(web.HTTPNotFound):
            await handle_update_folder(req)

    @pytest.mark.asyncio
    async def test_update_empty_name_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="PATCH", user_id=10, folder_id="fav",
            body={"name": "   "},
        )
        with pytest.raises(web.HTTPBadRequest, match="name"):
            await handle_update_folder(req)


class TestDeleteFolder:
    @pytest.mark.asyncio
    async def test_delete_200(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.delete_folder",
            AsyncMock(return_value=True),
        )
        req = _FakeRequest(
            app_with_pool, method="DELETE", user_id=10, folder_id="fav",
        )
        resp = await handle_delete_folder(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_delete_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.folder_handlers.folder_repo.delete_folder",
            AsyncMock(return_value=False),
        )
        req = _FakeRequest(
            app_with_pool, method="DELETE", user_id=10, folder_id="ghost",
        )
        with pytest.raises(web.HTTPNotFound):
            await handle_delete_folder(req)
