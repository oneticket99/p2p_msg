# SPDX-License-Identifier: GPL-3.0-or-later
"""contacts + devices handlers chain E2E — cycle 169.724 신설."""

from __future__ import annotations

import base64
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.contacts_handlers import (
    handle_list_contacts, handle_upsert_contact,
)
from server.api.devices_handlers import (
    handle_register_device, handle_revoke_device,
)


pytestmark = pytest.mark.integration


class _FakeRequest:
    def __init__(
        self,
        app: web.Application,
        *,
        method: str = "POST",
        user_id: int | None = None,
        match_info: dict | None = None,
        body: dict | None = None,
    ) -> None:
        self.app = app
        self.method = method
        self.headers = {"User-Agent": "pytest"}
        self.match_info = match_info or {}
        self.query = {}
        self._state = {"user_id": user_id} if user_id is not None else {}
        self.remote = "127.0.0.1"
        self._body = body

    def __getitem__(self, key: str) -> Any:
        return self._state[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    async def json(self) -> dict:
        if self._body is None:
            raise ValueError("body 부재")
        return self._body


@pytest.fixture
def app_with_pool() -> web.Application:
    app = web.Application()
    app["db_pool"] = MagicMock()
    return app


class TestUpsertContact:
    @pytest.mark.asyncio
    async def test_no_auth_401(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, body={"phone": "010"})
        with pytest.raises(web.HTTPUnauthorized):
            await handle_upsert_contact(req)

    @pytest.mark.asyncio
    async def test_empty_phone_400(self, app_with_pool) -> None:
        req = _FakeRequest(app_with_pool, user_id=10, body={"phone": "  "})
        with pytest.raises(web.HTTPBadRequest, match="phone"):
            await handle_upsert_contact(req)

    @pytest.mark.asyncio
    async def test_pool_absent_503(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, user_id=10, body={"phone": "010-1234"})
        resp = await handle_upsert_contact(req)
        assert resp.status == 503

    @pytest.mark.asyncio
    async def test_upsert_returns_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.contacts_handlers._uc_repo.upsert_contact",
            AsyncMock(return_value=99),
        )
        monkeypatch.setattr(
            "server.api.contacts_handlers._uc_repo.find_user_by_phone",
            AsyncMock(return_value=20),
        )
        monkeypatch.setattr(
            "server.api.contacts_handlers._attempt_bidirectional_match",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"phone": "010-1234", "last_name": "Kim", "first_name": "Alice"},
        )
        resp = await handle_upsert_contact(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["contact_id"] == 99
        assert data["matched_user_id"] == 20


class TestListContacts:
    @pytest.mark.asyncio
    async def test_no_auth_401(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, method="GET")
        with pytest.raises(web.HTTPUnauthorized):
            await handle_list_contacts(req)

    @pytest.mark.asyncio
    async def test_pool_absent_empty(self) -> None:
        app = web.Application()
        req = _FakeRequest(app, method="GET", user_id=10)
        resp = await handle_list_contacts(req)
        assert resp.status == 200
        assert json.loads(resp.body)["contacts"] == []

    @pytest.mark.asyncio
    async def test_list_returns_payload(self, app_with_pool, monkeypatch) -> None:
        row = SimpleNamespace(
            id=1, phone="010-1234", last_name="Kim", first_name="Alice",
            matched_user_id=20,
        )
        monkeypatch.setattr(
            "server.api.contacts_handlers._uc_repo.list_contacts",
            AsyncMock(return_value=[row]),
        )
        req = _FakeRequest(app_with_pool, method="GET", user_id=10)
        resp = await handle_list_contacts(req)
        assert resp.status == 200
        data = json.loads(resp.body)
        assert len(data["contacts"]) == 1
        assert data["contacts"][0]["phone"] == "010-1234"


def _valid_pubkey_b64() -> str:
    # 한글 주석 — 32 byte X25519 public key base64
    return base64.b64encode(b"\x00" * 32).decode()


class TestRegisterDevice:
    @pytest.mark.asyncio
    async def test_empty_device_id_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"device_id": "", "bundle": {}},
        )
        with pytest.raises(web.HTTPBadRequest, match="device_id"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_oversize_device_id_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"device_id": "x" * 65, "bundle": {}},
        )
        with pytest.raises(web.HTTPBadRequest, match="64"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_missing_bundle_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={"device_id": "dev-1"},
        )
        with pytest.raises(web.HTTPBadRequest, match="bundle"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_register_201(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.insert_device",
            AsyncMock(return_value=99),
        )
        monkeypatch.setattr(
            "server.api.devices_handlers._audit_device",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={
                "device_id": "dev-1",
                "label": "MyMac",
                "bundle": {
                    "identity_public": _valid_pubkey_b64(),
                    "signed_prekey_public": _valid_pubkey_b64(),
                },
            },
        )
        resp = await handle_register_device(req)
        assert resp.status == 201
        data = json.loads(resp.body)
        assert data["id"] == 99
        assert data["device_id"] == "dev-1"

    @pytest.mark.asyncio
    async def test_duplicate_device_id_409(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.insert_device",
            AsyncMock(side_effect=RuntimeError("1062 Duplicate entry")),
        )
        req = _FakeRequest(
            app_with_pool, user_id=10,
            body={
                "device_id": "dev-1", "label": "x",
                "bundle": {
                    "identity_public": _valid_pubkey_b64(),
                    "signed_prekey_public": _valid_pubkey_b64(),
                },
            },
        )
        resp = await handle_register_device(req)
        assert resp.status == 409
        assert json.loads(resp.body)["error"] == "duplicate_device_id"


class TestRevokeDevice:
    @pytest.mark.asyncio
    async def test_empty_path_400(self, app_with_pool) -> None:
        req = _FakeRequest(
            app_with_pool, method="DELETE", user_id=10,
            match_info={"device_id": ""},
        )
        with pytest.raises(web.HTTPBadRequest, match="device_id"):
            await handle_revoke_device(req)

    @pytest.mark.asyncio
    async def test_revoke_success(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.revoke_device",
            AsyncMock(return_value=True),
        )
        monkeypatch.setattr(
            "server.api.devices_handlers._audit_device",
            AsyncMock(return_value=None),
        )
        req = _FakeRequest(
            app_with_pool, method="DELETE", user_id=10,
            match_info={"device_id": "dev-1"},
        )
        resp = await handle_revoke_device(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_revoke_not_found_404(self, app_with_pool, monkeypatch) -> None:
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.revoke_device",
            AsyncMock(return_value=False),
        )
        req = _FakeRequest(
            app_with_pool, method="DELETE", user_id=10,
            match_info={"device_id": "ghost"},
        )
        resp = await handle_revoke_device(req)
        assert resp.status == 404
