# SPDX-License-Identifier: GPL-3.0-or-later
"""``server.api.devices_handlers`` 단위 테스트.

multi-device sync handler — base64 디코딩 + wire format 변환 + handler
3 함수 (register / list / revoke) logic 검증. pool/middleware 의 mock
주입 의무. aiohttp HTTPException 의 status 검증.
"""

from __future__ import annotations

import base64
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import web

from server.api.devices_handlers import (
    _decode_pubkey,
    _device_row_to_wire,
    _encode_pubkey,
    handle_list_devices,
    handle_register_device,
    handle_revoke_device,
)
from server.db.repositories.devices import DeviceRow


def _make_row(
    device_id: str = "dev-1",
    user_id: int = 42,
    status: str = "active",
    label: str = "MacBook",
) -> DeviceRow:
    return DeviceRow(
        id=1,
        device_id=device_id,
        user_id=user_id,
        label=label,
        identity_public=b"\x01" * 32,
        signed_prekey_public=b"\x02" * 32,
        one_time_prekey_public=b"\x03" * 32,
        created_at=datetime(2026, 5, 20, 16, 0, 0),
        updated_at=datetime(2026, 5, 20, 16, 0, 0),
        last_seen_at=None,
        status=status,
    )


def _make_request(
    *,
    user_id: int = 42,
    body: dict | None = None,
    match_info: dict | None = None,
    query: dict | None = None,
) -> MagicMock:
    """aiohttp.web.Request mock — user_id middleware 주입 모사 + app[db_pool]."""

    req = MagicMock()
    req.__getitem__.side_effect = lambda k: {"user_id": user_id}[k]
    req.app = MagicMock()
    req.app.__getitem__.side_effect = lambda k: {"db_pool": MagicMock()}[k]
    if body is not None:
        req.json = AsyncMock(return_value=body)
    if match_info is not None:
        req.match_info = match_info
    else:
        req.match_info = {}
    req.query = query or {}
    return req


# ---------------------------------------------------------------------------
# base64 헬퍼
# ---------------------------------------------------------------------------


class TestDecodePubkey:
    def test_valid_32_bytes(self) -> None:
        raw = b"\xAA" * 32
        b64 = base64.b64encode(raw).decode("ascii")
        assert _decode_pubkey(b64, field_name="ik") == raw

    def test_wrong_length_rejected(self) -> None:
        b64 = base64.b64encode(b"\x01" * 31).decode("ascii")
        with pytest.raises(web.HTTPBadRequest, match="ik 길이"):
            _decode_pubkey(b64, field_name="ik")

    def test_invalid_base64_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="base64"):
            _decode_pubkey("@@invalid@@", field_name="spk")

    def test_empty_string_rejected(self) -> None:
        with pytest.raises(web.HTTPBadRequest, match="길이"):
            _decode_pubkey("", field_name="opk")


class TestEncodePubkey:
    def test_bytes_encoded(self) -> None:
        raw = b"\x55" * 32
        result = _encode_pubkey(raw)
        assert result == base64.b64encode(raw).decode("ascii")

    def test_none_returns_none(self) -> None:
        assert _encode_pubkey(None) is None


class TestDeviceRowToWire:
    def test_basic_row(self) -> None:
        row = _make_row(label="Daisy 의 MacBook")
        wire = _device_row_to_wire(row)
        assert wire["device_id"] == "dev-1"
        assert wire["user_id"] == 42
        assert wire["label"] == "Daisy 의 MacBook"
        assert wire["status"] == "active"
        assert wire["bundle"]["identity_public"] == base64.b64encode(b"\x01" * 32).decode("ascii")
        assert wire["bundle"]["one_time_prekey_public"] is not None

    def test_revoked_status(self) -> None:
        row = _make_row(status="revoked")
        wire = _device_row_to_wire(row)
        assert wire["status"] == "revoked"

    def test_last_seen_none(self) -> None:
        row = _make_row()
        wire = _device_row_to_wire(row)
        assert wire["last_seen_at"] is None

    def test_opk_none(self) -> None:
        row = DeviceRow(
            id=1,
            device_id="dev-noopk",
            user_id=1,
            label="",
            identity_public=b"\x01" * 32,
            signed_prekey_public=b"\x02" * 32,
            one_time_prekey_public=None,
            created_at=datetime(2026, 5, 20),
            updated_at=datetime(2026, 5, 20),
            last_seen_at=None,
            status="active",
        )
        wire = _device_row_to_wire(row)
        assert wire["bundle"]["one_time_prekey_public"] is None


# ---------------------------------------------------------------------------
# handle_register_device
# ---------------------------------------------------------------------------


