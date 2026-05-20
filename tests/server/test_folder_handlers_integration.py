# SPDX-License-Identifier: GPL-3.0-or-later
"""folder REST handler integration test (cycle 169.80 신설 — MED-3 회수)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import web

from server.api.folder_handlers import (
    handle_create_folder,
    handle_create_folder_invite,
    handle_delete_folder,
    handle_list_folders,
)


def _make_request(user_id=42, json_payload=None, match_info=None):
    """aiohttp Request mock + db_pool + user_id."""
    req = MagicMock()
    req.app = {"db_pool": MagicMock()}
    req.get = MagicMock(return_value=user_id)
    req.json = AsyncMock(return_value=json_payload or {})
    req.match_info = match_info or {}
    return req


class TestFolderHandlers:

    @pytest.mark.asyncio
    async def test_create_folder_401_without_user(self) -> None:
        req = _make_request(user_id=None)
        with pytest.raises(web.HTTPUnauthorized):
            await handle_create_folder(req)

    @pytest.mark.asyncio
    async def test_create_folder_400_missing_name(self) -> None:
        req = _make_request(json_payload={"folder_id": "abc12345"})
        with pytest.raises(web.HTTPBadRequest):
            await handle_create_folder(req)

    @pytest.mark.asyncio
    async def test_create_folder_400_invalid_color_hex(self) -> None:
        # cycle 169.79 MED-4 회수 — color_hex regex 검증
        req = _make_request(json_payload={
            "folder_id": "abc12345", "name": "X", "color_hex": "zzz",
        })
        with pytest.raises(web.HTTPBadRequest):
            await handle_create_folder(req)

    @pytest.mark.asyncio
    async def test_create_folder_201_aggregate_insert(self) -> None:
        req = _make_request(json_payload={
            "folder_id": "abc12345", "name": "Good", "color_hex": "#3b82f6",
            "included_chats": [{"kind": "room", "target_id": 1}],
        })
        with patch(
            "server.api.folder_handlers.folder_repo.insert_folder_with_chats",
            new=AsyncMock(return_value=99),
        ) as m_insert:
            resp = await handle_create_folder(req)
        assert resp.status == 201
        m_insert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_folders_401_without_user(self) -> None:
        req = _make_request(user_id=None)
        with pytest.raises(web.HTTPUnauthorized):
            await handle_list_folders(req)

    @pytest.mark.asyncio
    async def test_delete_folder_404_missing(self) -> None:
        req = _make_request(match_info={"folder_id": "noexist"})
        with patch(
            "server.api.folder_handlers.folder_repo.delete_folder",
            new=AsyncMock(return_value=False),
        ):
            with pytest.raises(web.HTTPNotFound):
                await handle_delete_folder(req)

    @pytest.mark.asyncio
    async def test_invite_404_missing_folder(self) -> None:
        # cycle 169.79 MED-1 회수 — fetch_by_folder_id_and_owner single SQL
        req = _make_request(match_info={"folder_id": "noexist"})
        with patch(
            "server.api.folder_handlers.folder_repo.fetch_by_folder_id_and_owner",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(web.HTTPNotFound):
                await handle_create_folder_invite(req)

    @pytest.mark.asyncio
    async def test_invite_201_with_url_env(self) -> None:
        req = _make_request(match_info={"folder_id": "abc12345"})
        folder_row = MagicMock(id=42)
        with patch(
            "server.api.folder_handlers.folder_repo.fetch_by_folder_id_and_owner",
            new=AsyncMock(return_value=folder_row),
        ), patch(
            "server.api.folder_handlers.folder_repo.create_invite",
            new=AsyncMock(return_value="a" * 32),
        ):
            resp = await handle_create_folder_invite(req)
        assert resp.status == 201
