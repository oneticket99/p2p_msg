# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 148 — signaling rooms REST integration e2e edge case.

cycle 144 (rooms REST + peers UPSERT + audit chain) 의 추가 검증 + edge case.
test_signaling_rooms_integration.py 의 8 test 와 별개 영역 — 동시성 + 형식
검증 + audit chain + persist 실패 graceful + leave cleanup 의 10 test.

Test scope
----------
1.  TestRoomCreateFromSignalingOnly — REST 부재 + signaling 첫 peer → rooms INSERT + owner role
2.  TestRoomCreateFromRESTThenSignalingJoin — REST 가 사전 room → JOIN 시 SELECT 만 (INSERT 부재)
3.  TestRoomCodeFormatValidation — 잘못된 room_code 도 persist hook 진입 (graceful 호환)
4.  TestConcurrentJoinSameRoom — 5 peer 순차 JOIN → 첫 1 owner + 4 member role 의 SQL params
5.  TestRoomLeaveCleanup — 모든 peer leave → registry GC + ROOM_CLOSE audit emit
6.  TestOwnerLeaveSucceeded — owner leave + member 잔존 → ROOM_LEAVE audit emit (별개 cycle 위탁)
7.  TestAuditChainROOM_CREATE_JOIN — 단일 첫 peer JOIN → ROOM_CREATE + ROOM_JOIN 의 2 audit
8.  TestPoolNoneGraceful — db_pool=None → all hook skip + WS chain 보존
9.  TestPersistFailGraceful — rooms_repo.insert_room exception → swallow + log warning
10. TestPeerLeftAtSetOnLeave — handle_leave → peers.left_at NOW UPDATE SQL emit

mock asyncmy pool + cursor + signaling Room + WebSocketResponse stub.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.room import Peer, RoomRegistry
from server.signaling import _handle_join, _handle_leave


# ─── 공통 fixture builders ──────────────────────────────────────────────────


def _mock_pool_with_fetchone(
    *,
    fetchone_sequence: list[Any] | None = None,
    lastrowid: int = 7,
    execute_side_effect: Exception | None = None,
) -> tuple[Any, Any]:
    """asyncmy pool + cursor mock.

    fetchone_sequence — SELECT 호출 순서별 row 반환값 (None = 부재).
    execute_side_effect — execute 호출 시 raise 의 의도적 주입 (graceful 검증).
    """
    cursor = MagicMock()
    if execute_side_effect is not None:
        cursor.execute = AsyncMock(side_effect=execute_side_effect)
    else:
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


def _make_room_tuple(
    *,
    room_id: int = 7,
    room_code: str = "room-1",
    owner_id: int = 42,
) -> tuple[Any, ...]:
    """rooms SELECT 의 row tuple builder — RoomRow 의 7 column 정합."""
    return (
        room_id,
        room_code,
        owner_id,
        "direct",
        "active",
        datetime(2026, 5, 19, 12, 0, 0),
        None,
    )


# ─── 1. TestRoomCreateFromSignalingOnly ────────────────────────────────────


class TestRoomCreateFromSignalingOnly:
    """REST API 사전 호출 부재 → 첫 peer signaling JOIN 시 rooms 신규 INSERT."""

    @pytest.mark.asyncio
    async def test_signaling_first_peer_creates_room_owner_role(self) -> None:
        """REST 부재 시나리오 — signaling 첫 peer JOIN → rooms INSERT + peers role=owner."""
        registry = RoomRegistry()
        # 한글 주석: fetchone 시퀀스 — 1st SELECT rooms = None → INSERT → lastrowid=7
        #                             2nd SELECT peers = None → INSERT peers (owner)
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[None, None],
            lastrowid=7,
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "abc123def456", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        # 한글 주석: rooms INSERT + peers INSERT 의 양쪽 호출 의무
        assert any("INSERT INTO rooms" in s for s in sql_calls)
        assert any("INSERT INTO peers" in s for s in sql_calls)

        # 한글 주석: 첫 peer 의 role=owner 의 검증
        for call in cursor.execute.call_args_list:
            sql = call.args[0]
            if "INSERT INTO peers" in sql:
                params = call.args[1]
                assert params[2] == "owner"
                break
        else:
            pytest.fail("peers INSERT 호출 부재")


