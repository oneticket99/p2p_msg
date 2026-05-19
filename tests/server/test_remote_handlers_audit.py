# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 5 cycle 132 — remote_handlers 의 REMOTE_REQUEST + REMOTE_GRANT +
REMOTE_REVOKE 3 ActivityAction audit hook 검증.

DB audit endpoint coverage 15 → 18 ActivityAction 의 wiring 검증.
- pool 가용 시 INSERT user_activity_log SQL 호출 + action params 정합.
- pool 부재 시 graceful skip + endpoint 응답 무영향.
- 실 Quartz / BitBlt / X11 binding = 별개 cycle 166+ (skeleton only).
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.api.remote_handlers import (
    handle_remote_grant,
    handle_remote_request,
    handle_remote_revoke,
)
from server.db.repositories.user_activity import ActivityAction


def _mock_pool() -> tuple[Any, Any]:
    """한글 주석 — asyncmy pool + cursor mock 의 표준 builder."""

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


class _FakeRequest:
    """aiohttp.web.Request minimal mock — req.get(key, default) + req.app +
    req.headers + req.remote + req.content_length + req.json() 의무.
    """

    def __init__(
        self,
        *,
        db_pool: Any = None,
        user_id: int = 42,
        body: dict[str, Any] | None = None,
        xff: str = "",
        remote: str = "10.0.0.1",
        ua: str = "TooTalk/0.4.0",
    ) -> None:
        self._app: dict[str, Any] = {"db_pool": db_pool}
        self._body = body or {}
        self._user_id = user_id
        self._xff = xff
        self._remote_ip = remote
        self._ua = ua
        # 한글 주석: content_length — body 부재 시 0 의무 (handler 의 if content_length 분기)
        self.content_length = len(json.dumps(self._body)) if self._body else 0

    @property
    def app(self) -> dict[str, Any]:
        return self._app

    @property
    def headers(self) -> Any:
        class _H:
            def __init__(self, xff: str, ua: str) -> None:
                self._data = {"X-Forwarded-For": xff, "User-Agent": ua}

            def get(self, key: str, default: str = "") -> str:
                return self._data.get(key, default)

        return _H(self._xff, self._ua)

    @property
    def remote(self) -> str:
        return self._remote_ip

    def get(self, key: str, default: Any = None) -> Any:
        """한글 주석 — aiohttp request 의 dict-style get (middleware 주입 키)."""
        if key == "user_id":
            return self._user_id
        return default

    async def json(self) -> dict[str, Any]:
        return self._body


class TestRemoteRequest:
    """REMOTE_REQUEST audit + skeleton 응답 검증."""

    @pytest.mark.asyncio
    async def test_pool_present_inserts_audit_row(self) -> None:
        # 한글 주석: pool 가용 시 INSERT user_activity_log + action=remote_request
        pool, cursor = _mock_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=42,
            body={"target_user_id": 99, "pattern": "help"},
            xff="203.0.113.5",
        )
        resp = await handle_remote_request(req)  # type: ignore[arg-type]
        assert resp.status == 200

        # SQL + params 검증
        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42  # user_id (requester)
        assert params[1] == ActivityAction.REMOTE_REQUEST.value  # "remote_request"
        assert params[2] == 99  # target_id = target_user_id
        assert params[3] == "203.0.113.5"  # ip_address
        # metadata JSON = {"pattern": "help"}
        meta = json.loads(params[5])
        assert meta == {"pattern": "help"}

    @pytest.mark.asyncio
    async def test_pool_none_graceful_skip(self) -> None:
        # 한글 주석: pool 부재 — audit 미호출 + endpoint 200 유지
        req = _FakeRequest(
            db_pool=None,
            user_id=42,
            body={"target_user_id": 99, "pattern": "control"},
        )
        resp = await handle_remote_request(req)  # type: ignore[arg-type]
        assert resp.status == 200


class TestRemoteGrant:
    """REMOTE_GRANT audit + skeleton 응답 검증."""

    @pytest.mark.asyncio
    async def test_pool_present_inserts_audit_row(self) -> None:
        # 한글 주석: pool 가용 + grant action params 정합
        pool, cursor = _mock_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=99,
            body={"request_id": 7, "requester_user_id": 42},
        )
        resp = await handle_remote_grant(req)  # type: ignore[arg-type]
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 99  # user_id (granter = target)
        assert params[1] == ActivityAction.REMOTE_GRANT.value  # "remote_grant"
        assert params[2] == 42  # target_id = requester_user_id
        meta = json.loads(params[5])
        assert meta == {"request_id": 7}

    @pytest.mark.asyncio
    async def test_pool_none_graceful_skip(self) -> None:
        req = _FakeRequest(
            db_pool=None,
            user_id=99,
            body={"request_id": 7, "requester_user_id": 42},
        )
        resp = await handle_remote_grant(req)  # type: ignore[arg-type]
        assert resp.status == 200


class TestRemoteRevoke:
    """REMOTE_REVOKE audit + skeleton 응답 검증."""

    @pytest.mark.asyncio
    async def test_pool_present_inserts_audit_row(self) -> None:
        # 한글 주석: pool 가용 + revoke action params 정합
        pool, cursor = _mock_pool()
        req = _FakeRequest(
            db_pool=pool,
            user_id=42,
            body={"session_id": 13, "target_user_id": 99},
        )
        resp = await handle_remote_revoke(req)  # type: ignore[arg-type]
        assert resp.status == 200

        sql_calls = [c.args for c in cursor.execute.call_args_list]
        insert_call = next(
            (c for c in sql_calls if "INSERT INTO user_activity_log" in c[0]),
            None,
        )
        assert insert_call is not None
        params = insert_call[1]
        assert params[0] == 42  # user_id (revoker)
        assert params[1] == ActivityAction.REMOTE_REVOKE.value  # "remote_revoke"
        assert params[2] == 99  # target_id = target_user_id
        meta = json.loads(params[5])
        assert meta == {"session_id": 13}

    @pytest.mark.asyncio
    async def test_pool_none_graceful_skip(self) -> None:
        req = _FakeRequest(
            db_pool=None,
            user_id=42,
            body={"session_id": 13, "target_user_id": 99},
        )
        resp = await handle_remote_revoke(req)  # type: ignore[arg-type]
        assert resp.status == 200
