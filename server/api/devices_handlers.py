# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — multi-device sync (Phase 2 사이클 43).

엔드포인트:
- POST /api/devices — device 등록 (Authorization Bearer 의무)
- GET /api/devices — 현재 사용자 의 device list fetch
- DELETE /api/devices/<device_id> — device revoke (soft-delete)

사이클 42 의 `app/crypto/device_registry.py` skeleton 의 server-side
counterpart. wire format = base64 + JSON (한글 UTF-8 보존 ensure_ascii=False).

설계 결정
---------
- 모든 endpoint = auth_middleware 의 Bearer 검증 의무 (PUBLIC_PATHS 외).
- request['user_id'] = middleware 주입. body 의 user_id 별도 검증 없음
  (자신 의 device 만 조작 가능).
- DELETE = soft-delete (status='revoked'). hard-delete = 별도 cycle.
- base64 길이 검증 = X25519 32 byte raw (44 char base64 padded).
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from aiohttp import web

from server.db.repositories import devices as devices_repo
from server.db.repositories.user_activity import ActivityAction, log_activity
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)


_X25519_KEY_BYTES = 32


def _decode_pubkey(b64: str, *, field_name: str) -> bytes:
    """base64 string → 32 byte X25519 공개 키. 무효 = 400."""

    try:
        raw = base64.b64decode(b64, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise web.HTTPBadRequest(reason=f"{field_name} base64 디코딩 실패") from exc
    if len(raw) != _X25519_KEY_BYTES:
        raise web.HTTPBadRequest(
            reason=f"{field_name} 길이 = {len(raw)} (32 의무)"
        )
    return raw


def _encode_pubkey(raw: bytes | None) -> str | None:
    """bytes → base64 string. None = None."""

    if raw is None:
        return None
    return base64.b64encode(raw).decode("ascii")


def _device_row_to_wire(row: Any) -> dict:
    """``DeviceRow`` → JSON-safe dict (wire format)."""

    return {
        "device_id": row.device_id,
        "user_id": row.user_id,
        "label": row.label,
        "status": row.status,
        "bundle": {
            "identity_public": _encode_pubkey(row.identity_public),
            "signed_prekey_public": _encode_pubkey(row.signed_prekey_public),
            "one_time_prekey_public": _encode_pubkey(row.one_time_prekey_public),
        },
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "last_seen_at": row.last_seen_at.isoformat() if row.last_seen_at else None,
    }


async def _audit_device(
    request: web.Request,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: int | None,
    metadata: dict | None = None,
) -> None:
    """cycle 122 — DEVICE_REGISTER / DEVICE_REVOKE audit helper.

    pool 부재 graceful skip + 모든 예외 swallow. user_activity_log INSERT.
    """

    pool = request.app.get("db_pool")
    if pool is None:
        return
    try:
        await log_activity(
            pool,
            user_id=user_id,
            action=action,
            target_id=target_id,
            ip_address=extract_client_ip(request),
            user_agent=request.headers.get("User-Agent", "")[:255] or None,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "device audit 실패 user_id=%d action=%s: %s",
            user_id,
            action.value,
            exc,
        )


async def _read_json(request: web.Request) -> dict:
    """request body JSON 파싱 — 무효 = 400."""

    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001 - aiohttp json 다양한 예외 catch-all
        raise web.HTTPBadRequest(reason="JSON 파싱 실패") from exc


async def handle_register_device(request: web.Request) -> web.Response:
    """POST /api/devices — device 등록.

    body = ``{device_id, label?, bundle: {identity_public, signed_prekey_public, one_time_prekey_public?}}``.
    user_id = middleware 주입 (Bearer 토큰 기반).
    """

    user_id = request["user_id"]
    body = await _read_json(request)

    device_id = body.get("device_id", "").strip()
    if not device_id:
        raise web.HTTPBadRequest(reason="device_id 필수")
    if len(device_id) > 64:
        raise web.HTTPBadRequest(reason="device_id 길이 = 64 상한")

    label = (body.get("label") or "").strip()
    if len(label) > 128:
        raise web.HTTPBadRequest(reason="label 길이 = 128 상한")

    bundle = body.get("bundle")
    if not isinstance(bundle, dict):
        raise web.HTTPBadRequest(reason="bundle 필수 (dict)")

    identity_public = _decode_pubkey(
        bundle.get("identity_public", ""), field_name="identity_public"
    )
    signed_prekey_public = _decode_pubkey(
        bundle.get("signed_prekey_public", ""), field_name="signed_prekey_public"
    )

    opk_b64 = bundle.get("one_time_prekey_public")
    one_time_prekey_public = (
        _decode_pubkey(opk_b64, field_name="one_time_prekey_public")
        if opk_b64
        else None
    )

    pool = request.app["db_pool"]

    try:
        new_id = await devices_repo.insert_device(
            pool,
            device_id=device_id,
            user_id=user_id,
            label=label,
            identity_public=identity_public,
            signed_prekey_public=signed_prekey_public,
            one_time_prekey_public=one_time_prekey_public,
        )
    except Exception as exc:  # MariaDB 1062 UNIQUE 위반 catch
        msg = str(exc)
        if "1062" in msg or "Duplicate" in msg:
            return web.json_response(
                {"error": "duplicate_device_id", "message": "device_id 중복"},
                status=409,
            )
        log.exception("device 등록 실패 — user_id=%s device_id=%s", user_id, device_id)
        raise web.HTTPInternalServerError(reason="device 등록 실패") from exc

    # cycle 122 — DEVICE_REGISTER audit
    await _audit_device(
        request,
        user_id=user_id,
        action=ActivityAction.DEVICE_REGISTER,
        target_id=new_id,
        metadata={"device_id": device_id, "label": label or None},
    )

    return web.json_response(
        {"ok": True, "id": new_id, "device_id": device_id},
        status=201,
    )


async def handle_list_devices(request: web.Request) -> web.Response:
    """GET /api/devices — 현재 사용자 의 active device 목록."""

    user_id = request["user_id"]
    pool = request.app["db_pool"]

    include_revoked_raw = request.query.get("include_revoked", "").lower()
    include_revoked = include_revoked_raw in {"1", "true", "yes"}

    rows = await devices_repo.get_devices_by_user(
        pool, user_id, include_revoked=include_revoked
    )

    payload = {
        "ok": True,
        "user_id": user_id,
        "devices": [_device_row_to_wire(row) for row in rows],
        "count": len(rows),
    }
    return web.json_response(payload)


async def handle_revoke_device(request: web.Request) -> web.Response:
    """DELETE /api/devices/<device_id> — device revoke (soft-delete)."""

    user_id = request["user_id"]
    device_id = request.match_info.get("device_id", "").strip()
    if not device_id:
        raise web.HTTPBadRequest(reason="device_id 경로 변수 부재")

    pool = request.app["db_pool"]
    revoked = await devices_repo.revoke_device(pool, device_id, user_id)
    if not revoked:
        return web.json_response(
            {"error": "not_found_or_already_revoked", "device_id": device_id},
            status=404,
        )
    # cycle 122 — DEVICE_REVOKE audit (device_id 자체 = metadata, row PK None)
    await _audit_device(
        request,
        user_id=user_id,
        action=ActivityAction.DEVICE_REVOKE,
        target_id=None,
        metadata={"device_id": device_id},
    )
    return web.json_response({"ok": True, "device_id": device_id})


def register_devices_routes(app: web.Application) -> None:
    """aiohttp Application 에 devices 3 endpoint 등록."""

    app.router.add_post("/api/devices", handle_register_device)
    app.router.add_get("/api/devices", handle_list_devices)
    app.router.add_delete("/api/devices/{device_id}", handle_revoke_device)
