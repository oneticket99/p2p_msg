# SPDX-License-Identifier: GPL-3.0-or-later
"""users repository methods unit — cycle 169.721 신설.

get_user_by_email + get_user_by_username + mark_email_verified + update_last_login.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(fetchone_row=None, lastrowid: int = 1) -> MagicMock:
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=fetchone_row)
    cur.lastrowid = lastrowid

    cur_ctx = MagicMock()
    cur_ctx.__aenter__ = AsyncMock(return_value=cur)
    cur_ctx.__aexit__ = AsyncMock(return_value=None)

    conn = MagicMock()
    conn.cursor = MagicMock(return_value=cur_ctx)
    conn.commit = AsyncMock(return_value=None)

    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)

    pool.acquire = MagicMock(return_value=conn_ctx)
    return pool


def _row_tuple() -> tuple:
    return (
        1, "x@x.com", "alice", "hash$abc", 1, "active",
        datetime(2026, 5, 24, tzinfo=timezone.utc),
        datetime(2026, 5, 24, tzinfo=timezone.utc),
        None,
    )


class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_returns_user(self) -> None:
        from server.db.repositories.users import get_user_by_email

        pool = _build_pool(fetchone_row=_row_tuple())
        u = await get_user_by_email(pool, "X@X.com")
        assert u is not None
        assert u.email == "x@x.com"
        assert u.username == "alice"

    @pytest.mark.asyncio
    async def test_missing_returns_none(self) -> None:
        from server.db.repositories.users import get_user_by_email

        pool = _build_pool(fetchone_row=None)
        u = await get_user_by_email(pool, "ghost@x.com")
        assert u is None


class TestGetUserByUsername:
    @pytest.mark.asyncio
    async def test_returns_user(self) -> None:
        from server.db.repositories.users import get_user_by_username

        pool = _build_pool(fetchone_row=_row_tuple())
        u = await get_user_by_username(pool, "alice")
        assert u is not None
        assert u.username == "alice"

    @pytest.mark.asyncio
    async def test_missing_returns_none(self) -> None:
        from server.db.repositories.users import get_user_by_username

        pool = _build_pool(fetchone_row=None)
        u = await get_user_by_username(pool, "ghost")
        assert u is None


class TestMarkEmailVerified:
    @pytest.mark.asyncio
    async def test_dispatches(self) -> None:
        from server.db.repositories.users import mark_email_verified

        pool = _build_pool()
        # 한글 주석 — return None + exception 부재
        await mark_email_verified(pool, user_id=10)


class TestUpdateLastLogin:
    @pytest.mark.asyncio
    async def test_dispatches(self) -> None:
        from server.db.repositories.users import update_last_login

        pool = _build_pool()
        await update_last_login(pool, user_id=10)


class TestUpdatePassword:
    @pytest.mark.asyncio
    async def test_dispatches(self) -> None:
        from server.db.repositories.users import update_password

        pool = _build_pool()
        await update_password(pool, user_id=10, new_hash="new$hash")
