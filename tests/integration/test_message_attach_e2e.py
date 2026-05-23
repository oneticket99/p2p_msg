# SPDX-License-Identifier: GPL-3.0-or-later
"""file attach message chain E2E — cycle 169.669 신설.

사용자 directive — file/image 첨부 chat dispatch.

chain:
1. POST kind=file + file_id 32 hex → INSERT 201
2. POST kind=file + invalid file_id (short) → 400
3. POST kind=file + missing file_id → 400
4. POST kind=system + body → INSERT 201
5. POST kind=text + body 상한 초과 → 400
6. POST kind=invalid → 400
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.messages_handlers import handle_post_message
from server.db.repositories.messages import MessageRow


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        user_id: int,
        room_id: int,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "POST"
        self.headers = {"User-Agent": "pytest", "Authorization": "Bearer fake"}
        self.match_info = {"room_id": str(room_id)}
        self._state = {"user_id": user_id}
        self.remote = "127.0.0.1"
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


def _patch_common(monkeypatch, message_id: int = 50) -> AsyncMock:
    monkeypatch.setattr(
        "server.api.messages_handlers.rooms_repo.get_room_by_id",
        AsyncMock(return_value=_make_room()),
    )
    monkeypatch.setattr(
        "server.api.messages_handlers.rooms_repo.get_peer",
        AsyncMock(return_value=MagicMock()),
    )
    insert_mock = AsyncMock(return_value=message_id)
    monkeypatch.setattr(
        "server.api.messages_handlers.messages_repo.insert_message", insert_mock
    )
    row = MessageRow(
        id=message_id, room_id=1, sender_id=10, kind="file",
        body=None, file_id="a" * 32,
        created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        "server.api.messages_handlers.messages_repo.get_by_id",
        AsyncMock(return_value=row),
    )
    monkeypatch.setattr(
        "server.api.messages_handlers._audit_message", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        "server.api.messages_handlers._fire_push_notification",
        AsyncMock(return_value=None),
    )
    return insert_mock


class TestFileAttachMessage:
    @pytest.mark.asyncio
    async def test_file_kind_valid(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — kind=file + file_id 32 hex → 201
        insert_mock = _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "file", "file_id": "a" * 32},
        )
        resp = await handle_post_message(req)
        assert resp.status == 201
        assert insert_mock.await_args.kwargs["kind"] == "file"
        assert insert_mock.await_args.kwargs["body"] is None

    @pytest.mark.asyncio
    async def test_file_id_too_short_400(self, app_with_pool, monkeypatch) -> None:
        _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "file", "file_id": "abc"},
        )
        with pytest.raises(web.HTTPBadRequest, match="file_id"):
            await handle_post_message(req)

    @pytest.mark.asyncio
    async def test_file_missing_id_400(self, app_with_pool, monkeypatch) -> None:
        _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "file"},
        )
        with pytest.raises(web.HTTPBadRequest):
            await handle_post_message(req)


class TestSystemMessage:
    @pytest.mark.asyncio
    async def test_system_kind_valid(self, app_with_pool, monkeypatch) -> None:
        insert_mock = _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "system", "body": "joined"},
        )
        resp = await handle_post_message(req)
        assert resp.status == 201
        assert insert_mock.await_args.kwargs["kind"] == "system"


class TestInvalidKind:
    @pytest.mark.asyncio
    async def test_unknown_kind_400(self, app_with_pool, monkeypatch) -> None:
        _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "voice", "body": "x"},
        )
        with pytest.raises(web.HTTPBadRequest, match="kind"):
            await handle_post_message(req)

    @pytest.mark.asyncio
    async def test_body_too_long_400(self, app_with_pool, monkeypatch) -> None:
        from server.api.messages_handlers import _MAX_BODY_LEN
        _patch_common(monkeypatch)
        req = _FakeRequest(
            app_with_pool, user_id=10, room_id=1,
            body={"kind": "text", "body": "a" * (_MAX_BODY_LEN + 1)},
        )
        with pytest.raises(web.HTTPBadRequest, match="상한"):
            await handle_post_message(req)