class TestHandleRegisterDevice:
    @pytest.mark.asyncio
    async def test_valid_registration(self, monkeypatch) -> None:
        body = {
            "device_id": "dev-x",
            "label": "Daisy 의 노트북",
            "bundle": {
                "identity_public": base64.b64encode(b"\x01" * 32).decode("ascii"),
                "signed_prekey_public": base64.b64encode(b"\x02" * 32).decode("ascii"),
            },
        }
        req = _make_request(body=body)
        mock_insert = AsyncMock(return_value=99)
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.insert_device",
            mock_insert,
        )

        resp = await handle_register_device(req)
        assert resp.status == 201
        # mock 호출 인자 검증
        call_kwargs = mock_insert.await_args.kwargs
        assert call_kwargs["device_id"] == "dev-x"
        assert call_kwargs["user_id"] == 42
        assert call_kwargs["label"] == "Daisy 의 노트북"
        assert len(call_kwargs["identity_public"]) == 32

    @pytest.mark.asyncio
    async def test_missing_device_id_rejected(self) -> None:
        req = _make_request(body={"bundle": {}})
        with pytest.raises(web.HTTPBadRequest, match="device_id"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_missing_bundle_rejected(self) -> None:
        req = _make_request(body={"device_id": "x"})
        with pytest.raises(web.HTTPBadRequest, match="bundle"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_invalid_pubkey_length_rejected(self) -> None:
        body = {
            "device_id": "x",
            "bundle": {
                "identity_public": base64.b64encode(b"\x01" * 31).decode("ascii"),
                "signed_prekey_public": base64.b64encode(b"\x02" * 32).decode("ascii"),
            },
        }
        req = _make_request(body=body)
        with pytest.raises(web.HTTPBadRequest, match="identity_public"):
            await handle_register_device(req)

    @pytest.mark.asyncio
    async def test_duplicate_device_id_409(self, monkeypatch) -> None:
        body = {
            "device_id": "dev-dup",
            "bundle": {
                "identity_public": base64.b64encode(b"\x01" * 32).decode("ascii"),
                "signed_prekey_public": base64.b64encode(b"\x02" * 32).decode("ascii"),
            },
        }
        req = _make_request(body=body)
        mock_insert = AsyncMock(side_effect=Exception("1062 Duplicate entry"))
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.insert_device",
            mock_insert,
        )

        resp = await handle_register_device(req)
        assert resp.status == 409

    @pytest.mark.asyncio
    async def test_device_id_too_long(self) -> None:
        body = {
            "device_id": "x" * 65,
            "bundle": {
                "identity_public": base64.b64encode(b"\x01" * 32).decode("ascii"),
                "signed_prekey_public": base64.b64encode(b"\x02" * 32).decode("ascii"),
            },
        }
        req = _make_request(body=body)
        with pytest.raises(web.HTTPBadRequest, match="64 상한"):
            await handle_register_device(req)


# ---------------------------------------------------------------------------
# handle_list_devices
# ---------------------------------------------------------------------------


class TestHandleListDevices:
    @pytest.mark.asyncio
    async def test_empty_list(self, monkeypatch) -> None:
        req = _make_request()
        mock_get = AsyncMock(return_value=[])
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.get_devices_by_user",
            mock_get,
        )

        resp = await handle_list_devices(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_multi_devices_returned(self, monkeypatch) -> None:
        req = _make_request()
        rows = [_make_row(device_id="d1"), _make_row(device_id="d2", label="phone")]
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.get_devices_by_user",
            AsyncMock(return_value=rows),
        )

        resp = await handle_list_devices(req)
        assert resp.status == 200
        # response body — aiohttp web.Response.body bytes
        body = resp.body.decode("utf-8")
        assert '"count": 2' in body
        assert '"d1"' in body
        assert '"d2"' in body

    @pytest.mark.asyncio
    async def test_include_revoked_query(self, monkeypatch) -> None:
        req = _make_request(query={"include_revoked": "1"})
        mock_get = AsyncMock(return_value=[])
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.get_devices_by_user",
            mock_get,
        )

        await handle_list_devices(req)
        assert mock_get.await_args.kwargs["include_revoked"] is True


# ---------------------------------------------------------------------------
# handle_revoke_device
# ---------------------------------------------------------------------------


class TestHandleRevokeDevice:
    @pytest.mark.asyncio
    async def test_successful_revoke(self, monkeypatch) -> None:
        req = _make_request(match_info={"device_id": "dev-revoke"})
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.revoke_device",
            AsyncMock(return_value=True),
        )

        resp = await handle_revoke_device(req)
        assert resp.status == 200

    @pytest.mark.asyncio
    async def test_missing_device_returns_404(self, monkeypatch) -> None:
        req = _make_request(match_info={"device_id": "missing"})
        monkeypatch.setattr(
            "server.api.devices_handlers.devices_repo.revoke_device",
            AsyncMock(return_value=False),
        )

        resp = await handle_revoke_device(req)
        assert resp.status == 404

    @pytest.mark.asyncio
    async def test_empty_device_id_path(self) -> None:
        req = _make_request(match_info={"device_id": ""})
        with pytest.raises(web.HTTPBadRequest, match="device_id"):
            await handle_revoke_device(req)
