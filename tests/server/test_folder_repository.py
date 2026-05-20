# SPDX-License-Identifier: GPL-3.0-or-later
"""folders repository unit test (cycle 169.80 신설 — MED-3 회수)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from server.db.repositories.folders import (
    add_folder_chat,
    create_invite,
    delete_folder,
    fetch_by_folder_id_and_owner,
    insert_folder,
    insert_folder_with_chats,
    list_folders,
)


def _make_pool_mock(fetch_one=None, fetch_all=None, lastrowid=1, rowcount=1):
    """asyncmy pool + cursor + conn mock factory."""
    cur = AsyncMock()
    cur.fetchone = AsyncMock(return_value=fetch_one)
    cur.fetchall = AsyncMock(return_value=fetch_all or [])
    cur.execute = AsyncMock()
    cur.lastrowid = lastrowid
    cur.rowcount = rowcount

    conn = MagicMock()
    conn.cursor = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=cur), __aexit__=AsyncMock()))
    conn.commit = AsyncMock()
    conn.rollback = AsyncMock()
    conn.begin = AsyncMock()

    pool = MagicMock()
    pool.acquire = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=conn), __aexit__=AsyncMock()))
    return pool, conn, cur


class TestFoldersRepository:

    @pytest.mark.asyncio
    async def test_insert_folder_basic(self) -> None:
        pool, conn, cur = _make_pool_mock(lastrowid=42)
        result = await insert_folder(
            pool, folder_id="abc12345", owner_id=1, name="My Folder",
            color_name="blue", color_hex="#3b82f6",
        )
        assert result == 42
        cur.execute.assert_awaited_once()
        conn.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_list_folders_empty(self) -> None:
        pool, conn, cur = _make_pool_mock(fetch_all=[])
        result = await list_folders(pool, owner_id=1)
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_folder_returns_true_on_affected(self) -> None:
        pool, conn, cur = _make_pool_mock(rowcount=1)
        ok = await delete_folder(pool, "abc12345", owner_id=1)
        assert ok is True

    @pytest.mark.asyncio
    async def test_delete_folder_returns_false_on_zero_rows(self) -> None:
        pool, conn, cur = _make_pool_mock(rowcount=0)
        ok = await delete_folder(pool, "noexist", owner_id=1)
        assert ok is False

    @pytest.mark.asyncio
    async def test_fetch_by_folder_id_and_owner_none(self) -> None:
        pool, conn, cur = _make_pool_mock(fetch_one=None)
        result = await fetch_by_folder_id_and_owner(pool, "abc12345", 1)
        assert result is None

    @pytest.mark.asyncio
    async def test_create_invite_secrets_token(self) -> None:
        pool, conn, cur = _make_pool_mock()
        token = await create_invite(pool, folder_pk=42, created_by=1)
        # secrets.token_hex(16) = 32 char hex
        assert len(token) == 32
        assert all(c in "0123456789abcdef" for c in token)

    @pytest.mark.asyncio
    async def test_insert_folder_with_chats_atomic_commit(self) -> None:
        pool, conn, cur = _make_pool_mock(lastrowid=100)
        included = [{"kind": "room", "target_id": 1}, {"kind": "friend", "target_id": 2}]
        excluded = [{"kind": "bot", "target_id": 3}]
        new_id = await insert_folder_with_chats(
            pool, folder_id="aggregate", owner_id=1, name="Aggregate",
            color_name="blue", color_hex="#3b82f6",
            included_chats=included, excluded_chats=excluded,
        )
        assert new_id == 100
        conn.commit.assert_awaited_once()
        # folders INSERT 1회 + folder_chats INSERT 3회
        assert cur.execute.await_count == 4

    @pytest.mark.skip(reason="cycle 169.80 — mock cursor reuse + side_effect chain 회수 별도 cycle (실 DB integration 의무)")
    @pytest.mark.asyncio
    async def test_insert_folder_with_chats_rollback_on_exception(self) -> None:
        pass
