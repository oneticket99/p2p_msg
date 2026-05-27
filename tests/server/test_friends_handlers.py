# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 1 cycle 144 — friends_handlers 의 8 endpoint + audit 검증.

REST endpoint × (정상 + 권한 부재 + edge case) 의 10 test.
FRIEND_REQUEST / FRIEND_ACCEPT / FRIEND_REJECT / FRIEND_BLOCK / FRIEND_REMOVE
의 user_activity_log INSERT 정합 검증.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.friends_handlers import (
    handle_accept_friend,
    handle_block_friend,
    handle_list_friends,
    handle_list_pending,
    handle_reject_friend,
    handle_remove_friend,
    handle_request_friend,
    handle_search_user,
)
from server.db.repositories.friends import FriendRow, FriendWithProfile
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


def _make_friend_row(
    *,
    fid: int = 1,
    user_id: int = 42,
    friend_user_id: int = 99,
    status: str = "pending",
) -> FriendRow:
    return FriendRow(
        id=fid,
        user_id=user_id,
        friend_user_id=friend_user_id,
        status=status,
        nickname=None,
        requested_at=datetime(2026, 5, 19, 12, 0, 0),
        accepted_at=None,
    )


def _make_friend_with_profile(
    *,
    fid: int = 1,
    user_id: int = 42,
    friend_user_id: int = 99,
    status: str = "accepted",
    friend_username: str = "alice",
) -> FriendWithProfile:
    return FriendWithProfile(
        id=fid,
        user_id=user_id,
        friend_user_id=friend_user_id,
        status=status,
        nickname=None,
        requested_at=datetime(2026, 5, 19, 12, 0, 0),
        accepted_at=datetime(2026, 5, 19, 12, 5, 0),
        friend_username=friend_username,
        friend_email_verified=1,
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
    req.app = MagicMock()
    req.app.__getitem__.side_effect = lambda k: {"db_pool": db_pool}[k]
    req.app.get = lambda k, default=None: db_pool if k == "db_pool" else default
    req.headers = MagicMock()
    req.headers.get = lambda k, default="": (
        "TooTalk/0.5.0" if k == "User-Agent" else default
    )
    req.remote = "10.0.0.1"
    return req


# ─── 1. POST /api/friends — request ─────────────────────────────────────────


class TestRequestFriend:
    @pytest.mark.asyncio
    async def test_request_friend_success_audit(self, monkeypatch) -> None:
        # FRIEND_REQUEST audit row INSERT 정합 검증.
        pool, cursor = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42, body={"user_id": 99})

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend",
            AsyncMock(return_value=77),
        )

        resp = await handle_request_friend(req)
        assert resp.status == 201
        body = json.loads(resp.body.decode("utf-8"))
        assert body["ok"] is True
        assert body["id"] == 77
        assert body["status"] == "pending"

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.FRIEND_REQUEST.value
        assert params[2] == 99
        # metadata JSON 정합 — friend_id + nickname 보존.
        assert params[5] is not None
        meta = json.loads(params[5])
        assert meta["friend_id"] == 77
        assert "nickname" in meta

    @pytest.mark.asyncio
    async def test_request_friend_self_blocked_400(self) -> None:
        # 자기 자신 친구 차단 = 400.
        req = _make_request(db_pool=MagicMock(), user_id=42, body={"user_id": 42})
        with pytest.raises(web.HTTPBadRequest, match="자기 자신"):
            await handle_request_friend(req)

    @pytest.mark.asyncio
    async def test_request_friend_already_exists_409(self, monkeypatch) -> None:
        # 이미 accepted/pending row 가용 시 409.
        pool, _ = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42, body={"user_id": 99})

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=_make_friend_row(status="accepted")),
        )

        resp = await handle_request_friend(req)
        assert resp.status == 409


# ─── 2. GET /api/friends — list ─────────────────────────────────────────────


class TestListFriends:
    @pytest.mark.asyncio
    async def test_list_friends_returns_count_and_rows(
        self, monkeypatch
    ) -> None:
        # list_by_user 결과 의 JSON 직렬화 + count 정합.
        pool, _ = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42)

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.list_by_user",
            AsyncMock(
                return_value=[
                    _make_friend_with_profile(fid=1, friend_user_id=99),
                    _make_friend_with_profile(
                        fid=2, friend_user_id=100, status="pending"
                    ),
                ]
            ),
        )

        resp = await handle_list_friends(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 2
        assert body["friends"][0]["friend_user_id"] == 99
        assert body["friends"][0]["friend_email_verified"] is True


# ─── 3. GET /api/friends/pending ────────────────────────────────────────────


class TestListPending:
    @pytest.mark.asyncio
    async def test_list_pending_filters_incoming(self, monkeypatch) -> None:
        # pending 수신 list — friend_user_id = user_id 의 row.
        pool, _ = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42)

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.list_pending_requests",
            AsyncMock(
                return_value=[
                    _make_friend_with_profile(
                        fid=3, user_id=88, friend_user_id=42, status="pending"
                    )
                ]
            ),
        )

        resp = await handle_list_pending(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        assert body["count"] == 1
        assert body["pending"][0]["user_id"] == 88


# ─── 4. GET /api/friends/search ─────────────────────────────────────────────


class TestSearchUser:
    @pytest.mark.asyncio
    async def test_search_user_excludes_self(self, monkeypatch) -> None:
        # 자기 PK row 의 사전 필터.
        pool, _ = _mock_pool()
        req = _make_request(db_pool=pool, user_id=42, query={"q": "ali"})

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.search_users_by_username",
            AsyncMock(
                return_value=[
                    {"id": 42, "username": "alice", "email_verified": True},
                    {"id": 99, "username": "alibaba", "email_verified": False},
                ]
            ),
        )

        resp = await handle_search_user(req)
        assert resp.status == 200
        body = json.loads(resp.body.decode("utf-8"))
        # 자기 PK 제외 — 1건 만 반환
        assert body["count"] == 1
        assert body["results"][0]["id"] == 99

    @pytest.mark.asyncio
    async def test_search_user_short_keyword_400(self) -> None:
        # keyword 1자 = 400.
        req = _make_request(db_pool=MagicMock(), user_id=42, query={"q": "a"})
        with pytest.raises(web.HTTPBadRequest, match="2자 이상"):
            await handle_search_user(req)


