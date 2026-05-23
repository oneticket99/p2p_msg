# SPDX-License-Identifier: GPL-3.0-or-later
"""auth handlers chain E2E — cycle 169.685 신설.

chain:
1. register 201 success
2. register 400 VALIDATION
3. register 409 EMAIL_DUPLICATE race
4. register 409 USERNAME_DUPLICATE race
5. register 500 internal
6. verify 200 + token + session_store 등록
7. verify AuthError → http_status 매핑
8. login 200 + token + email retain
9. login AuthError → http_status 매핑
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.auth_handlers import (
    handle_login, handle_register, handle_verify,
)
from server.auth.exceptions import (
    AuthError, EmailAlreadyRegistered, InvalidCredentials, OtpInvalid,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = "POST"
        self.headers = {"User-Agent": "pytest"}
        self.match_info = {}
        self._state = {}
        self.remote = "127.0.0.1"
        self._body = body or {}

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    app["session_store"] = {}
    return app


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(return_value={
                "user_id": 99, "reclaimed": False, "smtp_status": "sent",
            }),
        )
        monkeypatch.setattr(
            "server.api.auth_handlers._audit", AsyncMock(return_value=None)
        )
        req = _FakeRequest(app_with_pool, body={
            "email": "x@x.com", "username": "user1", "password": "Passw0rd!",
        })
        resp = await handle_register(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["user_id"] == 99
        assert data["next"] == "verify_otp"

    @pytest.mark.asyncio
    async def test_register_validation_400(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(side_effect=ValueError("password 8자")),
        )
        req = _FakeRequest(app_with_pool, body={"email": "x"})
        resp = await handle_register(req)
        assert resp.status == 400
        assert json.loads(resp.body)["error"] == "VALIDATION"

    @pytest.mark.asyncio
    async def test_register_email_duplicate_auth_error(
        self, app_with_pool, monkeypatch,
    ) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(side_effect=EmailAlreadyRegistered("dup")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_register(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "EMAIL_DUPLICATE"

    @pytest.mark.asyncio
    async def test_register_race_uq_email(self, app_with_pool, monkeypatch) -> None:
        # 한글 주석 — race INSERT exception 안 uq_users_email 매핑
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(side_effect=RuntimeError("uq_users_email violation")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_register(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "EMAIL_DUPLICATE"

    @pytest.mark.asyncio
    async def test_register_race_uq_username(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(side_effect=RuntimeError("uq_users_username violation")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_register(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "USERNAME_DUPLICATE"

    @pytest.mark.asyncio
    async def test_register_unknown_500(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.register_uc.register_user",
            AsyncMock(side_effect=RuntimeError("unknown")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_register(req)
        assert resp.status == 500


class TestVerify:
    @pytest.mark.asyncio
    async def test_verify_otp_returns_token(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.verify_uc.verify_signup_otp",
            AsyncMock(return_value=42),
        )
        # 한글 주석 — generate_session_token 의 함수 안 local import 정합 — app.core.security path
        monkeypatch.setattr(
            "app.core.security.generate_session_token",
            MagicMock(return_value="tok-abc"),
        )
        monkeypatch.setattr(
            "server.api.auth_handlers._create_session_row",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.auth_handlers._audit", AsyncMock(return_value=None)
        )
        req = _FakeRequest(app_with_pool, body={"email": "x@x", "code": "123456"})
        resp = await handle_verify(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["user_id"] == 42
        assert data["token"] == "tok-abc"
        assert app_with_pool["session_store"]["tok-abc"] == 42

    @pytest.mark.asyncio
    async def test_verify_otp_invalid_400(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.verify_uc.verify_signup_otp",
            AsyncMock(side_effect=OtpInvalid("mismatch")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_verify(req)
        assert resp.status == 400
        assert json.loads(resp.body)["error"] == "OTP_INVALID"


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_returns_token_email(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.login_uc.login_user",
            AsyncMock(return_value=(99, "tok-xyz")),
        )
        monkeypatch.setattr(
            "server.api.auth_handlers._create_session_row",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            "server.api.auth_handlers._audit", AsyncMock(return_value=None)
        )
        req = _FakeRequest(app_with_pool, body={
            "email": "alice@x.com", "password": "Passw0rd!",
        })
        resp = await handle_login(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert data["user_id"] == 99
        assert data["token"] == "tok-xyz"
        assert data["email"] == "alice@x.com"

    @pytest.mark.asyncio
    async def test_login_invalid_creds_401(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.auth_handlers.login_uc.login_user",
            AsyncMock(side_effect=InvalidCredentials("mismatch")),
        )
        req = _FakeRequest(app_with_pool, body={})
        resp = await handle_login(req)
        assert resp.status == 401
        assert json.loads(resp.body)["error"] == "INVALID_CREDENTIALS"
