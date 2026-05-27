# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.db.repositories.user_activity`` 의 단위 테스트.

ActivityAction + SessionEndReason ENUM 정합 + log_activity / create_session /
update_session_last_active / close_session 의 input validation + mock pool 의
SQL parameter assertion.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from server.db.repositories.user_activity import (
    ActivityAction,
    SessionEndReason,
    close_session,
    create_session,
    log_activity,
    update_session_last_active,
)


def _mock_pool(*, lastrowid: int = 42, rowcount: int = 1) -> Any:
    """asyncmy pool + conn + cursor mock — execute spy + lastrowid stub."""

    cursor = MagicMock()
    cursor.execute = AsyncMock()
    cursor.lastrowid = lastrowid
    cursor.rowcount = rowcount

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
    return pool, conn, cursor


class TestActivityAction:
    def test_29_actions_defined(self) -> None:
        # cycle 169.586: cycle 144 ENUM 28 → 29 추가 (cycle 169.x 신규 1건 정합).
        actions = [a.value for a in ActivityAction]
        assert len(actions) == 29, f"ENUM count = {len(actions)}, expect 29"
        assert "signup" in actions
        assert "login" in actions
        assert "bot_chat" in actions
        assert "remote_request" in actions
        assert "remote_grant" in actions
        assert "remote_revoke" in actions
        assert "account_delete" in actions
        assert "bot_escalate" in actions
        assert "room_create" in actions
        assert "room_close" in actions
        assert "message_send" in actions


class TestSessionEndReason:
    def test_5_reasons_defined(self) -> None:
        reasons = [r.value for r in SessionEndReason]
        assert reasons == [
            "logout",
            "idle_timeout",
            "token_revoke",
            "force_disconnect",
            "server_restart",
        ]


class TestLogActivityValidation:
    @pytest.mark.asyncio
    async def test_none_pool_raises(self) -> None:
        with pytest.raises(ValueError, match="pool"):
            await log_activity(None, user_id=1, action=ActivityAction.LOGIN)

    @pytest.mark.asyncio
    async def test_zero_user_id_raises(self) -> None:
        pool, _, _ = _mock_pool()
        with pytest.raises(ValueError, match="user_id 양수"):
            await log_activity(pool, user_id=0, action=ActivityAction.LOGIN)

    @pytest.mark.asyncio
    async def test_negative_user_id_raises(self) -> None:
        pool, _, _ = _mock_pool()
        with pytest.raises(ValueError, match="user_id 양수"):
            await log_activity(pool, user_id=-1, action=ActivityAction.LOGIN)


class TestLogActivityExecution:
    @pytest.mark.asyncio
    async def test_minimal_inserts_action_row(self) -> None:
        pool, conn, cursor = _mock_pool(lastrowid=101)
        new_id = await log_activity(
            pool,
            user_id=42,
            action=ActivityAction.LOGIN,
            ip_address="1.2.3.4",
        )
        assert new_id == 101
        # 첫 호출 = INSERT user_activity_log
        first_call = cursor.execute.call_args_list[0]
        sql, params = first_call.args
        assert "INSERT INTO user_activity_log" in sql
        assert params[0] == 42  # user_id
        assert params[1] == "login"  # action.value
        assert params[3] == "1.2.3.4"  # ip_address
        # 두 번째 호출 = UPDATE users.last_activity_at
        second_call = cursor.execute.call_args_list[1]
        sql2, params2 = second_call.args
        assert "UPDATE users" in sql2
        assert params2 == (42,)
        # commit 호출
        conn.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_metadata_json_serialized(self) -> None:
        pool, _, cursor = _mock_pool()
        await log_activity(
            pool,
            user_id=1,
            action=ActivityAction.BOT_CHAT,
            metadata={"provider": "anthropic", "tokens": 128},
        )
        params = cursor.execute.call_args_list[0].args[1]
        # metadata_json (params[5]) 의 JSON parse + 정합 검증
        meta = json.loads(params[5])
        assert meta == {"provider": "anthropic", "tokens": 128}

    @pytest.mark.asyncio
    async def test_no_metadata_passes_none(self) -> None:
        pool, _, cursor = _mock_pool()
        await log_activity(pool, user_id=1, action=ActivityAction.LOGIN)
        params = cursor.execute.call_args_list[0].args[1]
        assert params[5] is None


