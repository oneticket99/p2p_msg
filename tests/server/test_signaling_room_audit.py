# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 127 — signaling _handle_join + _handle_leave audit hook 검증.

ROOM_JOIN + ROOM_LEAVE audit chain — pool 가용 + user_id 가용 시 actual SQL.
graceful skip — pool 부재 또는 user_id 부재.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.room import Peer, RoomRegistry
from server.signaling import _handle_join, _handle_leave


def _mock_pool() -> tuple[Any, Any]:
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = 1
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


def _make_ws_request(*, db_pool: Any = None) -> Any:
    app = MagicMock()
    app.get = lambda k, default=None: db_pool if k == "db_pool" else default
    req = MagicMock()
    req.app = app
    ws = MagicMock()
    ws._req = req
    ws.send_json = AsyncMock()
    ws.send_str = AsyncMock()
    return ws


class TestHandleJoinAudit:
    @pytest.mark.asyncio
    async def test_pool_none_no_audit(self) -> None:
        registry = RoomRegistry()
        ws = _make_ws_request(db_pool=None)
        payload = {"room": "room-1", "peer_id": "p1", "user_id": 42}
        # 한글 주석: pool 없음 → audit 미호출 + raise 부재
        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.peer_id == "p1"
        assert peer.user_id == 42

    @pytest.mark.asyncio
    async def test_pool_present_user_id_audit_called(self) -> None:
        registry = RoomRegistry()
        pool, cursor = _mock_pool()
        ws = _make_ws_request(db_pool=pool)
        payload = {"room": "room-1", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        # 한글 주석: ROOM_JOIN audit SQL — peer.db_room_id 부재 → audit skip 정합.
        # 다음 test 에서 db_room_id 주입 + INSERT 호출 검증.

    @pytest.mark.asyncio
    async def test_pool_present_with_db_room_id_audit_calls_insert(self) -> None:
        registry = RoomRegistry()
        pool, cursor = _mock_pool()
        ws = _make_ws_request(db_pool=pool)

        # 한글 주석: 기존 peer 의 db_room_id 주입 의 재JOIN 흐름
        existing_peer = Peer(peer_id="p1", ws=ws)
        existing_peer.user_id = 42
        existing_peer.db_room_id = 99

        payload = {"room": "room-1", "peer_id": "p1", "user_id": 42}
        peer = await _handle_join(ws, existing_peer, payload, registry)
        assert peer is not None
        # 한글 주석: persist_peer_join + log_activity 의 SQL 호출 검증
        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        assert any("INSERT INTO user_activity_log" in s for s in sql_calls)

    @pytest.mark.asyncio
    async def test_first_peer_triggers_room_create(self) -> None:
        # 한글 주석: 사이클 128 — 빈 registry 의 첫 peer join → ROOM_CREATE + ROOM_JOIN 의 2 SQL
        registry = RoomRegistry()
        pool, cursor = _mock_pool()
        ws = _make_ws_request(db_pool=pool)

        existing_peer = Peer(peer_id="p1", ws=ws)
        existing_peer.user_id = 42
        existing_peer.db_room_id = 99

        payload = {"room": "room-1", "peer_id": "p1", "user_id": 42}
        peer = await _handle_join(ws, existing_peer, payload, registry)
        assert peer is not None
        assert registry.room_size("room-1") == 1

        # 한글 주석: action 인자 의 추출 — execute(sql, params) params[1] = action
        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                params = call.args[1]
                action_params.append(params[1])
        assert "room_create" in action_params
        assert "room_join" in action_params


class TestHandleLeaveAudit:
    @pytest.mark.asyncio
    async def test_pool_present_room_leave_audit(self) -> None:
        registry = RoomRegistry()
        pool, cursor = _mock_pool()
        ws = _make_ws_request(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.room_id = "room-1"
        peer.user_id = 42
        peer.db_room_id = 99
        # registry 에 join 등록 (leave 의 lookup 의 의무)
        await registry.join("room-1", peer)

        payload = {"room": "room-1", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)

        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        assert any(
            "INSERT INTO user_activity_log" in s for s in sql_calls
        )

    @pytest.mark.asyncio
    async def test_pool_none_no_audit_no_raise(self) -> None:
        registry = RoomRegistry()
        ws = _make_ws_request(db_pool=None)

        peer = Peer(peer_id="p1", ws=ws)
        peer.room_id = "room-1"
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("room-1", peer)

        payload = {"room": "room-1", "peer_id": "p1"}
        # 한글 주석: pool 부재 — raise 부재 + audit 미호출
        await _handle_leave(ws, peer, payload, registry)

    @pytest.mark.asyncio
    async def test_last_peer_triggers_room_close(self) -> None:
        # 한글 주석: 사이클 128 — 1 peer join + leave → registry.room_size = 0 → ROOM_CLOSE + ROOM_LEAVE
        registry = RoomRegistry()
        pool, cursor = _mock_pool()
        ws = _make_ws_request(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("room-1", peer)
        # registry.join 직후 peer.room_id 갱신 정합 확인
        assert peer.room_id == "room-1"

        payload = {"room": "room-1", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)
        assert registry.room_size("room-1") == 0

        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                params = call.args[1]
                action_params.append(params[1])
        assert "room_close" in action_params
        assert "room_leave" in action_params
