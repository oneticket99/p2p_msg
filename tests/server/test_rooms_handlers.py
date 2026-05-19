# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 135 — rooms_handlers 의 6 endpoint + audit 검증.

REST endpoint × (정상 + 권한 부재 + edge case) 의 10 test.
ROOM_CREATE / ROOM_JOIN / ROOM_LEAVE 의 user_activity_log INSERT 정합 검증.

실 WebRTC / mesh 토폴로지 manager binding = 별개 cycle (skeleton 외).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.rooms_handlers import (
    handle_create_room,
    handle_get_room,
    handle_invite_room,
    handle_join_room,
    handle_kick_room,
    handle_leave_room,
    handle_list_rooms,
)
from server.db.repositories.rooms import PeerRow, RoomRow
from server.db.repositories.user_activity import ActivityAction


# ─── fixtures + builders ────────────────────────────────────────────────────


def _mock_pool() -> tuple[Any, Any]:
    """asyncmy pool + cursor mock 의 표준 builder — audit INSERT capture."""

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


def _make_room(
    *,
    room_id: int = 7,
    owner_id: int = 42,
    kind: str = "group",
    status: str = "active",
) -> RoomRow:
    return RoomRow(
        id=room_id,
        room_code="abcd1234",
        owner_id=owner_id,
        kind=kind,
        status=status,
        created_at=datetime(2026, 5, 19, 12, 0, 0),
        closed_at=None,
    )


def _make_peer(
    *,
    peer_id: int = 1,
    room_id: int = 7,
    user_id: int = 42,
    role: str = "owner",
) -> PeerRow:
    return PeerRow(
        id=peer_id,
        room_id=room_id,
        user_id=user_id,
        role=role,
        joined_at=datetime(2026, 5, 19, 12, 0, 0),
        left_at=None,
    )


def _make_request(
    *,
    db_pool: Any = None,
    user_id: int = 42,
    body: dict | None = None,
    match_info: dict | None = None,
    query: dict | None = None,
) -> MagicMock:
    """aiohttp.web.Request mock — middleware user_id 주입 + app[db_pool]."""

    req = MagicMock()
    req.__getitem__.side_effect = lambda k: {"user_id": user_id}[k]
    body_str = json.dumps(body) if body is not None else ""
    req.content_length = len(body_str) if body else 0
    req.json = AsyncMock(return_value=body or {})
    req.match_info = match_info or {}
    req.query = query or {}
    # 한글 주석: app[db_pool] 의무 + .get("db_pool") audit graceful skip.
    req.app = MagicMock()
    req.app.__getitem__.side_effect = lambda k: {"db_pool": db_pool}[k]
    req.app.get = lambda k, default=None: db_pool if k == "db_pool" else default
    req.headers = MagicMock()
    req.headers.get = lambda k, default="": (
        "TooTalk/0.4.0" if k == "User-Agent" else default
    )
    req.remote = "10.0.0.1"
    return req


# ─── 1. POST /api/rooms — create ────────────────────────────────────────────


class TestCreateRoom:
    @pytest.mark.asyncio
    async def test_create_room_success_audit_room_create(
        self, monkeypatch
    ) -> None:
        # 한글 주석: ROOM_CREATE audit row INSERT 정합 검증.
        pool, cursor = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42, body={"kind": "group"})

        mock_insert_room = AsyncMock(return_value=77)
        mock_insert_peer = AsyncMock(return_value=1)
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_room",
            mock_insert_room,
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            mock_insert_peer,
        )

        resp = await handle_create_room(req)
        assert resp.status == 201
        body = json.loads(resp.body.decode("utf-8"))
        assert body["ok"] is True
        assert body["id"] == 77
        assert body["kind"] == "group"
        assert body["owner_id"] == 42
        assert len(body["room_code"]) == 8

        # owner peer 자동 등록 확인
        assert mock_insert_peer.await_args.kwargs["role"] == "owner"

        # ROOM_CREATE audit INSERT 검증
        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42  # user_id
        assert params[1] == ActivityAction.ROOM_CREATE.value
        assert params[2] == 77  # target_id = room_id
        # 한글 주석: cycle 149 — metadata 안 room_code + kind 동시 emit 정합 검증.
        meta = json.loads(params[5])
        assert meta["room_code"] == body["room_code"]
        assert meta["kind"] == "group"
        # 한글 주석: cycle 149 — users.last_activity_at UPDATE 의 동반 emit 정합.
        assert any(
            "UPDATE users SET last_activity_at" in c[0] for c in sql_calls
        )

    @pytest.mark.asyncio
    async def test_create_room_pool_none_skip_audit(
        self, monkeypatch
    ) -> None:
        # 한글 주석: cycle 149 — pool 부재 시 endpoint 실패 (500) — audit graceful skip 의 경계 조건.
        req = _make_request(db_pool=None, user_id=42, body={"kind": "group"})
        with pytest.raises(web.HTTPInternalServerError, match="db_pool"):
            await handle_create_room(req)

    @pytest.mark.asyncio
    async def test_create_room_invalid_kind_400(self) -> None:
        # 한글 주석: kind = direct/group 외 = 400.
        req = _make_request(db_pool=MagicMock(), body={"kind": "broadcast"})
        with pytest.raises(web.HTTPBadRequest, match="kind"):
            await handle_create_room(req)


# ─── 2. GET /api/rooms — list ───────────────────────────────────────────────


