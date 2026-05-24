# SPDX-License-Identifier: GPL-3.0-or-later
"""device_tokens + folders + emoji_packs repository unit — cycle 169.759 신설.

잔존 repo 3종 cov 회수 batch. mock async pool (begin/rollback/autocommit 포함).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1, execute_return=None) -> MagicMock:
    # 한글 주석 — acquire + cursor 2단 async context + transaction(begin/rollback/autocommit) 모킹
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=execute_return)
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
    conn.begin = AsyncMock(return_value=None)
    conn.rollback = AsyncMock(return_value=None)
    conn.autocommit = AsyncMock(return_value=None)
    conn_ctx = MagicMock()
    conn_ctx.__aenter__ = AsyncMock(return_value=conn)
    conn_ctx.__aexit__ = AsyncMock(return_value=None)
    pool.acquire = MagicMock(return_value=conn_ctx)
    return pool


_TS = datetime(2026, 5, 24, tzinfo=timezone.utc)


# ─── device_tokens ──────────────────────────────────────────────────────────

class TestDeviceTokens:
    @pytest.mark.asyncio
    async def test_upsert_zero_user_raises(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="user_id"):
            await upsert_token(_build_pool(), user_id=0, fcm_token="t", platform="ios")

    @pytest.mark.asyncio
    async def test_upsert_bad_platform_raises(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="platform"):
            await upsert_token(_build_pool(), user_id=1, fcm_token="t", platform="palm")

    @pytest.mark.asyncio
    async def test_upsert_returns_id(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        rid = await upsert_token(_build_pool(lastrowid=7), user_id=1,
                                 fcm_token="t" * 32, platform="android", device_label="갤럭시")
        assert rid == 7

    @pytest.mark.asyncio
    async def test_list_active_tokens(self) -> None:
        from server.db.repositories.device_tokens import DeviceTokenRow, list_active_tokens

        row = (1, 10, "fcm", "ios", "iPhone", 1, _TS, None)
        rows = await list_active_tokens(_build_pool(fetchall=[row]), user_id=10)
        assert len(rows) == 1 and isinstance(rows[0], DeviceTokenRow)
        assert rows[0].is_active is True

    @pytest.mark.asyncio
    async def test_deactivate_true_false(self) -> None:
        from server.db.repositories.device_tokens import deactivate_token

        assert await deactivate_token(_build_pool(rowcount=1), token_id=5) is True
        assert await deactivate_token(_build_pool(rowcount=0), token_id=5) is False

    @pytest.mark.asyncio
    async def test_touch_last_used_commits(self) -> None:
        from server.db.repositories.device_tokens import touch_last_used

        pool = _build_pool()
        await touch_last_used(pool, token_id=5)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()


# ─── folders ────────────────────────────────────────────────────────────────

class TestFolders:
    @pytest.mark.asyncio
    async def test_insert_folder_returns_id(self) -> None:
        from server.db.repositories.folders import insert_folder

        assert await insert_folder(_build_pool(lastrowid=3),
                                   folder_id="abc12345", owner_id=10, name="업무") == 3

    @pytest.mark.asyncio
    async def test_list_folders(self) -> None:
        from server.db.repositories.folders import FolderRow, list_folders

        row = (1, "abc12345", 10, "업무", "blue", "#0066FF", 2, _TS)
        rows = await list_folders(_build_pool(fetchall=[row]), 10)
        assert len(rows) == 1 and isinstance(rows[0], FolderRow)

    @pytest.mark.asyncio
    async def test_list_folder_chats_include_exclude(self) -> None:
        from server.db.repositories.folders import list_folder_chats

        rows = [("dm", 100, "include"), ("room", 200, "exclude")]
        out = await list_folder_chats(_build_pool(fetchall=rows), 1)
        assert out["included_chats"] == [{"kind": "dm", "target_id": 100}]
        assert out["excluded_chats"] == [{"kind": "room", "target_id": 200}]

    @pytest.mark.asyncio
    async def test_delete_folder_true_false(self) -> None:
        from server.db.repositories.folders import delete_folder

        assert await delete_folder(_build_pool(rowcount=1), "abc12345", 10) is True
        assert await delete_folder(_build_pool(rowcount=0), "abc12345", 99) is False

    @pytest.mark.asyncio
    async def test_fetch_by_folder_id_found(self) -> None:
        from server.db.repositories.folders import FolderRow, fetch_by_folder_id_and_owner

        row = (1, "abc12345", 10, "업무", None, None, 0, _TS)
        result = await fetch_by_folder_id_and_owner(_build_pool(fetchone=row), "abc12345", 10)
        assert isinstance(result, FolderRow)

    @pytest.mark.asyncio
    async def test_fetch_by_folder_id_missing_none(self) -> None:
        from server.db.repositories.folders import fetch_by_folder_id_and_owner

        assert await fetch_by_folder_id_and_owner(_build_pool(fetchone=None), "x", 10) is None

    @pytest.mark.asyncio
    async def test_insert_folder_with_chats(self) -> None:
        from server.db.repositories.folders import insert_folder_with_chats

        new_id = await insert_folder_with_chats(
            _build_pool(lastrowid=5), folder_id="abc12345", owner_id=10, name="업무",
            included_chats=[{"kind": "dm", "target_id": 1}],
            excluded_chats=[{"kind": "room", "target_id": 2}],
        )
        assert new_id == 5

    @pytest.mark.asyncio
    async def test_update_folder_with_chats_found(self) -> None:
        from server.db.repositories.folders import update_folder_with_chats

        ok = await update_folder_with_chats(
            _build_pool(fetchone=(1,)), folder_id="abc12345", owner_id=10, name="신규명",
            included_chats=[{"kind": "dm", "target_id": 1}],
        )
        assert ok is True

    @pytest.mark.asyncio
    async def test_update_folder_with_chats_not_found(self) -> None:
        from server.db.repositories.folders import update_folder_with_chats

        ok = await update_folder_with_chats(
            _build_pool(fetchone=None), folder_id="ghost", owner_id=10, name="x")
        assert ok is False

    @pytest.mark.asyncio
    async def test_create_invite_returns_token(self) -> None:
        from server.db.repositories.folders import create_invite

        token = await create_invite(_build_pool(), folder_pk=1, created_by=10)
        assert isinstance(token, str) and len(token) == 32


# ─── emoji_packs ────────────────────────────────────────────────────────────

class TestEmojiPacks:
    @pytest.mark.asyncio
    async def test_insert_pack_pool_none_raises(self) -> None:
        from server.db.repositories.emoji_packs import insert_pack

        with pytest.raises(ValueError, match="pool"):
            await insert_pack(None, owner_user_id=1, name="n", slug="s")

    @pytest.mark.asyncio
    async def test_insert_pack_bad_slug_raises(self) -> None:
        from server.db.repositories.emoji_packs import insert_pack

        with pytest.raises(ValueError, match="slug"):
            await insert_pack(_build_pool(), owner_user_id=1, name="n", slug="")

    @pytest.mark.asyncio
    async def test_insert_pack_returns_id(self) -> None:
        from server.db.repositories.emoji_packs import insert_pack

        assert await insert_pack(_build_pool(lastrowid=9),
                                 owner_user_id=1, name="투나팩", slug="toona") == 9

    @pytest.mark.asyncio
    async def test_get_pack_by_slug_found(self) -> None:
        from server.db.repositories.emoji_packs import EmojiPackRow, get_pack_by_slug

        row = (3, 10, "투나팩", "toona", "설명", 1, "approved", 42)
        pack = await get_pack_by_slug(_build_pool(fetchone=row), "toona")
        assert isinstance(pack, EmojiPackRow)
        assert pack.download_count == 42 and pack.is_public is True

    @pytest.mark.asyncio
    async def test_get_pack_by_slug_missing_none(self) -> None:
        from server.db.repositories.emoji_packs import get_pack_by_slug

        assert await get_pack_by_slug(_build_pool(fetchone=None), "ghost") is None

    @pytest.mark.asyncio
    async def test_list_public_approved_limit_raises(self) -> None:
        from server.db.repositories.emoji_packs import list_public_approved

        with pytest.raises(ValueError, match="limit"):
            await list_public_approved(_build_pool(), limit=201)

    @pytest.mark.asyncio
    async def test_insert_item_bad_mime_raises(self) -> None:
        from server.db.repositories.emoji_packs import insert_item

        with pytest.raises(ValueError, match="mime_type"):
            await insert_item(_build_pool(), pack_id=1, shortcode="sc",
                              file_path="/p", mime_type="image/bmp")

    @pytest.mark.asyncio
    async def test_insert_item_returns_id(self) -> None:
        from server.db.repositories.emoji_packs import insert_item

        iid = await insert_item(_build_pool(lastrowid=11), pack_id=1,
                                shortcode="hi", file_path="/p.png", file_size=100, width=64, height=64)
        assert iid == 11

    @pytest.mark.asyncio
    async def test_list_items(self) -> None:
        from server.db.repositories.emoji_packs import EmojiPackItemRow, list_items

        row = (1, 3, "hi", "/p.png", "image/png", 100, 64, 64, "approved")
        rows = await list_items(_build_pool(fetchall=[row]), pack_id=3)
        assert len(rows) == 1 and isinstance(rows[0], EmojiPackItemRow)

    @pytest.mark.asyncio
    async def test_update_moderation_status(self) -> None:
        from server.db.repositories.emoji_packs import ModerationStatus, update_moderation_status

        n = await update_moderation_status(_build_pool(rowcount=1), pack_id=3,
                                           moderation_status=ModerationStatus.APPROVED)
        assert n == 1

    @pytest.mark.asyncio
    async def test_list_pending(self) -> None:
        from server.db.repositories.emoji_packs import PendingPackRow, list_pending

        row = (3, "toona", "투나팩", 10, "2026-05-24T00:00:00")
        rows = await list_pending(_build_pool(fetchall=[row]))
        assert len(rows) == 1 and isinstance(rows[0], PendingPackRow)