class TestCreateSessionValidation:
    @pytest.mark.asyncio
    async def test_none_pool_raises(self) -> None:
        with pytest.raises(ValueError, match="pool"):
            await create_session(
                None,
                user_id=1,
                session_token_hash="a" * 64,
                ip_address="1.1.1.1",
            )

    @pytest.mark.asyncio
    async def test_invalid_token_length_raises(self) -> None:
        pool, _, _ = _mock_pool()
        with pytest.raises(ValueError, match="64자 SHA-256"):
            await create_session(
                pool,
                user_id=1,
                session_token_hash="short",
                ip_address="1.1.1.1",
            )

    @pytest.mark.asyncio
    async def test_empty_ip_raises(self) -> None:
        pool, _, _ = _mock_pool()
        with pytest.raises(ValueError, match="ip_address"):
            await create_session(
                pool,
                user_id=1,
                session_token_hash="b" * 64,
                ip_address="",
            )


class TestCreateSessionExecution:
    @pytest.mark.asyncio
    async def test_inserts_session_and_updates_last_login(self) -> None:
        pool, conn, cursor = _mock_pool(lastrowid=777)
        new_id = await create_session(
            pool,
            user_id=42,
            session_token_hash="c" * 64,
            ip_address="203.0.113.10",
            user_agent="TooTalk/0.3.0",
        )
        assert new_id == 777
        # 첫 호출 = INSERT user_sessions
        first_sql, first_params = cursor.execute.call_args_list[0].args
        assert "INSERT INTO user_sessions" in first_sql
        assert first_params == (42, "c" * 64, "203.0.113.10", "TooTalk/0.3.0")
        # 두 번째 호출 = UPDATE users (last_login_at + last_login_ip)
        second_sql, second_params = cursor.execute.call_args_list[1].args
        assert "last_login_at" in second_sql
        assert "last_login_ip" in second_sql
        assert second_params == ("203.0.113.10", 42)


class TestUpdateSessionLastActive:
    @pytest.mark.asyncio
    async def test_updates_active_session(self) -> None:
        pool, conn, cursor = _mock_pool(rowcount=1)
        affected = await update_session_last_active(
            pool, session_token_hash="d" * 64
        )
        assert affected == 1
        sql, params = cursor.execute.call_args_list[0].args
        assert "UPDATE user_sessions" in sql
        assert "disconnected_at IS NULL" in sql
        assert params == ("d" * 64,)

    @pytest.mark.asyncio
    async def test_empty_token_raises(self) -> None:
        pool, _, _ = _mock_pool()
        with pytest.raises(ValueError, match="session_token_hash"):
            await update_session_last_active(pool, session_token_hash="")


class TestCloseSession:
    @pytest.mark.asyncio
    async def test_close_with_end_reason(self) -> None:
        pool, _, cursor = _mock_pool(rowcount=1)
        affected = await close_session(
            pool,
            session_token_hash="e" * 64,
            end_reason=SessionEndReason.LOGOUT,
        )
        assert affected == 1
        sql, params = cursor.execute.call_args_list[0].args
        assert "disconnected_at" in sql
        assert "TIMESTAMPDIFF" in sql
        assert "end_reason" in sql
        assert params == ("logout", "e" * 64)

    @pytest.mark.asyncio
    async def test_close_idle_timeout(self) -> None:
        pool, _, cursor = _mock_pool()
        await close_session(
            pool,
            session_token_hash="f" * 64,
            end_reason=SessionEndReason.IDLE_TIMEOUT,
        )
        params = cursor.execute.call_args_list[0].args[1]
        assert params[0] == "idle_timeout"