class TestListRooms:
    @pytest.mark.asyncio
    async def test_list_rooms_combines_owner_and_member(
        self, monkeypatch
    ) -> None:
        # 한글 주석: scope=all 시 owner + member 의 중복 제거 + 결과 통합.
        pool, _ = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42)

        owner_room = _make_room(room_id=1, owner_id=42)
        member_room = _make_room(room_id=2, owner_id=99)
        # 한글 주석: id=1 중복 row 의 dedupe 검증.
        dup_room = _make_room(room_id=1, owner_id=42)

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.list_rooms_by_owner",
            AsyncMock(return_value=[owner_room]),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.list_rooms_by_member",
            AsyncMock(return_value=[dup_room, member_room]),
        )

        resp = await handle_list_rooms(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 2  # dedup 적용
        room_ids = {r["id"] for r in body["rooms"]}
        assert room_ids == {1, 2}


# ─── 3. GET /api/rooms/{room_id} — detail ───────────────────────────────────


class TestGetRoom:
    @pytest.mark.asyncio
    async def test_get_room_owner_access_with_members(
        self, monkeypatch
    ) -> None:
        # 한글 주석: owner 접근 + member list 반환.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=_make_peer()),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.list_active_peers",
            AsyncMock(
                return_value=[
                    _make_peer(peer_id=1, user_id=42, role="owner"),
                    _make_peer(peer_id=2, user_id=99, role="member"),
                ]
            ),
        )

        resp = await handle_get_room(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["room"]["id"] == 7
        assert body["member_count"] == 2

    @pytest.mark.asyncio
    async def test_get_room_non_member_forbidden_403(
        self, monkeypatch
    ) -> None:
        # 한글 주석: owner 아님 + 활성 peer 아님 = 403.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=999, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )

        resp = await handle_get_room(req)
        assert resp.status == 403


# ─── 4. POST /api/rooms/{room_id}/join ──────────────────────────────────────


class TestJoinRoom:
    @pytest.mark.asyncio
    async def test_join_room_success_audit_room_join(
        self, monkeypatch
    ) -> None:
        # 한글 주석: ROOM_JOIN audit row INSERT 정합 검증.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=99, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            AsyncMock(return_value=88),
        )

        resp = await handle_join_room(req)
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 99  # user_id (joining)
        assert params[1] == ActivityAction.ROOM_JOIN.value
        assert params[2] == 7  # target_id = room_id

    @pytest.mark.asyncio
    async def test_join_room_already_member_409(self, monkeypatch) -> None:
        # 한글 주석: 이미 활성 참여 중 = 409.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=99, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=_make_peer(user_id=99, role="member")),
        )

        resp = await handle_join_room(req)
        assert resp.status == 409


# ─── 5. POST /api/rooms/{room_id}/leave ─────────────────────────────────────


class TestLeaveRoom:
    @pytest.mark.asyncio
    async def test_leave_room_success_audit_room_leave(
        self, monkeypatch
    ) -> None:
        # 한글 주석: ROOM_LEAVE audit row INSERT 정합 검증.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=99, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=1),
        )

        resp = await handle_leave_room(req)
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 99
        assert params[1] == ActivityAction.ROOM_LEAVE.value
        assert params[2] == 7

    @pytest.mark.asyncio
    async def test_leave_room_not_member_404(self, monkeypatch) -> None:
        # 한글 주석: 활성 참여 부재 = 404.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=99, match_info={"room_id": "7"}
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=0),
        )

        resp = await handle_leave_room(req)
        assert resp.status == 404


# ─── 6. POST /api/rooms/{room_id}/invite ────────────────────────────────────


class TestInviteRoom:
    @pytest.mark.asyncio
    async def test_invite_room_owner_success(self, monkeypatch) -> None:
        # 한글 주석: owner 의 초대 + ROOM_JOIN audit metadata.invited_user_id.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            body={"user_id": 99},
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_peer",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.insert_peer",
            AsyncMock(return_value=88),
        )

        resp = await handle_invite_room(req)
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        meta = json.loads(insert_call[1][5])
        assert meta["invited_user_id"] == 99

    @pytest.mark.asyncio
    async def test_invite_room_non_owner_403(self, monkeypatch) -> None:
        # 한글 주석: owner 아님 = 403.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool,
            user_id=999,
            match_info={"room_id": "7"},
            body={"user_id": 88},
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )

        resp = await handle_invite_room(req)
        assert resp.status == 403


# ─── 7. POST /api/rooms/{room_id}/kick ──────────────────────────────────────


class TestKickRoom:
    @pytest.mark.asyncio
    async def test_kick_room_owner_success(self, monkeypatch) -> None:
        # 한글 주석: owner 의 추방 + ROOM_LEAVE audit metadata.kicked_user_id.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            body={"user_id": 99},
        )

        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.get_room_by_id",
            AsyncMock(return_value=_make_room(owner_id=42)),
        )
        monkeypatch.setattr(
            "server.api.rooms_handlers.rooms_repo.update_peer_left",
            AsyncMock(return_value=1),
        )

        resp = await handle_kick_room(req)
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        meta = json.loads(insert_call[1][5])
        assert meta["kicked_user_id"] == 99

    @pytest.mark.asyncio
    async def test_kick_room_self_kick_blocked_400(self) -> None:
        # 한글 주석: 자기 자신 추방 차단 = 400.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool,
            user_id=42,
            match_info={"room_id": "7"},
            body={"user_id": 42},
        )

        with pytest.raises(web.HTTPBadRequest, match="자기 자신"):
            await handle_kick_room(req)
