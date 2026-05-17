# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — Phase 1 auth 흐름.

엔드포인트:
- POST /api/auth/register — 회원가입 + OTP 발송
- POST /api/auth/verify — signup OTP 검증
- POST /api/auth/login — 로그인 + 세션 토큰
- POST /api/auth/reset/request — 비번 재설정 OTP 발송
- POST /api/auth/reset/consume — OTP + 비번 갱신
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiohttp import web

from server.auth import login as login_uc
from server.auth import register as register_uc
from server.auth import reset_password as reset_uc
from server.auth import verify as verify_uc
from server.auth.exceptions import AuthError

log = logging.getLogger(__name__)


def _json_error(exc: AuthError) -> web.Response:
    """AuthError → JSON 응답 + 적정 HTTP status."""

    return web.json_response(
        {"error": exc.code, "message": str(exc)},
        status=exc.http_status,
    )


async def _read_json(request: web.Request) -> dict[str, Any]:
    """요청 body JSON 파싱 — 형식 오류 = 400."""

    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001
        raise web.HTTPBadRequest(reason=f"JSON 파싱 실패: {exc}")


async def handle_register(request: web.Request) -> web.Response:
    """POST /api/auth/register"""

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    try:
        user_id = await register_uc.register_user(
            pool,
            email=str(payload.get("email", "")),
            username=str(payload.get("username", "")),
            password=str(payload.get("password", "")),
        )
    except ValueError as exc:
        return web.json_response(
            {"error": "VALIDATION", "message": str(exc)}, status=400
        )
    except AuthError as exc:
        return _json_error(exc)

    return web.json_response(
        {"ok": True, "user_id": user_id, "next": "verify_otp"},
        status=201,
    )


async def handle_verify(request: web.Request) -> web.Response:
    """POST /api/auth/verify"""

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    try:
        user_id = await verify_uc.verify_signup_otp(
            pool,
            email=str(payload.get("email", "")),
            code=str(payload.get("code", "")),
        )
    except AuthError as exc:
        return _json_error(exc)

    return web.json_response({"ok": True, "user_id": user_id})


async def handle_login(request: web.Request) -> web.Response:
    """POST /api/auth/login"""

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    try:
        user_id, token = await login_uc.login_user(
            pool,
            email=str(payload.get("email", "")),
            password=str(payload.get("password", "")),
        )
    except AuthError as exc:
        return _json_error(exc)

    # 세션 store 등록 (Phase 1 = in-memory dict)
    request.app["session_store"][token] = user_id

    return web.json_response({"ok": True, "user_id": user_id, "token": token})


async def handle_reset_request(request: web.Request) -> web.Response:
    """POST /api/auth/reset/request — silent success (enumeration 방어)."""

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    await reset_uc.request_password_reset(pool, str(payload.get("email", "")))
    return web.json_response({"ok": True})


async def handle_reset_consume(request: web.Request) -> web.Response:
    """POST /api/auth/reset/consume"""

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    try:
        user_id = await reset_uc.consume_password_reset(
            pool,
            email=str(payload.get("email", "")),
            code=str(payload.get("code", "")),
            new_password=str(payload.get("new_password", "")),
        )
    except ValueError as exc:
        return web.json_response(
            {"error": "VALIDATION", "message": str(exc)}, status=400
        )
    except AuthError as exc:
        return _json_error(exc)

    return web.json_response({"ok": True, "user_id": user_id})


def register_auth_routes(app: web.Application) -> None:
    """auth route 등록 — server.main 에서 호출."""

    app.router.add_post("/api/auth/register", handle_register)
    app.router.add_post("/api/auth/verify", handle_verify)
    app.router.add_post("/api/auth/login", handle_login)
    app.router.add_post("/api/auth/reset/request", handle_reset_request)
    app.router.add_post("/api/auth/reset/consume", handle_reset_consume)
    log.info("[api] auth 5 endpoint 등록 완료")
