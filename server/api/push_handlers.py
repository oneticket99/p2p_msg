# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — FCM device token register/unregister (cycle 169.446 신설).

엔드포인트:
- POST /api/push/register — 디바이스 FCM token 등록 (사용자 self token)
- DELETE /api/push/tokens/{token_id} — 디바이스 token 비활성 (사용자 self token)
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from server.db.repositories import device_tokens as _dt_repo

log = logging.getLogger(__name__)


async def handle_register_token(request: web.Request) -> web.Response:
    """POST /api/push/register — 디바이스 FCM token UPSERT.

    body = ``{fcm_token: str, platform: str, device_label: str?}``.
    응답 = ``{token_id: int}``.
    """
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(reason="JSON body 의무")
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")
    fcm_token = str(body.get("fcm_token", "")).strip()
    platform = str(body.get("platform", "")).strip().lower()
    device_label = body.get("device_label")
    if not fcm_token:
        raise web.HTTPBadRequest(reason="fcm_token 빈 차단")
    if platform not in ("macos", "windows", "linux", "ios", "android", "web"):
        raise web.HTTPBadRequest(reason="platform ENUM 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    try:
        token_id = await _dt_repo.upsert_token(
            pool, user_id=user_id, fcm_token=fcm_token, platform=platform,
            device_label=device_label,
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc))
    log.info(
        "[push] register user_id=%d platform=%s token_id=%d",
        user_id, platform, token_id,
    )
    return web.json_response({"token_id": token_id}, status=201)


async def handle_unregister_token(request: web.Request) -> web.Response:
    """DELETE /api/push/tokens/{token_id} — token 비활성 chain."""
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        token_id = int(request.match_info["token_id"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(reason="token_id 정수 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    # 한글 주석 — owner 검증: device_tokens WHERE id=? AND user_id=?
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT user_id FROM device_tokens WHERE id = %s LIMIT 1",
                (token_id,),
            )
            row = await cur.fetchone()
    if row is None:
        raise web.HTTPNotFound(reason=f"token_id={token_id} 부재")
    if int(row[0]) != user_id:
        raise web.HTTPForbidden(reason="token owner 만 unregister 가능")
    ok = await _dt_repo.deactivate_token(pool, token_id=token_id)
    return web.json_response({"deactivated": ok, "token_id": token_id})


def register_push_routes(app: web.Application) -> None:
    """server.main register entry — 2 endpoint 등록."""
    app.router.add_post("/api/push/register", handle_register_token)
    app.router.add_delete("/api/push/tokens/{token_id}", handle_unregister_token)
    log.info("[api] push 2 endpoint 등록 완료 (cycle 169.446)")