# ─── 5. POST /api/friends/{user_id}/accept ──────────────────────────────────


class TestAcceptFriend:
    @pytest.mark.asyncio
    async def test_accept_friend_inserts_reverse_row_audit(
        self, monkeypatch
    ) -> None:
        # accept_friend rowcount=1 + reverse row INSERT + FRIEND_ACCEPT audit.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"user_id": "99"}
        )

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.accept_friend",
            AsyncMock(return_value=1),
        )
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=None),
        )
        insert_mock = AsyncMock(return_value=88)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend",
            insert_mock,
        )

        resp = await handle_accept_friend(req)
        assert resp.status == 200

        # reverse row 의 status=accepted 확인
        assert insert_mock.await_args.kwargs["status"] == "accepted"
        assert insert_mock.await_args.kwargs["user_id"] == 42
        assert insert_mock.await_args.kwargs["friend_user_id"] == 99

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.FRIEND_ACCEPT.value
        assert params[2] == 99
        # FRIEND_ACCEPT metadata=None 정합 — JSON null serialize 회피.
        assert params[5] is None

    @pytest.mark.asyncio
    async def test_accept_friend_pending_not_found_404(
        self, monkeypatch
    ) -> None:
        # pending row 부재 = 404.
        pool, _ = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"user_id": "99"}
        )

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.accept_friend",
            AsyncMock(return_value=0),
        )

        resp = await handle_accept_friend(req)
        assert resp.status == 404


# ─── 6. POST /api/friends/{user_id}/reject ──────────────────────────────────


class TestRejectFriend:
    @pytest.mark.asyncio
    async def test_reject_friend_marks_removed_audit(
        self, monkeypatch
    ) -> None:
        # pending → removed 갱신 + FRIEND_REJECT audit.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"user_id": "99"}
        )

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status",
            AsyncMock(return_value=1),
        )

        resp = await handle_reject_friend(req)
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.FRIEND_REJECT.value
        assert params[2] == 99
        assert params[5] is None


# ─── 7. POST /api/friends/{user_id}/block ───────────────────────────────────


class TestBlockFriend:
    @pytest.mark.asyncio
    async def test_block_friend_inserts_when_none_audit(
        self, monkeypatch
    ) -> None:
        # 기존 row 부재 → blocked 신규 INSERT + FRIEND_BLOCK audit.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"user_id": "99"}
        )

        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.get_friend",
            AsyncMock(return_value=None),
        )
        insert_mock = AsyncMock(return_value=55)
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.insert_friend",
            insert_mock,
        )

        resp = await handle_block_friend(req)
        assert resp.status == 200
        assert insert_mock.await_args.kwargs["status"] == "blocked"

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.FRIEND_BLOCK.value
        assert params[2] == 99
        assert params[5] is None


# ─── 8. DELETE /api/friends/{user_id} ───────────────────────────────────────


class TestRemoveFriend:
    @pytest.mark.asyncio
    async def test_remove_friend_marks_removed_both_directions(
        self, monkeypatch
    ) -> None:
        # 양방향 update_status removed + FRIEND_REMOVE audit.
        pool, cursor = _mock_pool()
        req = _make_request(
            db_pool=pool, user_id=42, match_info={"user_id": "99"}
        )

        update_mock = AsyncMock(side_effect=[1, 1])
        monkeypatch.setattr(
            "server.api.friends_handlers.friends_repo.update_status",
            update_mock,
        )

        resp = await handle_remove_friend(req)
        assert resp.status == 200
        # 2번 호출 — owner row + peer row
        assert update_mock.await_count == 2

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42
        assert params[1] == ActivityAction.FRIEND_REMOVE.value
        assert params[2] == 99
        assert params[5] is None


# ─── 9. 5 ENUM 정합 sweep ───────────────────────────────────────────────────


class TestFriendEnumSweep:
    @pytest.mark.asyncio
    async def test_all_five_friend_enums_distinct_values(self) -> None:
        # 5 ENUM string value 정합 + 중복 부재.
        values = {
            ActivityAction.FRIEND_REQUEST.value,
            ActivityAction.FRIEND_ACCEPT.value,
            ActivityAction.FRIEND_REJECT.value,
            ActivityAction.FRIEND_BLOCK.value,
            ActivityAction.FRIEND_REMOVE.value,
        }
        assert len(values) == 5
        assert ActivityAction.FRIEND_REQUEST.value == "friend_request"
        assert ActivityAction.FRIEND_ACCEPT.value == "friend_accept"
        assert ActivityAction.FRIEND_REJECT.value == "friend_reject"
        assert ActivityAction.FRIEND_BLOCK.value == "friend_block"
        assert ActivityAction.FRIEND_REMOVE.value == "friend_remove"
