# SPDX-License-Identifier: GPL-3.0-or-later
"""AuthClient unit test — cycle 169.676 omit 제거 path."""

from __future__ import annotations

import pytest


class TestAuthClientInit:
    def test_trims_trailing_slash(self) -> None:
        from app.net.auth_client import AuthClient

        c = AuthClient("https://api.local/")
        assert c._base_url == "https://api.local"
        assert c._owns_session is True

    def test_no_session_owns_default(self) -> None:
        from app.net.auth_client import AuthClient

        c = AuthClient("https://api.local")
        assert c._session is None
        assert c._owns_session is True

    def test_external_session_not_owned(self) -> None:
        from unittest.mock import MagicMock

        from app.net.auth_client import AuthClient

        session = MagicMock()
        c = AuthClient("https://api.local", session=session)
        assert c._session is session
        assert c._owns_session is False


class TestAuthResult:
    def test_default_ok_true(self) -> None:
        from app.net.auth_client import AuthResult

        r = AuthResult(ok=True, user_id=10, token="abc")
        assert r.ok is True
        assert r.user_id == 10
        assert r.token == "abc"
        assert r.error_code is None

    def test_error_result_fields(self) -> None:
        from app.net.auth_client import AuthResult

        r = AuthResult(
            ok=False, error_code="INVALID_CRED",
            error_message="비밀번호 불일치",
        )
        assert r.ok is False
        assert r.error_code == "INVALID_CRED"
        assert r.error_message == "비밀번호 불일치"
        assert r.user_id is None

    def test_next_step_field(self) -> None:
        # 한글 주석 — OTP 의 의 next_step="otp" path
        from app.net.auth_client import AuthResult

        r = AuthResult(ok=True, next_step="otp")
        assert r.next_step == "otp"


class TestAuthClientClose:
    @pytest.mark.asyncio
    async def test_close_no_session_noop(self) -> None:
        from app.net.auth_client import AuthClient

        c = AuthClient("https://api.local")
        # session=None → close graceful
        await c.close()

    @pytest.mark.asyncio
    async def test_close_external_session_not_closed(self) -> None:
        # 한글 주석 — 외부 주입 session 의 close 책임 caller
        from unittest.mock import AsyncMock, MagicMock

        from app.net.auth_client import AuthClient

        session = MagicMock()
        session.close = AsyncMock()
        c = AuthClient("https://api.local", session=session)
        await c.close()
        session.close.assert_not_awaited()
