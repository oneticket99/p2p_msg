# SPDX-License-Identifier: GPL-3.0-or-later
"""read_states repository unit — cycle 169.752 신설.

읽음 상태 추적 — upsert_last_read(역행 차단) / get_last_read / batch / unread_counts.
mock async pool 로 asyncmy 우회.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None) -> MagicMock:
    # 한글 주석 — acquire + cursor 2단 async context 모킹
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
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


class TestUpsertLastRead:
    @pytest.mark.asyncio
    async def test_zero_user_raises(self) -> None:
        from server.db.repositories.read_states import upsert_last_read

        with pytest.raises(ValueError, match="양수"):
            await upsert_last_read(None, user_id=0, room_id=1, last_read_msg_id=5)

    @pytest.mark.asyncio
    async def test_zero_room_raises(self) -> None:
        from server.db.repositories.read_states import upsert_last_read

        with pytest.raises(ValueError, match="양수"):
            await upsert_last_read(None, user_id=1, room_id=0, last_read_msg_id=5)

    @pytest.mark.asyncio
    async def test_negative_msg_id_raises(self) -> None:
        from server.db.repositories.read_states import upsert_last_read

        with pytest.raises(ValueError, match="음수"):
            await upsert_last_read(None, user_id=1, room_id=1, last_read_msg_id=-1)

    @pytest.mark.asyncio
    async def test_valid_commits(self) -> None:
        from server.db.repositories.read_states import upsert_last_read

        pool = _build_pool()
        await upsert_last_read(pool, user_id=10, room_id=100, last_read_msg_id=42)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()


class TestGetLastRead:
    @pytest.mark.asyncio
    async def test_row_found(self) -> None:
        from server.db.repositories.read_states import get_last_read

        pool = _build_pool(fetchone=(77,))
        assert await get_last_read(pool, user_id=10, room_id=100) == 77

    @pytest.mark.asyncio
    async def test_row_missing_returns_zero(self) -> None:
        from server.db.repositories.read_states import get_last_read

        pool = _build_pool(fetchone=None)
        assert await get_last_read(pool, user_id=10, room_id=999) == 0


class TestGetLastReadBatch:
    @pytest.mark.asyncio
    async def test_empty_room_ids_returns_empty(self) -> None:
        from server.db.repositories.read_states import get_last_read_batch

        assert await get_last_read_batch(None, user_id=10, room_ids=[]) == {}

    @pytest.mark.asyncio
    async def test_merges_rows_over_default_zero(self) -> None:
        from server.db.repositories.read_states import get_last_read_batch

        # 한글 주석 — room 1=50, room 2 부재(default 0), room 3=10
        pool = _build_pool(fetchall=[(1, 50), (3, 10)])
        out = await get_last_read_batch(pool, user_id=10, room_ids=[1, 2, 3])
        assert out == {1: 50, 2: 0, 3: 10}


class TestGetUnreadCounts:
    @pytest.mark.asyncio
    async def test_empty_room_ids_returns_empty(self) -> None:
        from server.db.repositories.read_states import get_unread_counts

        assert await get_unread_counts(None, user_id=10, room_ids=[]) == {}

    @pytest.mark.asyncio
    async def test_merges_unread_over_default_zero(self) -> None:
        from server.db.repositories.read_states import get_unread_counts

        pool = _build_pool(fetchall=[(1, 3)])
        out = await get_unread_counts(pool, user_id=10, room_ids=[1, 2])
        assert out == {1: 3, 2: 0}
