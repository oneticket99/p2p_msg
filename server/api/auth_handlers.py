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

import hashlib
import logging
from typing import Any, Awaitable, Callable, Optional

from aiohttp import web

from server.auth import login as login_uc
from server.auth import register as register_uc
from server.auth import reset_password as reset_uc
from server.auth import verify as verify_uc
from server.auth.exceptions import AuthError
from server.db.repositories.user_activity import (
    ActivityAction,
    SessionEndReason,
    close_session,
    create_session,
    log_activity,
)
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)


def _json_error(exc: AuthError) -> web.Response:
    """AuthError → JSON 응답 + 적정 HTTP status."""

    return web.json_response(
        {"error": exc.code, "message": str(exc)},
        status=exc.http_status,
    )


async def _audit(
    request: web.Request,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> None:
    """log_activity wrapper — pool 부재 시 graceful skip (dev DB_ENABLED=0 정합).

    cycle 119 — DB audit migration 0003 의 actual call site wiring. 모든 auth
    endpoint 의 success 직후 호출 의무. 실패 = log warning + endpoint 응답 무영향.
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
        log.warning("audit log 실패 (user_id=%d action=%s): %s", user_id, action.value, exc)


async def _create_session_row(
    request: web.Request,
    *,
    user_id: int,
    token: str,
) -> None:
    """user_sessions row 생성 — pool 부재 시 graceful skip."""

    pool = request.app.get("db_pool")
    if pool is None:
        return
    try:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        await create_session(
            pool,
            user_id=user_id,
            session_token_hash=token_hash,
            ip_address=extract_client_ip(request) or "0.0.0.0",
            user_agent=request.headers.get("User-Agent", "")[:255] or None,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("session 생성 실패 (user_id=%d): %s", user_id, exc)


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

    await _audit(request, user_id=user_id, action=ActivityAction.SIGNUP)
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

    await _audit(request, user_id=user_id, action=ActivityAction.SIGNUP_OTP_VERIFY)
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

    # cycle 119 — user_sessions row 생성 + LOGIN audit
    await _create_session_row(request, user_id=user_id, token=token)
    await _audit(request, user_id=user_id, action=ActivityAction.LOGIN)

    return web.json_response({"ok": True, "user_id": user_id, "token": token})


async def handle_logout(request: web.Request) -> web.Response:
    """POST /api/auth/logout — cycle 121.

    session_store 에서 token 제거 + user_sessions row 의 disconnected_at +
    end_reason=logout 갱신 + log_activity(LOGOUT) audit. auth_middleware 통과
    필수 (user_id + session_token request 의 등록 보장).
    """

    user_id = request.get("user_id")
    token = request.get("session_token")
    if not isinstance(user_id, int) or user_id <= 0 or not isinstance(token, str):
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    # session_store 제거 (Phase 1 in-memory dict)
    store = request.app.get("session_store")
    if isinstance(store, dict):
        store.pop(token, None)

    # user_sessions row close — graceful skip (pool 부재 시)
    pool = request.app.get("db_pool")
    if pool is not None:
        try:
            token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
            await close_session(
                pool,
                session_token_hash=token_hash,
                end_reason=SessionEndReason.LOGOUT,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("logout close_session 실패 user_id=%d: %s", user_id, exc)

    await _audit(request, user_id=user_id, action=ActivityAction.LOGOUT)
    return web.json_response({"ok": True})


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

    # cycle 122 — PASSWORD_RESET_COMPLETE audit
    await _audit(request, user_id=user_id, action=ActivityAction.PASSWORD_RESET_COMPLETE)
    return web.json_response({"ok": True, "user_id": user_id})


def register_auth_routes(app: web.Application) -> None:
    """auth route 등록 — server.main 에서 호출."""

    app.router.add_post("/api/auth/register", handle_register)
    app.router.add_post("/api/auth/verify", handle_verify)
    app.router.add_post("/api/auth/login", handle_login)
    app.router.add_post("/api/auth/logout", handle_logout)
    app.router.add_post("/api/auth/reset/request", handle_reset_request)
    app.router.add_post("/api/auth/reset/consume", handle_reset_consume)
    log.info("[api] auth 5 endpoint 등록 완료")