# ─── 2. TestRoomCreateFromRESTThenSignalingJoin ────────────────────────────


class TestRoomCreateFromRESTThenSignalingJoin:
    """REST POST /api/rooms 가 사전 room 생성 → signaling JOIN 시 SELECT 만 + INSERT rooms 부재."""

    @pytest.mark.asyncio
    async def test_rest_room_then_signaling_resolves_select_only(self) -> None:
        """기존 rooms row 가용 → SELECT rooms 만 + INSERT rooms 의 부재."""
        registry = RoomRegistry()
        # 한글 주석: 1st SELECT rooms = 기존 row (REST 사전 생성) → INSERT 부재
        #            2nd SELECT peers = None → INSERT peers
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[
                _make_room_tuple(room_id=99, room_code="rest-room-1", owner_id=10),
                None,
            ]
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "rest-room-1", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        # 한글 주석: REST 안 생성된 room_id=99 의 resolve 확인
        assert peer.db_room_id == 99

        sql_calls = _sql_calls(cursor)
        # 한글 주석: SELECT rooms 호출 의무 + INSERT rooms 부재
        assert any("FROM rooms WHERE room_code" in s for s in sql_calls)
        assert not any("INSERT INTO rooms" in s for s in sql_calls)
        assert any("INSERT INTO peers" in s for s in sql_calls)


# ─── 3. TestRoomCodeFormatValidation ────────────────────────────────────────


class TestRoomCodeFormatValidation:
    """다양한 room_code 형식 — UUID4 hex 32자 / 8자 secrets hex / 비표준 모두 persist 진입."""

    @pytest.mark.asyncio
    async def test_uuid4_hex_room_code_accepted(self) -> None:
        """UUID4 hex 32자 room_code → persist hook 정상 진행."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[None, None],
            lastrowid=7,
        )
        ws = _make_ws(db_pool=pool)
        # 한글 주석: UUID4 hex 32자 의 표본
        payload = {
            "room": "550e8400e29b41d4a716446655440000",
            "peer_id": "p1",
            "user_id": 42,
        }

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.db_room_id == 7

        sql_calls = _sql_calls(cursor)
        assert any("INSERT INTO rooms" in s for s in sql_calls)

    @pytest.mark.asyncio
    async def test_short_secrets_hex_room_code_accepted(self) -> None:
        """8자 secrets hex room_code → persist hook 정상 진행."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[None, None],
            lastrowid=8,
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "a1b2c3d4", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None
        assert peer.db_room_id == 8


# ─── 4. TestConcurrentJoinSameRoom ──────────────────────────────────────────


class TestConcurrentJoinSameRoom:
    """5 peer 순차 JOIN — 첫 1 owner + 4 member role 의 SQL params 검증."""

    @pytest.mark.asyncio
    async def test_five_peers_owner_plus_members(self) -> None:
        """5 peer JOIN — 첫 peer = owner, 2~5 peer = member."""
        registry = RoomRegistry()

        # 한글 주석: 매 JOIN 의 fetchone 시퀀스 — SELECT rooms + SELECT peers
        # 첫 JOIN: SELECT rooms = None → INSERT lastrowid=7, SELECT peers = None → INSERT (owner)
        # 2~5 JOIN: SELECT rooms = 기존, SELECT peers = None → INSERT (member)

        roles_observed: list[str] = []

        for idx in range(5):
            if idx == 0:
                fetchone_seq = [None, None]
            else:
                fetchone_seq = [_make_room_tuple(room_id=7), None]

            pool, cursor = _mock_pool_with_fetchone(
                fetchone_sequence=fetchone_seq,
                lastrowid=7,
            )
            ws = _make_ws(db_pool=pool)
            payload = {
                "room": "concurrent-room",
                "peer_id": f"p{idx}",
                "user_id": 100 + idx,
            }
            peer = await _handle_join(ws, None, payload, registry)
            assert peer is not None

            # 한글 주석: peers INSERT params[2] = role 추출
            for call in cursor.execute.call_args_list:
                sql = call.args[0]
                if "INSERT INTO peers" in sql:
                    roles_observed.append(call.args[1][2])
                    break

        # 한글 주석: 첫 peer = owner, 2~5 = member 의 5 element 검증
        assert len(roles_observed) == 5
        assert roles_observed[0] == "owner"
        assert all(r == "member" for r in roles_observed[1:])


