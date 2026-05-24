# SPDX-License-Identifier: GPL-3.0-or-later
"""file_meta + password_reset repo unit — cycle 169.751 신설.

mock async pool (acquire + cursor 2-level async context) 으로 asyncmy 우회 검증.
file_meta = 파일 송수신 영속, password_reset = 비번 재설정 토큰 발급/검증/소진.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1) -> MagicMock:
    # 한글 주석 — asyncmy pool.acquire() → conn.cursor() 2단 async context 모킹
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=None)
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
    cur.lastrowid = lastrowid
    cur.rowcount = rowcount
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


# 한글 주석 — file_meta SELECT 컬럼 순서 정합 12-tuple
_FILE_ROW = (
    7, "a" * 32, 100, 10, "photo.png", 2048, "image/png",
    "b" * 64, "completed", None,
    datetime(2026, 5, 24, tzinfo=timezone.utc), None,
)

# 한글 주석 — password_reset SELECT 컬럼 순서 정합 6-tuple
_RESET_ROW = (
    3, 10, "c" * 64,
    datetime(2026, 5, 24, 1, 0, tzinfo=timezone.utc), None,
    datetime(2026, 5, 24, tzinfo=timezone.utc),
)


class TestFileMetaInsert:
    @pytest.mark.asyncio
    async def test_insert_returns_lastrowid(self) -> None:
        from server.db.repositories.file_meta import insert_file_meta

        pool = _build_pool(lastrowid=42)
        new_id = await insert_file_meta(
            pool, file_id="f" * 32, room_id=100, sender_id=10,
            name="doc.pdf", size=1024, mime="application/pdf", sha256="d" * 64,
        )
        assert new_id == 42

    @pytest.mark.asyncio
    async def test_insert_commits(self) -> None:
        from server.db.repositories.file_meta import insert_file_meta

        pool = _build_pool(lastrowid=1)
        await insert_file_meta(
            pool, file_id="f" * 32, room_id=1, sender_id=1,
            name="x", size=1, mime="text/plain", sha256="e" * 64,
            thumbnail_base64="dGh1bWI=",
        )
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()


class TestFileMetaStatus:
    @pytest.mark.asyncio
    async def test_mark_completed(self) -> None:
        from server.db.repositories.file_meta import mark_completed

        pool = _build_pool()
        await mark_completed(pool, "f" * 32)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_mark_failed(self) -> None:
        from server.db.repositories.file_meta import mark_failed

        pool = _build_pool()
        await mark_failed(pool, "f" * 32)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()


class TestFileMetaGet:
    @pytest.mark.asyncio
    async def test_get_by_file_id_found(self) -> None:
        from server.db.repositories.file_meta import FileMetaRow, get_by_file_id

        pool = _build_pool(fetchone=_FILE_ROW)
        row = await get_by_file_id(pool, "a" * 32)
        assert isinstance(row, FileMetaRow)
        assert row.id == 7
        assert row.status == "completed"
        assert row.mime == "image/png"

    @pytest.mark.asyncio
    async def test_get_by_file_id_missing_returns_none(self) -> None:
        from server.db.repositories.file_meta import get_by_file_id

        pool = _build_pool(fetchone=None)
        assert await get_by_file_id(pool, "z" * 32) is None


class TestPasswordResetInsert:
    @pytest.mark.asyncio
    async def test_insert_reset_token_returns_id(self) -> None:
        from server.db.repositories.password_reset import insert_reset_token

        pool = _build_pool(lastrowid=99)
        new_id = await insert_reset_token(pool, user_id=10, token_hash="h" * 64)
        assert new_id == 99

    @pytest.mark.asyncio
    async def test_insert_custom_ttl_commits(self) -> None:
        from server.db.repositories.password_reset import insert_reset_token

        pool = _build_pool(lastrowid=1)
        await insert_reset_token(pool, user_id=5, token_hash="g" * 64, ttl_seconds=600)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()


class TestPasswordResetLookup:
    @pytest.mark.asyncio
    async def test_find_active_token_found(self) -> None:
        from server.db.repositories.password_reset import ResetTokenRow, find_active_token

        pool = _build_pool(fetchone=_RESET_ROW)
        row = await find_active_token(pool, "c" * 64)
        assert isinstance(row, ResetTokenRow)
        assert row.user_id == 10
        assert row.consumed_at is None

    @pytest.mark.asyncio
    async def test_find_active_token_missing_returns_none(self) -> None:
        from server.db.repositories.password_reset import find_active_token

        pool = _build_pool(fetchone=None)
        assert await find_active_token(pool, "x" * 64) is None


class TestPasswordResetConsume:
    @pytest.mark.asyncio
    async def test_consume_token_commits(self) -> None:
        from server.db.repositories.password_reset import consume_token

        pool = _build_pool()
        await consume_token(pool, 3)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()
