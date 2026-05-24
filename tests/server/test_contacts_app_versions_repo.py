# SPDX-License-Identifier: GPL-3.0-or-later
"""user_contacts + app_versions repo unit — cycle 169.734 신설."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, rowcount=1) -> MagicMock:
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


class TestNormalizePhone:
    def test_korean_mobile_0_prefix(self) -> None:
        from server.db.repositories.user_contacts import normalize_phone

        assert normalize_phone("01012345678") == "+821012345678"

    def test_with_spaces_and_plus(self) -> None:
        from server.db.repositories.user_contacts import normalize_phone

        assert normalize_phone("+82 10 1234 5678") == "+821012345678"

    def test_82_prefix_12_digit(self) -> None:
        from server.db.repositories.user_contacts import normalize_phone

        assert normalize_phone("821012345678") == "+821012345678"

    def test_empty_returns_empty(self) -> None:
        from server.db.repositories.user_contacts import normalize_phone

        assert normalize_phone("") == ""
        assert normalize_phone("abc") == ""


class TestUpsertContact:
    @pytest.mark.asyncio
    async def test_zero_owner_raises(self) -> None:
        from server.db.repositories.user_contacts import upsert_contact

        with pytest.raises(ValueError, match="owner_user_id"):
            await upsert_contact(None, owner_user_id=0, phone="010-1234-5678")

    @pytest.mark.asyncio
    async def test_empty_phone_raises(self) -> None:
        from server.db.repositories.user_contacts import upsert_contact

        pool = _build_pool()
        with pytest.raises(ValueError, match="phone"):
            await upsert_contact(pool, owner_user_id=10, phone="")

    @pytest.mark.asyncio
    async def test_upsert_returns_id(self) -> None:
        from server.db.repositories.user_contacts import upsert_contact

        pool = _build_pool(lastrowid=99)
        rid = await upsert_contact(
            pool, owner_user_id=10, phone="010-1234-5678",
            last_name="Kim", first_name="Alice",
        )
        assert rid == 99


class TestFindUserByPhone:
    @pytest.mark.asyncio
    async def test_empty_phone_none(self) -> None:
        from server.db.repositories.user_contacts import find_user_by_phone

        assert await find_user_by_phone(None, "") is None

    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from server.db.repositories.user_contacts import find_user_by_phone

        pool = _build_pool(fetchone=(20,))
        uid = await find_user_by_phone(pool, "010-1234-5678")
        assert uid == 20

    @pytest.mark.asyncio
    async def test_not_found_none(self) -> None:
        from server.db.repositories.user_contacts import find_user_by_phone

        pool = _build_pool(fetchone=None)
        assert await find_user_by_phone(pool, "010-9999-9999") is None


class TestListContacts:
    @pytest.mark.asyncio
    async def test_returns_rows(self) -> None:
        from server.db.repositories.user_contacts import list_contacts

        row = (1, 10, "+821012345678", "Kim", "Alice", 20,
               datetime(2026, 5, 24, tzinfo=timezone.utc))
        pool = _build_pool(fetchall=[row])
        rows = await list_contacts(pool, owner_user_id=10)
        assert len(rows) == 1
        assert rows[0].matched_user_id == 20


class TestAppVersionInsert:
    @pytest.mark.asyncio
    async def test_pool_none_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, insert_version

        with pytest.raises(ValueError, match="pool"):
            await insert_version(
                None, version="1.0.0", platform=Platform.MACOS_ARM64,
                zip_url="https://x/y.zip", sha256="a" * 64,
            )

    @pytest.mark.asyncio
    async def test_empty_version_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, insert_version

        pool = _build_pool()
        with pytest.raises(ValueError, match="version"):
            await insert_version(
                pool, version="", platform=Platform.MACOS_ARM64,
                zip_url="https://x/y.zip", sha256="a" * 64,
            )

    @pytest.mark.asyncio
    async def test_invalid_sha256_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, insert_version

        pool = _build_pool()
        with pytest.raises(ValueError, match="sha256"):
            await insert_version(
                pool, version="1.0.0", platform=Platform.MACOS_ARM64,
                zip_url="https://x/y.zip", sha256="tooshort",
            )

    @pytest.mark.asyncio
    async def test_non_hex_sha256_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, insert_version

        pool = _build_pool()
        with pytest.raises(ValueError, match="sha256"):
            await insert_version(
                pool, version="1.0.0", platform=Platform.MACOS_ARM64,
                zip_url="https://x/y.zip", sha256="z" * 64,
            )

    @pytest.mark.asyncio
    async def test_insert_returns_id(self) -> None:
        from server.db.repositories.app_versions import Platform, insert_version

        pool = _build_pool(lastrowid=77)
        vid = await insert_version(
            pool, version="1.2.3", platform=Platform.MACOS_ARM64,
            zip_url="https://x/y.zip", sha256="a" * 64,
            file_size=12345, is_latest=True,
        )
        assert vid == 77


class TestAppVersionListHistory:
    @pytest.mark.asyncio
    async def test_pool_none_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, list_history

        with pytest.raises(ValueError, match="pool"):
            await list_history(None, platform=Platform.MACOS_ARM64)

    @pytest.mark.asyncio
    async def test_invalid_limit_raises(self) -> None:
        from server.db.repositories.app_versions import Platform, list_history

        pool = _build_pool()
        with pytest.raises(ValueError, match="limit"):
            await list_history(pool, platform=Platform.MACOS_ARM64, limit=0)

    @pytest.mark.asyncio
    async def test_returns_rows(self) -> None:
        from server.db.repositories.app_versions import Platform, list_history

        row = (
            1, "1.2.3", "macos-arm64", "https://x/y.zip", "a" * 64,
            12345, "1.0.0",
            datetime(2026, 5, 24, tzinfo=timezone.utc), "notes", 1,
        )
        pool = _build_pool(fetchall=[row])
        rows = await list_history(pool, platform=Platform.MACOS_ARM64)
        assert len(rows) == 1
        assert rows[0].version == "1.2.3"