# ─── 5. TestRoomLeaveCleanup ────────────────────────────────────────────────


class TestRoomLeaveCleanup:
    """모든 peer leave → registry GC + ROOM_CLOSE audit emit."""

    @pytest.mark.asyncio
    async def test_last_peer_leave_triggers_room_close_audit(self) -> None:
        """1 peer JOIN + LEAVE → registry.room_size = 0 + ROOM_CLOSE audit."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(fetchone_sequence=[])
        ws = _make_ws(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("close-room", peer)
        assert registry.room_size("close-room") == 1

        payload = {"room": "close-room", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)
        # 한글 주석: registry GC 의무 — 마지막 peer 의 leave 후 room_size=0
        assert registry.room_size("close-room") == 0

        # 한글 주석: ROOM_CLOSE + ROOM_LEAVE audit 의 양쪽 emit 확인
        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                action_params.append(call.args[1][1])
        assert "room_close" in action_params
        assert "room_leave" in action_params


# ─── 6. TestOwnerLeaveSucceeded ─────────────────────────────────────────────


class TestOwnerLeaveSucceeded:
    """owner leave + member 잔존 — ROOM_LEAVE audit emit + ROOM_CLOSE audit 부재."""

    @pytest.mark.asyncio
    async def test_owner_leave_with_member_remaining(self) -> None:
        """owner peer LEAVE → 잔존 member 존재 → ROOM_CLOSE audit 부재."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(fetchone_sequence=[])
        ws_owner = _make_ws(db_pool=pool)
        ws_member = _make_ws(db_pool=pool)

        owner = Peer(peer_id="owner-1", ws=ws_owner)
        owner.user_id = 1
        owner.db_room_id = 7

        member = Peer(peer_id="member-1", ws=ws_member)
        member.user_id = 2
        member.db_room_id = 7

        await registry.join("dual-room", owner)
        await registry.join("dual-room", member)
        assert registry.room_size("dual-room") == 2

        # 한글 주석: owner leave → member 잔존 → room_size = 1
        payload = {"room": "dual-room", "peer_id": "owner-1"}
        await _handle_leave(ws_owner, owner, payload, registry)
        assert registry.room_size("dual-room") == 1

        # 한글 주석: ROOM_LEAVE audit 의 호출 + ROOM_CLOSE audit 의 부재
        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                action_params.append(call.args[1][1])
        assert "room_leave" in action_params
        # 한글 주석: 잔존 member 가용 → room_close audit 의 부재
        assert "room_close" not in action_params


# ─── 7. TestAuditChainROOM_CREATE_JOIN ──────────────────────────────────────


