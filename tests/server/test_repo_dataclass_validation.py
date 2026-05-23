# SPDX-License-Identifier: GPL-3.0-or-later
"""server repository dataclass + validation unit — cycle 169.706 신설.

users + device_tokens + app_versions repo 의 dataclass shape + validation chain.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest


class TestUserRow:
    def test_construct(self) -> None:
        from server.db.repositories.users import UserRow

        u = UserRow(
            id=1, email="x@x.com", username="alice",
            password_hash="hash$" + "a" * 50, email_verified=True,
            status="active",
            created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            last_login_at=None,
        )
        assert u.email == "x@x.com"
        assert u.email_verified is True

    def test_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        from server.db.repositories.users import UserRow

        u = UserRow(
            id=1, email="x@x.com", username="alice",
            password_hash="x", email_verified=False, status="active",
            created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            last_login_at=None,
        )
        with pytest.raises(FrozenInstanceError):
            u.email = "y@y.com"  # type: ignore[misc]


class TestDeviceTokenRow:
    def test_construct(self) -> None:
        from server.db.repositories.device_tokens import DeviceTokenRow

        d = DeviceTokenRow(
            id=1, user_id=10, fcm_token="abc", platform="macos",
            device_label="my-mac", is_active=True,
            created_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            last_used_at=None,
        )
        assert d.platform == "macos"
        assert d.is_active is True


class TestUpsertTokenValidation:
    @pytest.mark.asyncio
    async def test_zero_user_id_raises(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="user_id"):
            await upsert_token(None, user_id=0, fcm_token="x", platform="macos")

    @pytest.mark.asyncio
    async def test_empty_token_raises(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="fcm_token"):
            await upsert_token(None, user_id=10, fcm_token="", platform="macos")

    @pytest.mark.asyncio
    async def test_oversize_token_raises(self) -> None:
        # 한글 주석 — 513자 → ValueError
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="fcm_token"):
            await upsert_token(
                None, user_id=10, fcm_token="x" * 513, platform="macos",
            )

    @pytest.mark.asyncio
    async def test_invalid_platform_raises(self) -> None:
        from server.db.repositories.device_tokens import upsert_token

        with pytest.raises(ValueError, match="platform"):
            await upsert_token(
                None, user_id=10, fcm_token="x", platform="freebsd",
            )


class TestPlatformEnum:
    def test_4_platforms(self) -> None:
        from server.db.repositories.app_versions import Platform

        assert Platform.MACOS_ARM64.value == "macos-arm64"
        assert Platform.MACOS_X64.value == "macos-x64"
        assert Platform.WINDOWS_X64.value == "windows-x64"
        assert Platform.LINUX_X64.value == "linux-x64"

    def test_str_enum(self) -> None:
        from server.db.repositories.app_versions import Platform

        assert Platform.MACOS_ARM64 == "macos-arm64"

    def test_invalid_raises(self) -> None:
        from server.db.repositories.app_versions import Platform

        with pytest.raises(ValueError):
            Platform("freebsd-x64")


class TestAppVersionRow:
    def test_construct(self) -> None:
        from server.db.repositories.app_versions import AppVersionRow, Platform

        r = AppVersionRow(
            id=1, version="1.2.3", platform=Platform.MACOS_ARM64,
            zip_url="https://x/y.zip", sha256="a" * 64, file_size=1000,
            min_compatible_version="1.0.0",
            released_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            release_notes="notes", is_latest=True,
        )
        assert r.version == "1.2.3"
        assert r.platform == Platform.MACOS_ARM64


class TestRowToDataclass:
    def test_tuple_to_row(self) -> None:
        from server.db.repositories.app_versions import (
            Platform, _row_to_dataclass,
        )

        tup = (
            1, "1.2.3", "macos-arm64", "https://x/y.zip", "a" * 64,
            12345, "1.0.0",
            datetime(2026, 5, 24, tzinfo=timezone.utc),
            "notes", 1,
        )
        row = _row_to_dataclass(tup)
        assert row.id == 1
        assert row.platform == Platform.MACOS_ARM64
        assert row.is_latest is True
