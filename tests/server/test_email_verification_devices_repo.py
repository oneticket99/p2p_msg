# SPDX-License-Identifier: GPL-3.0-or-later
"""email_verification + devices repository unit — cycle 169.755 신설.

OTP 발급/검증/소진/무효화/cleanup + device 등록/조회/revoke/last_seen.
mock async pool (execute_return 으로 rowcount 반환 SQL 지원).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest


def _build_pool(*, fetchone=None, fetchall=None, lastrowid=1, execute_return=None) -> MagicMock:
    # 한글 주석 — execute_return = invalidate/revoke 등 affected rowcount 반환 SQL 지원
    pool = MagicMock()
    cur = MagicMock()
    cur.execute = AsyncMock(return_value=execute_return)
    cur.fetchone = AsyncMock(return_value=fetchone)
    cur.fetchall = AsyncMock(return_value=fetchall or [])
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


_TS = datetime(2026, 5, 24, tzinfo=timezone.utc)
# 한글 주석 — email_verification OtpRow 8-tuple
_OTP_ROW = (4, "a@b.com", "signup", "h" * 64, _TS, None, 0, _TS)
# 한글 주석 — devices DeviceRow 11-tuple (identity/prekey = bytes)
_DEV_ROW = (
    1, "dev-uuid", 10, "iPhone", b"idpub", b"spk", b"otpk",
    _TS, _TS, None, "active",
)


class TestInsertOtp:
    @pytest.mark.asyncio
    async def test_returns_lastrowid(self) -> None:
        from server.db.repositories.email_verification import insert_otp

        new_id = await insert_otp(_build_pool(lastrowid=11),
                                  email="A@B.com", purpose="signup", code_hash="h" * 64)
        assert new_id == 11


class TestFindActiveOtp:
    @pytest.mark.asyncio
    async def test_found(self) -> None:
        from server.db.repositories.email_verification import OtpRow, find_active_otp

        row = await find_active_otp(_build_pool(fetchone=_OTP_ROW),
                                    email="a@b.com", purpose="signup")
        assert isinstance(row, OtpRow)
        assert row.purpose == "signup" and row.attempt_count == 0

    @pytest.mark.asyncio
    async def test_missing_returns_none(self) -> None:
        from server.db.repositories.email_verification import find_active_otp

        assert await find_active_otp(_build_pool(fetchone=None),
                                     email="x@y.com", purpose="signup") is None


class TestOtpMutate:
    @pytest.mark.asyncio
    async def test_increment_attempt_returns_count(self) -> None:
        from server.db.repositories.email_verification import increment_attempt

        assert await increment_attempt(_build_pool(fetchone=(3,)), 4) == 3

    @pytest.mark.asyncio
    async def test_increment_attempt_no_row_zero(self) -> None:
        from server.db.repositories.email_verification import increment_attempt

        assert await increment_attempt(_build_pool(fetchone=None), 4) == 0

    @pytest.mark.asyncio
    async def test_consume_otp_commits(self) -> None:
        from server.db.repositories.email_verification import consume_otp

        pool = _build_pool()
        await consume_otp(pool, 4)
        conn = await pool.acquire().__aenter__()
        conn.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalidate_pending_count(self) -> None:
        from server.db.repositories.email_verification import invalidate_pending

        n = await invalidate_pending(_build_pool(execute_return=2),
                                     email="A@B.com", purpose="signup")
        assert n == 2

    @pytest.mark.asyncio
    async def test_cleanup_expired_count(self) -> None:
        from server.db.repositories.email_verification import cleanup_expired

        assert await cleanup_expired(_build_pool(execute_return=5)) == 5


class TestInsertDevice:
    @pytest.mark.asyncio
    async def test_returns_lastrowid(self) -> None:
        from server.db.repositories.devices import insert_device

        new_id = await insert_device(
            _build_pool(lastrowid=9), device_id="dev-uuid", user_id=10,
            label="iPhone", identity_public=b"idpub", signed_prekey_public=b"spk",
        )
        assert new_id == 9


class TestGetDevices:
    @pytest.mark.asyncio
    async def test_active_only(self) -> None:
        from server.db.repositories.devices import get_devices_by_user

        rows = await get_devices_by_user(_build_pool(fetchall=[_DEV_ROW]), 10)
        assert len(rows) == 1 and rows[0].status == "active"

    @pytest.mark.asyncio
    async def test_include_revoked_branch(self) -> None:
        from server.db.repositories.devices import get_devices_by_user

        rows = await get_devices_by_user(
            _build_pool(fetchall=[_DEV_ROW, _DEV_ROW]), 10, include_revoked=True)
        assert len(rows) == 2

    @pytest.mark.asyncio
    async def test_get_by_device_id_found(self) -> None:
        from server.db.repositories.devices import DeviceRow, get_device_by_device_id

        row = await get_device_by_device_id(_build_pool(fetchone=_DEV_ROW), "dev-uuid")
        assert isinstance(row, DeviceRow)
        assert row.device_id == "dev-uuid"
        assert row.one_time_prekey_public == b"otpk"

    @pytest.mark.asyncio
    async def test_get_by_device_id_missing_none(self) -> None:
        from server.db.repositories.devices import get_device_by_device_id

        assert await get_device_by_device_id(_build_pool(fetchone=None), "ghost") is None


class TestDeviceMutate:
    @pytest.mark.asyncio
    async def test_revoke_success_true(self) -> None:
        from server.db.repositories.devices import revoke_device

        assert await revoke_device(_build_pool(execute_return=1), "dev-uuid", 10) is True

    @pytest.mark.asyncio
    async def test_revoke_noop_false(self) -> None:
        from server.db.repositories.devices import revoke_device

        assert await revoke_device(_build_pool(execute_return=0), "dev-uuid", 99) is False

    @pytest.mark.asyncio
    async def test_update_last_seen_true(self) -> None:
        from server.db.repositories.devices import update_last_seen

        assert await update_last_seen(_build_pool(execute_return=1), "dev-uuid") is True

    @pytest.mark.asyncio
    async def test_update_last_seen_missing_false(self) -> None:
        from server.db.repositories.devices import update_last_seen

        assert await update_last_seen(_build_pool(execute_return=0), "ghost") is False