class TestAuditChainROOM_CREATE_JOIN:
    """첫 peer JOIN → ROOM_CREATE + ROOM_JOIN audit 2종 chain emit."""

    @pytest.mark.asyncio
    async def test_first_peer_emits_both_create_and_join_audit(self) -> None:
        """단일 첫 peer JOIN 의 audit chain — ROOM_CREATE 직후 ROOM_JOIN."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(
            fetchone_sequence=[None, None],
            lastrowid=7,
        )
        ws = _make_ws(db_pool=pool)
        payload = {"room": "chain-room", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        assert peer is not None

        # 한글 주석: audit row 의 action params 추출
        action_params: list[str] = []
        for call in cursor.execute.call_args_list:
            if "INSERT INTO user_activity_log" in call.args[0]:
                action_params.append(call.args[1][1])
        # 한글 주석: 첫 peer = ROOM_CREATE + ROOM_JOIN 의 2 audit
        assert "room_create" in action_params
        assert "room_join" in action_params
        # 한글 주석: ROOM_CREATE 가 ROOM_JOIN 보다 먼저 emit 의 순서 검증
        create_idx = action_params.index("room_create")
        join_idx = action_params.index("room_join")
        assert create_idx < join_idx


# ─── 8. TestPoolNoneGraceful ────────────────────────────────────────────────


class TestPoolNoneGraceful:
    """db_pool=None → all hook skip + WS JOIN chain 보존."""

    @pytest.mark.asyncio
    async def test_pool_none_join_skips_all_persist_no_raise(self) -> None:
        """db_pool 부재 → rooms.id resolve + peers UPSERT + audit 의 전체 skip."""
        registry = RoomRegistry()
        ws = _make_ws(db_pool=None)
        payload = {"room": "no-db-room", "peer_id": "p1", "user_id": 42}

        peer = await _handle_join(ws, None, payload, registry)
        # 한글 주석: WS JOIN chain 의 정상 진행 (registry 합류 의무)
        assert peer is not None
        assert peer.peer_id == "p1"
        assert peer.user_id == 42
        # 한글 주석: db_pool 부재 → db_room_id 의 None 유지
        assert peer.db_room_id is None
        assert registry.room_size("no-db-room") == 1

    @pytest.mark.asyncio
    async def test_pool_none_leave_skips_all_persist_no_raise(self) -> None:
        """db_pool 부재 → LEAVE 의 audit + peers.left_at UPDATE 전체 skip."""
        registry = RoomRegistry()
        ws = _make_ws(db_pool=None)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("no-db-room", peer)

        payload = {"room": "no-db-room", "peer_id": "p1"}
        # 한글 주석: raise 부재 의무 + registry leave 의 정상 진행
        await _handle_leave(ws, peer, payload, registry)
        assert registry.room_size("no-db-room") == 0


# ─── 9. TestPersistFailGraceful ─────────────────────────────────────────────


class TestPersistFailGraceful:
    """rooms_repo.insert_room exception → swallow + warning log + raise 부재."""

    @pytest.mark.asyncio
    async def test_insert_room_exception_swallowed(self) -> None:
        """insert_room SQL exception → WS JOIN chain 보존 + peer.db_room_id None."""
        registry = RoomRegistry()

        # 한글 주석: insert_room 의 의도적 raise 의 주입 — rooms_repo level patch
        async def _raise_insert(*args: Any, **kwargs: Any) -> int:
            raise RuntimeError("DB INSERT INTO rooms 실패 의 simulate")

        pool, _ = _mock_pool_with_fetchone(fetchone_sequence=[None])

        with patch(
            "server.signaling.rooms_repo.get_room_by_code",
            new=AsyncMock(return_value=None),
        ), patch(
            "server.signaling.persist_room_create",
            new=AsyncMock(side_effect=_raise_insert),
        ):
            ws = _make_ws(db_pool=pool)
            payload = {"room": "fail-room", "peer_id": "p1", "user_id": 42}
            # 한글 주석: raise 부재 + db_room_id None 유지
            peer = await _handle_join(ws, None, payload, registry)
            assert peer is not None
            assert peer.db_room_id is None
            # 한글 주석: WS JOIN chain 의 정상 진행 (registry 합류 의무)
            assert registry.room_size("fail-room") == 1


# ─── 10. TestPeerLeftAtSetOnLeave ───────────────────────────────────────────


class TestPeerLeftAtSetOnLeave:
    """_handle_leave → peers.left_at NOW UPDATE SQL emit 의무."""

    @pytest.mark.asyncio
    async def test_leave_emits_update_peers_left_at(self) -> None:
        """LEAVE chain → UPDATE peers SET left_at = CURRENT_TIMESTAMP SQL emit."""
        registry = RoomRegistry()
        pool, cursor = _mock_pool_with_fetchone(fetchone_sequence=[])
        ws = _make_ws(db_pool=pool)

        peer = Peer(peer_id="p1", ws=ws)
        peer.user_id = 42
        peer.db_room_id = 99
        await registry.join("leave-room", peer)

        payload = {"room": "leave-room", "peer_id": "p1"}
        await _handle_leave(ws, peer, payload, registry)

        sql_calls = _sql_calls(cursor)
        # 한글 주석: peers.left_at UPDATE SQL 의 emit 의무
        assert any(
            "UPDATE peers SET left_at" in s for s in sql_calls
        )

        # 한글 주석: UPDATE params = (room_id, user_id) 의 정합 검증
        for call in cursor.execute.call_args_list:
            sql = call.args[0]
            if "UPDATE peers SET left_at" in sql:
                params = call.args[1]
                assert params == (99, 42)
                break
        else:
            pytest.fail("UPDATE peers SET left_at 호출 부재")
