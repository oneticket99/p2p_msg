# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp 세션 검증 미들웨어 — Authorization Bearer 헤더 검증."""

from __future__ import annotations

import logging
from typing import Any, Callable

from aiohttp import web

log = logging.getLogger(__name__)

_HEADER_AUTH = "Authorization"
_BEARER_PREFIX = "Bearer "

# 본 set 에 등록된 path 는 인증 skip (공개 endpoint)
_PUBLIC_PATHS = frozenset({
    "/health",
    "/api/auth/register",
    "/api/auth/verify",
    "/api/auth/login",
    "/api/auth/reset/request",
    "/api/auth/reset/consume",
})


@web.middleware
async def auth_middleware(
    request: web.Request,
    handler: Callable[[web.Request], Any],
) -> web.StreamResponse:
    """Authorization Bearer 검증 + request['user_id'] 주입.

    공개 endpoint (_PUBLIC_PATHS) 는 skip.
    """

    if request.path in _PUBLIC_PATHS:
        return await handler(request)

    auth_header = request.headers.get(_HEADER_AUTH, "")
    if not auth_header.startswith(_BEARER_PREFIX):
        raise web.HTTPUnauthorized(reason="Authorization Bearer 헤더 부재")

    token = auth_header[len(_BEARER_PREFIX):].strip()
    if not token:
        raise web.HTTPUnauthorized(reason="빈 토큰")

    # 세션 store lookup — 실제 store = app['session_store'] (Phase 1 = in-memory dict)
    session_store = request.app.get("session_store")
    if session_store is None:
        raise web.HTTPInternalServerError(reason="session_store 부재")

    user_id = session_store.get(token)
    if user_id is None:
        raise web.HTTPUnauthorized(reason="세션 토큰 무효")

    request["user_id"] = user_id
    return await handler(request)
