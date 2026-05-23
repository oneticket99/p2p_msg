# SPDX-License-Identifier: GPL-3.0-or-later
"""accepted 친구 chat room + 메시지 송수신 E2E — cycle 169.657 신설.

사용자 directive — "e2e 친구 추가 / 친구 수락 시 수락된 친구 채팅리스트에 노출되고
서로 대화 되는지 까지 가능?"

chain:
1. alice (user_id=42) → bob (user_id=99) DM room 생성 + alice owner
2. bob accept 후 room 안 peer 추가 (peer rooms_repo.get_peer)
3. alice POST /api/rooms/{room_id}/messages (text "hello bob") → MESSAGE_SEND audit
4. bob POST /api/rooms/{room_id}/messages (text "hi alice") → 양방향 verify
5. GET /api/rooms/{room_id}/messages → 2 message 누계 list

본 file = handler-level integration test (mock asyncmy + rooms_repo + messages_repo).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.messages_handlers import handle_list_room_messages, handle_post_message
from server.db.repositories.messages import MessageRow
from server.db.repositories.rooms import PeerRow, RoomRow


pytestmark = pytest.mark.integration


class _FakeRequest:
    """aiohttp Request 모방 — __getitem__ + json + read + match_info."""

    def __init__(self, method: str, path: str, app: web.Application, user_id: int, match_info: dict | None = None, body: dict | None = None) -> None:
        self.app = app
        self.method = method
        self.path = path
        self.headers = {"Authorization": "Bearer fake"}
        self.match_info = match_info or {}
        self.remote = "127.0.0.1"
        self._state = {"user_id": user_id}
        self._body = body
        self.query: dict[str, str] = {}
        self.rel_url = MagicMock()
        self.rel_url.query = self.query

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    async def read(self) -> bytes:
        return json.dumps(self._body or {}).encode("utf-8")

    async def json(self) -> dict:
        return self._body or {}


@pytest.fixture
def app_with_pool() -> web.Application:
    """aiohttp.Application + db_pool mock."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 200
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
    app = web.Application()
    app["db_pool"] = pool
    return app


def _make_active_room(room_id: int = 7, owner_id: int = 42) -> RoomRow:
    return RoomRow(
        id=room_id, room_code="ABCDEF", owner_id=owner_id, kind="dm",
        status="active", created_at=datetime(2026, 5, 25, 1, 0, 0), closed_at=None,
    )


def _make_peer(room_id: int = 7, user_id: int = 99) -> PeerRow:
    return PeerRow(
        id=300, room_id=room_id, user_id=user_id, role="member",
        joined_at=datetime(2026, 5, 25, 1, 5, 0), left_at=None,
    )


def _make_msg_row(msg_id: int, sender_id: int, body: str, room_id: int = 7) -> MessageRow:
    return MessageRow(
        id=msg_id, room_id=room_id, sender_id=sender_id, kind="text",
        body=body, file_id=None, created_at=datetime(2026, 5, 25, 1, 10, 0),
    )


class TestAcceptedFriendChatChain:
    """accepted 친구 DM room 안 양방향 메시지 송수신 chain."""

    @pytest.mark.asyncio
    async def test_alice_sends_message_to_bob(self, app_with_pool, monkeypatch) -> None:
        """alice (owner=42) POST /api/rooms/7/messages → 201 + MESSAGE_SEND."""

        room = _make_active_room()
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=room),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),  # 한글 주석 — owner 정합, peer 부재 OK
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.insert_message",
            AsyncMock(return_value=500),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(return_value=_make_msg_row(500, 42, "hello bob")),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers._fire_push_notification",
            AsyncMock(return_value=None),
        )

        req = _FakeRequest("POST", "/api/rooms/7/messages", app_with_pool,
                          user_id=42, match_info={"room_id": "7"},
                          body={"body": "hello bob", "kind": "text"})
        resp = await handle_post_message(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["ok"] is True
        assert data["message_id"] == 500

    @pytest.mark.asyncio
    async def test_bob_sends_message_to_alice(self, app_with_pool, monkeypatch) -> None:
        """bob (peer=99) POST /api/rooms/7/messages → 200 + MESSAGE_SEND."""

        room = _make_active_room()
        peer = _make_peer(user_id=99)
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=room),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=peer),  # 한글 주석 — bob 활성 peer
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.insert_message",
            AsyncMock(return_value=501),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.get_by_id",
            AsyncMock(return_value=_make_msg_row(501, 99, "hi alice")),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers._fire_push_notification",
            AsyncMock(return_value=None),
        )

        req = _FakeRequest("POST", "/api/rooms/7/messages", app_with_pool,
                          user_id=99, match_info={"room_id": "7"},
                          body={"body": "hi alice", "kind": "text"})
        resp = await handle_post_message(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["ok"] is True
        assert data["message_id"] == 501

    @pytest.mark.asyncio
    async def test_non_member_blocked_403(self, app_with_pool, monkeypatch) -> None:
        """non-friend (user_id=200) → forbidden_not_member 403."""

        room = _make_active_room(owner_id=42)
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=room),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )

        req = _FakeRequest("POST", "/api/rooms/7/messages", app_with_pool,
                          user_id=200, match_info={"room_id": "7"},
                          body={"body": "intruder", "kind": "text"})
        resp = await handle_post_message(req)
        assert resp.status == 403
        data = json.loads(resp.body)
        assert data["error"] == "forbidden_not_member"

    @pytest.mark.asyncio
    async def test_room_message_list_returns_both(self, app_with_pool, monkeypatch) -> None:
        """GET /api/rooms/7/messages → alice + bob 양방향 list."""

        room = _make_active_room()
        msg_alice = _make_msg_row(500, 42, "hello bob")
        msg_bob = _make_msg_row(501, 99, "hi alice")
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=room),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.list_by_room",
            AsyncMock(return_value=[msg_alice, msg_bob]),
        )
        monkeypatch.setattr(
            "server.api.messages_handlers.messages_repo.count_by_room",
            AsyncMock(return_value=2),
        )

        req = _FakeRequest("GET", "/api/rooms/7/messages", app_with_pool,
                          user_id=42, match_info={"room_id": "7"})
        resp = await handle_list_room_messages(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["count"] == 2
        bodies = [m["body"] for m in data["messages"]]
        assert "hello bob" in bodies
        assert "hi alice" in bodies
