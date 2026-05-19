# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 144 — signaling WS handler 안 rooms REST API integration.

cycle 127 (ROOM_JOIN/LEAVE audit) + cycle 135 (rooms REST 7 endpoint + peers row 관리)
의 chain 통합 검증. signaling.py 안 _handle_join / _handle_leave 의 rooms.id
resolve + peers row UPSERT + audit 의 8 test.

Test scope
----------
- room_code → rooms.id resolve 의 SELECT 호출 (mock 안 cursor capture)
- 부재 시 INSERT INTO rooms 의 신규 row 생성 (첫 peer = owner)
- 존재 시 SELECT 만 + peer.db_room_id mapping
- peers row UPSERT — 기존 활성 row 부재 시 INSERT, 존재 시 silent skip
- _handle_leave 의 room_code fallback resolve
- pool 부재 시 SQL 전체 skip + raise 부재
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.db.repositories.rooms import PeerRow, RoomRow
from server.room import Peer, RoomRegistry
from server.signaling import _handle_join, _handle_leave


# ─── fixtures + builders ────────────────────────────────────────────────────


def _make_room_row(*, room_id: int = 7, room_code: str = "room-1") -> RoomRow:
    """rooms row dataclass builder — get_room_by_code mock 응답 의."""
    return RoomRow(
        id=room_id,
        room_code=room_code,
        owner_id=42,
        kind="direct",
        status="active",
        created_at=datetime(2026, 5, 19, 12, 0, 0),
        closed_at=None,
    )


def _make_peer_row(*, peer_id: int = 1, room_id: int = 7) -> PeerRow:
    """peers row dataclass builder — get_peer mock 응답 의."""
    return PeerRow(
        id=peer_id,
        room_id=room_id,
        user_id=42,
        role="owner",
        joined_at=datetime(2026, 5, 19, 12, 0, 0),
        left_at=None,
    )


def _mock_pool_with_fetchone(
    *,
    fetchone_sequence: list[Any] | None = None,
    lastrowid: int = 7,
) -> tuple[Any, Any]:
    """asyncmy pool + cursor mock 안 fetchone 응답 시퀀스 의 주입.

    fetchone_sequence = SELECT 호출 순서별 row 반환값 (None = 부재). 마지막 row
    이후 호출은 None 반환 (StopIteration 방어).
    """
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = lastrowid
    cursor.rowcount = 1

    seq = list(fetchone_sequence or [])

    async def _fetchone() -> Any:
        if not seq:
            return None
        return seq.pop(0)

    cursor.fetchone = _fetchone

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


def _make_ws(*, db_pool: Any = None) -> Any:
    """aiohttp ws + request mock — db_pool 의 app dict 안 inject."""
    app = MagicMock()
    app.get = lambda k, default=None: db_pool if k == "db_pool" else default
    req = MagicMock()
    req.app = app
    ws = MagicMock()
    ws._req = req
    ws.send_json = AsyncMock()
    ws.send_str = AsyncMock()
    return ws


def _sql_calls(cursor: Any) -> list[str]:
    """cursor.execute 호출 의 SQL 문자열 list 추출."""
    return [c.args[0] for c in cursor.execute.call_args_list]


# ─── _handle_join 의 rooms REST integration test ──────────────────────────


