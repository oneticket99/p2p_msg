# SPDX-License-Identifier: GPL-3.0-or-later
"""messages repository unit — cycle 169.753 신설.

insert(generic/text/file/system) + get_by_id + list_by_room + count + delete +
soft_delete + list_recent + list_messages_in_range. validation + mock async pool.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1) -> MagicMock:
    # 한글 주석 — acquire + cursor 2단 async context 모킹
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


# 한글 주석 — messages SELECT 7-tuple 정합 (id/room/sender/kind/body/file_id/created_at)
_MSG_ROW = (5, 100, 10, "text", "hello", None,
            datetime(2026, 5, 24, tzinfo=timezone.utc))


class TestInsertMessageValidation:
    @pytest.mark.asyncio
    async def test_pool_none_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="pool"):
            await insert_message(None, room_id=1, sender_id=1, kind="text", body="x")

    @pytest.mark.asyncio
    async def test_zero_room_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="room_id"):
            await insert_message(_build_pool(), room_id=0, sender_id=1, kind="text", body="x")

    @pytest.mark.asyncio
    async def test_zero_sender_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="sender_id"):
            await insert_message(_build_pool(), room_id=1, sender_id=0, kind="text", body="x")

    @pytest.mark.asyncio
    async def test_invalid_kind_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="kind"):
            await insert_message(_build_pool(), room_id=1, sender_id=1, kind="bogus", body="x")

    @pytest.mark.asyncio
    async def test_text_without_body_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="body"):
            await insert_message(_build_pool(), room_id=1, sender_id=1, kind="text")

    @pytest.mark.asyncio
    async def test_file_without_file_id_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="file_id"):
            await insert_message(_build_pool(), room_id=1, sender_id=1, kind="file")

    @pytest.mark.asyncio
    async def test_system_without_body_raises(self) -> None:
        from server.db.repositories.messages import insert_message

        with pytest.raises(ValueError, match="body"):
            await insert_message(_build_pool(), room_id=1, sender_id=1, kind="system")

    @pytest.mark.asyncio
    async def test_valid_returns_lastrowid(self) -> None:
        from server.db.repositories.messages import insert_message

        pool = _build_pool(lastrowid=88)
        new_id = await insert_message(pool, room_id=1, sender_id=1, kind="text", body="hi")
        assert new_id == 88


class TestInsertVariants:
    @pytest.mark.asyncio
    async def test_insert_text(self) -> None:
        from server.db.repositories.messages import insert_text_message

        assert await insert_text_message(_build_pool(lastrowid=3),
                                         room_id=1, sender_id=2, body="t") == 3

    @pytest.mark.asyncio
    async def test_insert_file(self) -> None:
        from server.db.repositories.messages import insert_file_message

        assert await insert_file_message(_build_pool(lastrowid=4),
                                         room_id=1, sender_id=2, file_id="f" * 32) == 4

    @pytest.mark.asyncio
    async def test_insert_system(self) -> None:
        from server.db.repositories.messages import insert_system_message

        assert await insert_system_message(_build_pool(lastrowid=5),
                                           room_id=1, sender_id=2, body="joined") == 5


class TestGetById:
    @pytest.mark.asyncio
    async def test_pool_none_raises(self) -> None:
        from server.db.repositories.messages import get_by_id

        with pytest.raises(ValueError, match="pool"):
            await get_by_id(None, 1)

    @pytest.mark.asyncio
    async def test_zero_id_raises(self) -> None:
        from server.db.repositories.messages import get_by_id

        with pytest.raises(ValueError, match="message_id"):
            await get_by_id(_build_pool(), 0)

    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from server.db.repositories.messages import MessageRow, get_by_id

        row = await get_by_id(_build_pool(fetchone=_MSG_ROW), 5)
        assert isinstance(row, MessageRow)
        assert row.kind == "text" and row.body == "hello"

    @pytest.mark.asyncio
    async def test_missing_returns_none(self) -> None:
        from server.db.repositories.messages import get_by_id

        assert await get_by_id(_build_pool(fetchone=None), 999) is None


class TestListByRoom:
    @pytest.mark.asyncio
    async def test_limit_over_500_raises(self) -> None:
        from server.db.repositories.messages import list_by_room

        with pytest.raises(ValueError, match="limit"):
            await list_by_room(_build_pool(), room_id=1, limit=501)

    @pytest.mark.asyncio
    async def test_negative_offset_raises(self) -> None:
        from server.db.repositories.messages import list_by_room

        with pytest.raises(ValueError, match="offset"):
            await list_by_room(_build_pool(), room_id=1, offset=-1)

    @pytest.mark.asyncio
    async def test_returns_rows(self) -> None:
        from server.db.repositories.messages import list_by_room

        rows = await list_by_room(_build_pool(fetchall=[_MSG_ROW, _MSG_ROW]), room_id=1)
        assert len(rows) == 2


class TestCountDeleteSoft:
    @pytest.mark.asyncio
    async def test_count_by_room(self) -> None:
        from server.db.repositories.messages import count_by_room

        assert await count_by_room(_build_pool(fetchone=(7,)), 1) == 7

    @pytest.mark.asyncio
    async def test_count_none_returns_zero(self) -> None:
        from server.db.repositories.messages import count_by_room

        assert await count_by_room(_build_pool(fetchone=None), 1) == 0

    @pytest.mark.asyncio
    async def test_delete_by_id_rowcount(self) -> None:
        from server.db.repositories.messages import delete_by_id

        assert await delete_by_id(_build_pool(rowcount=1), 5) == 1

    @pytest.mark.asyncio
    async def test_soft_delete_rowcount(self) -> None:
        from server.db.repositories.messages import soft_delete

        assert await soft_delete(_build_pool(rowcount=1), 5) == 1


class TestListRecentAndRange:
    @pytest.mark.asyncio
    async def test_list_recent(self) -> None:
        from server.db.repositories.messages import list_recent

        rows = await list_recent(_build_pool(fetchall=[_MSG_ROW]), room_id=1)
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_range_end_before_start_raises(self) -> None:
        from server.db.repositories.messages import list_messages_in_range

        start = datetime(2026, 5, 24, tzinfo=timezone.utc)
        end = datetime(2026, 5, 23, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="end_ts"):
            await list_messages_in_range(_build_pool(), room_id=1, start_ts=start, end_ts=end)

    @pytest.mark.asyncio
    async def test_range_returns_rows(self) -> None:
        from server.db.repositories.messages import list_messages_in_range

        start = datetime(2026, 5, 1, tzinfo=timezone.utc)
        end = datetime(2026, 5, 24, tzinfo=timezone.utc)
        rows = await list_messages_in_range(
            _build_pool(fetchall=[_MSG_ROW]), room_id=1, start_ts=start, end_ts=end)
        assert len(rows) == 1
