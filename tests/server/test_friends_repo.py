# SPDX-License-Identifier: GPL-3.0-or-later
"""friends repository unit — cycle 169.756 신설.

친구 관계 insert/lookup/list/pending/accept/status/delete/search/nickname.
mock async pool 로 asyncmy 우회.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1) -> MagicMock:
    # acquire + cursor 2단 async context 모킹
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


_TS = datetime(2026, 5, 24, tzinfo=timezone.utc)
# FriendRow 7-tuple
_FRIEND_ROW = (1, 10, 20, "accepted", "친구별명", _TS, _TS)
# FriendWithProfile 9-tuple (+ username + email_verified)
_PROFILE_ROW = (1, 10, 20, "pending", None, _TS, None, "peer_user", 1)
# search 5-tuple (id/username/display_name/nickname/email_verified)
_SEARCH_ROW = (20, "peer_user", "피어", "별명", 1)


class TestInsertGetFriend:
    @pytest.mark.asyncio
    async def test_insert_returns_id(self) -> None:
        from server.db.repositories.friends import insert_friend

        assert await insert_friend(_build_pool(lastrowid=8),
                                   user_id=10, friend_user_id=20) == 8

    @pytest.mark.asyncio
    async def test_get_friend_found(self) -> None:
        from server.db.repositories.friends import FriendRow, get_friend

        row = await get_friend(_build_pool(fetchone=_FRIEND_ROW), user_id=10, friend_user_id=20)
        assert isinstance(row, FriendRow)
        assert row.status == "accepted" and row.nickname == "친구별명"

    @pytest.mark.asyncio
    async def test_get_friend_missing_none(self) -> None:
        from server.db.repositories.friends import get_friend

        assert await get_friend(_build_pool(fetchone=None), user_id=10, friend_user_id=99) is None


class TestListFriends:
    @pytest.mark.asyncio
    async def test_list_by_user(self) -> None:
        from server.db.repositories.friends import FriendWithProfile, list_by_user

        rows = await list_by_user(_build_pool(fetchall=[_PROFILE_ROW]), 10)
        assert len(rows) == 1
        assert isinstance(rows[0], FriendWithProfile)
        assert rows[0].friend_username == "peer_user"

    @pytest.mark.asyncio
    async def test_list_pending_requests(self) -> None:
        from server.db.repositories.friends import list_pending_requests

        rows = await list_pending_requests(_build_pool(fetchall=[_PROFILE_ROW, _PROFILE_ROW]), 10)
        assert len(rows) == 2


class TestStatusMutate:
    @pytest.mark.asyncio
    async def test_accept_friend_rowcount(self) -> None:
        from server.db.repositories.friends import accept_friend

        assert await accept_friend(_build_pool(rowcount=1), user_id=10, friend_user_id=20) == 1

    @pytest.mark.asyncio
    async def test_update_status_invalid_raises(self) -> None:
        from server.db.repositories.friends import update_status

        with pytest.raises(ValueError, match="invalid status"):
            await update_status(_build_pool(), user_id=10, friend_user_id=20, new_status="bogus")

    @pytest.mark.asyncio
    async def test_update_status_valid_rowcount(self) -> None:
        from server.db.repositories.friends import update_status

        n = await update_status(_build_pool(rowcount=1),
                                user_id=10, friend_user_id=20, new_status="blocked")
        assert n == 1

    @pytest.mark.asyncio
    async def test_delete_friend_rowcount(self) -> None:
        from server.db.repositories.friends import delete_friend

        assert await delete_friend(_build_pool(rowcount=1), user_id=10, friend_user_id=20) == 1

    @pytest.mark.asyncio
    async def test_set_nickname_rowcount(self) -> None:
        from server.db.repositories.friends import set_nickname

        n = await set_nickname(_build_pool(rowcount=1),
                               user_id=10, friend_user_id=20, nickname="새별명")
        assert n == 1

    @pytest.mark.asyncio
    async def test_set_nickname_null_removes(self) -> None:
        from server.db.repositories.friends import set_nickname

        n = await set_nickname(_build_pool(rowcount=1),
                               user_id=10, friend_user_id=20, nickname=None)
        assert n == 1


class TestSearchUsers:
    @pytest.mark.asyncio
    async def test_search_returns_dict_list(self) -> None:
        from server.db.repositories.friends import search_users_by_username

        out = await search_users_by_username(_build_pool(fetchall=[_SEARCH_ROW]), keyword="피어")
        assert out == [{
            "id": 20, "username": "peer_user", "display_name": "피어",
            "nickname": "별명", "email_verified": True,
        }]

    @pytest.mark.asyncio
    async def test_search_empty(self) -> None:
        from server.db.repositories.friends import search_users_by_username

        assert await search_users_by_username(_build_pool(fetchall=[]), keyword="없음") == []