class TestHandleJoinRoomsIntegration:
    """_handle_join 안 rooms REST API integration 6 test."""

    @pytest.mark.asyncio
    async def test_existing_room_select_only(self) -> None:
        """기존 rooms row 가용 시 — SELECT rooms WHERE room_code 만 호출, INSERT rooms 부재."""
        registry = RoomRegistry()
        # 한글 주석: fetchone 시퀀스 — rooms 의 row + peers 의 None (UPSERT 의 신규 INSERT 유도)
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[
                (7, "room-1", 42, "direct", "active",
                 datetime(2026, 5, 19, 12, 0, 0), None),
                None,
            ]
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "room-1", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        # 한글 주석: SELECT rooms WHERE room_code 호출 확인
        assert any(
            "FROM rooms WHERE room_code" in s for s in sql_calls
        )
        # 한글 주석: rooms INSERT 의 부재 — 기존 room 재사용
        assert not any("INSERT INTO rooms" in s for s in sql_calls)
        # 한글 주석: peers INSERT 의 호출 — 신규 활성 peer
        assert any("INSERT INTO peers" in s for s in sql_calls)

    @pytest.mark.asyncio
    async def test_new_room_creates_rooms_row(self) -> None:
        """rooms row 부재 시 — INSERT INTO rooms 호출 + peer.db_room_id 갱신 + ROOM_CREATE audit metadata 정합."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            # 한글 주석: 1st SELECT rooms = None (부재) → INSERT → lastrowid=7
            #            2nd SELECT peers = None (부재) → INSERT peers
            fetchone_sequence=[None, None],
            lastrowid=7,
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "room-2", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        # 한글 주석: 신규 rooms.id 의 peer 객체 안 mapping
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        # 한글 주석: rooms INSERT 의 호출
        assert any("INSERT INTO rooms" in s for s in sql_calls)
        # 한글 주석: peers INSERT 의 호출
        assert any("INSERT INTO peers" in s for s in sql_calls)

        # 한글 주석: cycle 149 — ROOM_CREATE audit row 의 metadata 안 room_id (room_code) + peer_id 정합 검증.
        import json as _json
        room_create_meta = None
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                params = call.args[1]
                if params[1] == "room_create":
                    room_create_meta = _json.loads(params[5])
                    # 한글 주석: target_id = peer.db_room_id (7)
                    assert params[2] == 7
                    # 한글 주석: user_id = JOIN payload user_id (42)
                    assert params[0] == 42
                    break
        assert room_create_meta is not None
        assert room_create_meta["room_id"] == "room-2"
        assert room_create_meta["peer_id"] == "p1"

    @pytest.mark.asyncio
    async def test_first_peer_role_owner(self) -> None:
        """첫 peer 합류 (room_size == 1) = role=owner 의 INSERT peers + ROOM_CREATE audit 의 actual emit."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[None, None],
            lastrowid=7,
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "room-3", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None

        # 한글 주석: peers INSERT 의 params 추출 → role 확인
        for call in cursor.execute.call_args_list:
            sql = call.args[0]
            if "INSERT INTO peers" in sql:
                params = call.args[1]
                # params = (room_id, user_id, role) — 3 element
                assert params[2] == "owner"
                break
        else:
            pytest.fail("peers INSERT 호출 부재")

        # 한글 주석: cycle 149 — 신규 room (room_size==1) 의 ROOM_CREATE audit 의 actual emit 정합.
        # signaling.py _handle_join 안 230~247 라인 chain (persist_room_create 직후 log_activity ROOM_CREATE).
        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                params = call.args[1]
                action_params.append(params[1])
        assert "room_create" in action_params
        assert "room_join" in action_params

    @pytest.mark.asyncio
    async def test_second_peer_role_member(self) -> None:
        """이미 1 peer 있는 방 에 추가 peer 합류 = role=member."""
        registry = RoomRegistry()
        # 한글 주석: 사전 peer 1건 의 registry 안 등록 — room_size = 1 의 상태
        pre_peer = Peer(peer_id="p0", ws=_make_ws())
        pre_peer.user_id = 1
        await registry.join("room-4", pre_peer)
        assert registry.room_size("room-4") == 1

        pool, cursor = _mock_pool_with_fetchone(
            # 한글 주석: SELECT rooms (존재) + SELECT peers (부재 = INSERT 진행)
            fetchone_sequence=[
                (7, "room-4", 1, "direct", "active",
                 datetime(2026, 5, 19, 12, 0, 0), None),
                None,
            ]
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "room-4", "peer_id": "p2", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None

        # 한글 주석: 추가 peer 합류 후 room_size = 2 → role=member 의 INSERT
        for call in cursor.execute.call_args_list:
            sql = call.args[0]
            if "INSERT INTO peers" in sql:
                params = call.args[1]
                assert params[2] == "member"
                break
        else:
            pytest.fail("peers INSERT 호출 부재")

    @pytest.mark.asyncio
    async def test_existing_peer_row_upsert_skip(self) -> None:
        """기존 활성 peers row 가용 시 — 신규 INSERT 부재 (idempotency)."""
        registry = RoomRegistry()
        # 한글 주석: fetchone 시퀀스 — SELECT rooms (존재) + SELECT peers (존재)
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[
                (7, "room-5", 42, "direct", "active",
                 datetime(2026, 5, 19, 12, 0, 0), None),
                (1, 7, 42, "owner",
                 datetime(2026, 5, 19, 12, 0, 0), None),
            ]
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "room-5", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        # 한글 주석: 기존 활성 peer 가용 → 신규 INSERT peers 의 부재
        assert not any("INSERT INTO peers" in s for s in sql_calls)

    @pytest.mark.asyncio
    async def test_pool_none_no_sql_no_raise(self) -> None:
        """pool 부재 — rooms.id resolve 전체 skip + raise 부재."""
        registry = RoomRegistry()
        ws = _make_ws(db_pool=None)
        payload = {"room": "room-6", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        # 한글 주석: db_pool 부재 → db_room_id 의 None 유지
        assert peer.db_room_id is None


# ─── _handle_leave 의 rooms REST integration test ─────────────────────────


class TestHandleLeaveRoomsIntegration:
    """_handle_leave 안 rooms REST API integration 2 test."""

    @pytest.mark.asyncio
    async def test_leave_resolves_room_code_when_db_room_id_missing(self) -> None:
        """db_room_id 부재 시 LEAVE 의 room_code → rooms.id 의 fallback resolve."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            # 한글 주석: SELECT rooms (존재) — peers UPDATE left_at 의 chain
            fetchone_sequence=[
                (7, "room-7", 42, "direct", "active",
                 datetime(2026, 5, 19, 12, 0, 0), None),
            ]
        )
        ws = _make_ws(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        # 한글 주석: db_room_id 부재 의 시나리오 — resolve fallback 의 trigger
        await registry.join("room-7", peer)

        payload = {"room": "room-7", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)

        # 한글 주석: db_room_id 가 fallback resolve 의 결과 7 로 갱신
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        # 한글 주석: SELECT rooms + UPDATE peers SET left_at 의 호출
        assert any(
            "FROM rooms WHERE room_code" in s for s in sql_calls
        )
        assert any(
            "UPDATE peers SET left_at" in s for s in sql_calls
        )

    @pytest.mark.asyncio
    async def test_leave_with_existing_db_room_id_skips_resolve(self) -> None:
        """db_room_id 가용 시 LEAVE — SELECT rooms 의 호출 부재 (이미 mapped)."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[]
        )
        ws = _make_ws(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("room-8", peer)

        payload = {"room": "room-8", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)

        sql_calls = _sql_calls(cursor)
        # 한글 주석: 이미 db_room_id 가용 → SELECT rooms 의 호출 부재
        assert not any(
            "FROM rooms WHERE room_code" in s for s in sql_calls
        )
        # 한글 주석: UPDATE peers SET left_at 의 호출 정상
        assert any(
            "UPDATE peers SET left_at" in s for s in sql_calls
        )
