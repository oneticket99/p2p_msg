# SPDX-License-Identifier: GPL-3.0-or-later
"""Phase 4 cycle 119 — auth_handlers actual DB audit wiring 검증.

_audit + _create_session_row helper 의 pool 부재 graceful skip + log_activity
호출 + create_session 호출 + extract_client_ip 정합 + audit log warning
on exception.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.api.auth_handlers import _audit, _create_session_row
from server.db.repositories.user_activity import ActivityAction


class _FakeRequest:
    """aiohttp.web.Request minimal mock."""

    def __init__(
        self,
        *,
        db_pool: Any = None,
        xff: str = "",
        remote: str = "10.0.0.1",
        ua: str = "TooTalk/0.4.0",
    ) -> None:
        self._app: dict[str, Any] = {"db_pool": db_pool, "session_store": {}}
        self._xff = xff
        self._remote = remote
        self._ua = ua

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
        return self._remote


def _mock_pool(*, lastrowid: int = 1) -> Any:
    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = lastrowid
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


class TestAuditPoolAbsent:
    """pool None 시 graceful skip — endpoint 응답 영향 부재."""

    @pytest.mark.asyncio
    async def test_audit_pool_none_skips(self) -> None:
        req = _FakeRequest(db_pool=None)
        # 한글 주석: pool 부재 — raise 부재 + 정상 return
        await _audit(req, user_id=1, action=ActivityAction.LOGIN)

    @pytest.mark.asyncio
    async def test_create_session_pool_none_skips(self) -> None:
        req = _FakeRequest(db_pool=None)
        await _create_session_row(req, user_id=1, token="dummy-token")


class TestAuditPoolPresent:
    """pool 가용 시 log_activity SQL 호출 검증."""

    @pytest.mark.asyncio
    async def test_signup_audit_calls_insert(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool, xff="203.0.113.5", ua="TooTalk/0.4.0")
        await _audit(req, user_id=42, action=ActivityAction.SIGNUP)
        # 한글 주석: 첫 호출 = INSERT user_activity_log
        first_sql, params = cursor.execute.call_args_list[0].args
        assert "INSERT INTO user_activity_log" in first_sql
        assert params[0] == 42  # user_id
        assert params[1] == "signup"  # action
        assert params[3] == "203.0.113.5"  # ip_address (XFF)
        assert params[4] == "TooTalk/0.4.0"  # user_agent

    @pytest.mark.asyncio
    async def test_xff_chain_picks_first(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(
            db_pool=pool,
            xff="1.2.3.4, 10.0.0.1, 172.16.0.1",
        )
        await _audit(req, user_id=1, action=ActivityAction.LOGIN)
        params = cursor.execute.call_args_list[0].args[1]
        assert params[3] == "1.2.3.4"

    @pytest.mark.asyncio
    async def test_xff_empty_fallback_to_remote(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool, xff="", remote="192.0.2.5")
        await _audit(req, user_id=1, action=ActivityAction.LOGIN)
        params = cursor.execute.call_args_list[0].args[1]
        assert params[3] == "192.0.2.5"

    @pytest.mark.asyncio
    async def test_user_agent_truncated_to_255(self) -> None:
        pool, cursor = _mock_pool()
        long_ua = "X" * 500
        req = _FakeRequest(db_pool=pool, ua=long_ua)
        await _audit(req, user_id=1, action=ActivityAction.LOGIN)
        params = cursor.execute.call_args_list[0].args[1]
        assert len(params[4]) == 255

    @pytest.mark.asyncio
    async def test_metadata_passed_through(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool)
        await _audit(
            req,
            user_id=1,
            action=ActivityAction.BOT_CHAT,
            metadata={"provider": "anthropic", "tokens": 128},
        )
        params = cursor.execute.call_args_list[0].args[1]
        # 한글 주석: metadata_json (idx 5) JSON serialize
        import json

        assert json.loads(params[5]) == {"provider": "anthropic", "tokens": 128}


class TestCreateSessionRow:
    """create_session row 의 token hash + IP + UA 의 capture 검증."""

    @pytest.mark.asyncio
    async def test_token_sha256_hashed(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool, xff="203.0.113.10")
        await _create_session_row(req, user_id=42, token="my-secret-token-abc")
        # INSERT user_sessions
        first_sql, params = cursor.execute.call_args_list[0].args
        assert "INSERT INTO user_sessions" in first_sql
        assert params[0] == 42  # user_id
        # 한글 주석: token_hash = SHA-256 hex 64자
        assert len(params[1]) == 64
        # 한글 주석: 실 값 = SHA-256("my-secret-token-abc")
        import hashlib

        expected = hashlib.sha256(b"my-secret-token-abc").hexdigest()
        assert params[1] == expected
        # IP + UA
        assert params[2] == "203.0.113.10"

    @pytest.mark.asyncio
    async def test_empty_xff_uses_remote(self) -> None:
        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool, xff="", remote="192.0.2.99")
        await _create_session_row(req, user_id=1, token="t")
        params = cursor.execute.call_args_list[0].args[1]
        assert params[2] == "192.0.2.99"


class TestAuditGracefulException:
    """log_activity 가 raise 해도 endpoint 영향 부재 (warning log 만)."""

    @pytest.mark.asyncio
    async def test_pool_raises_swallowed(self) -> None:
        pool = MagicMock()

        @asynccontextmanager
        async def bad_acquire() -> Any:
            raise RuntimeError("DB down")
            yield  # noqa: unreachable

        pool.acquire = lambda: bad_acquire()
        req = _FakeRequest(db_pool=pool)
        # 한글 주석: raise 부재 의무
        await _audit(req, user_id=1, action=ActivityAction.LOGIN)


class TestLogoutEndpoint:
    """cycle 121 — handle_logout audit + close_session + session_store 제거."""

    @pytest.mark.asyncio
    async def test_logout_pool_none_succeeds(self) -> None:
        from server.api.auth_handlers import handle_logout

        req = _FakeRequest(db_pool=None)
        req._app["session_store"] = {"test-token-xyz": 42}
        # 한글 주석: aiohttp 의 request scope dict-like
        req._user_id = 42
        req._token = "test-token-xyz"
        # __getitem__ + get
        original_get = req._app.get

        def get_attr(key: str, default: Any = None) -> Any:
            return {"user_id": 42, "session_token": "test-token-xyz"}.get(key, default)

        req.get = get_attr  # type: ignore[attr-defined]

        response = await handle_logout(req)  # type: ignore[arg-type]
        # session_store 제거 검증
        assert "test-token-xyz" not in req._app["session_store"]
        # response 200 + ok
        import json

        body = json.loads(response.body.decode("utf-8"))
        assert body["ok"] is True

    @pytest.mark.asyncio
    async def test_logout_pool_present_close_session_called(self) -> None:
        from server.api.auth_handlers import handle_logout

        pool, cursor = _mock_pool()
        req = _FakeRequest(db_pool=pool)
        req._app["session_store"] = {"tok-abc": 7}

        def get_attr(key: str, default: Any = None) -> Any:
            return {"user_id": 7, "session_token": "tok-abc"}.get(key, default)

        req.get = get_attr  # type: ignore[attr-defined]
        await handle_logout(req)  # type: ignore[arg-type]
        # 한글 주석: close_session UPDATE + log_activity INSERT 호출 검증
        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        assert any("UPDATE user_sessions" in s and "end_reason" in s for s in sql_calls)
        assert any("INSERT INTO user_activity_log" in s for s in sql_calls)

    @pytest.mark.asyncio
    async def test_logout_missing_token_unauthorized(self) -> None:
        from aiohttp import web as _web

        from server.api.auth_handlers import handle_logout

        req = _FakeRequest(db_pool=None)

        def get_attr(key: str, default: Any = None) -> Any:
            return None

        req.get = get_attr  # type: ignore[attr-defined]
        with pytest.raises(_web.HTTPUnauthorized):
            await handle_logout(req)  # type: ignore[arg-type]
