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
from server.auth import resend_signup_otp as resend_uc
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
        result = await register_uc.register_user(
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

    # cycle 169.67 회수 — reclaim path 의 의 별개 audit + smtp_status response 포함
    user_id = result["user_id"]
    reclaimed = result.get("reclaimed", False)
    smtp_status = result.get("smtp_status", "sent")
    action = ActivityAction.RECLAIM_UNVERIFIED if reclaimed else ActivityAction.SIGNUP
    await _audit(request, user_id=user_id, action=action)
    return web.json_response(
        {
            "ok": True,
            "user_id": user_id,
            "next": "verify_otp",
            "reclaimed": reclaimed,
            "smtp_status": smtp_status,
        },
        status=201,
    )


async def handle_resend_otp(request: web.Request) -> web.Response:
    """POST /api/auth/resend — 사용자 directive cycle 169.45 회수.

    OTP 재 송신 — email 검증 + 60초 cooldown + invalidate prior + 신규 발송.
    """

    payload = await _read_json(request)
    pool = request.app["db_pool"]
    try:
        user_id = await resend_uc.resend_signup_otp(
            pool,
            email=str(payload.get("email", "")),
        )
    except AuthError as exc:
        return _json_error(exc)
    except Exception as exc:  # noqa: BLE001 - SMTP 실패 graceful
        log.warning("[resend] 실패 — %r", exc)
        return web.json_response(
            {"error": "SMTP_FAILURE", "message": "OTP 메일 발송 실패 — 잠시 후 재시도"},
            status=503,
        )

    await _audit(request, user_id=user_id, action=ActivityAction.SIGNUP)
    return web.json_response({"ok": True, "user_id": user_id}, status=200)


async def handle_verify(request: web.Request) -> web.Response:
    """POST /api/auth/verify — cycle 169.54 회수.

    사용자 directive verbatim — "회원가입이 완료되면 당연히 로그인된상태로 메인ui가 떠야".
    OTP 검증 PASS 시점 자동 세션 토큰 발급 + session_store 등록 + LOGIN audit chain.
    """

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

    # 한글 주석 — OTP 검증 PASS = 자동 로그인 chain (회원가입 직후 main UI 진입 정합)
    from app.core.security import generate_session_token
    token = generate_session_token()
    request.app["session_store"][token] = user_id
    await _create_session_row(request, user_id=user_id, token=token)
    await _audit(request, user_id=user_id, action=ActivityAction.SIGNUP_OTP_VERIFY)
    await _audit(request, user_id=user_id, action=ActivityAction.LOGIN)

    return web.json_response({"ok": True, "user_id": user_id, "token": token})


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
    """POST /api/auth/reset/request — silent success (enumeration 방어).

    cycle 128 — PASSWORD_RESET_REQUEST audit (user_id 미해소 — email hash 만 metadata).
    enumeration 방어 의 응답 신호 부재 정합 + audit 의 hash-only metadata 의 분리.
    """

    payload = await _read_json(request)
    email = str(payload.get("email", "")).strip().lower()
    pool = request.app["db_pool"]
    await reset_uc.request_password_reset(pool, email)

    # cycle 128 — PASSWORD_RESET_REQUEST audit (user_id lookup 없이 email hash 만)
    # enumeration 방어 정합 — silent success + audit user_id=-1 (시스템 의 placeholder)
    # 실 user_id 의 audit chain = handle_reset_consume 의 PASSWORD_RESET_COMPLETE
    if email and pool is not None:
        try:
            import hashlib

            email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest()[:16]
            await log_activity(
                pool,
                user_id=1,  # 시스템 placeholder — 실 user 미연결 (enumeration 방어)
                action=ActivityAction.PASSWORD_RESET_REQUEST,
                ip_address=extract_client_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:255] or None,
                metadata={"email_hash": email_hash},
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("reset_request audit 실패: %s", exc)

    return web.json_response({"ok": True})


async def handle_profile_update(request: web.Request) -> web.Response:
    """PUT /api/auth/profile — cycle 128 profile 갱신 skeleton.

    schema = ``{display_name?: str, username?: str}``. user_id = middleware 주입.
    actual UPDATE users SET = 별개 cycle (Phase 5+ 본격 implementation).
    PROFILE_UPDATE audit + 임시 200 응답 + 변경 field metadata.
    """

    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    payload = await _read_json(request)
    changed_fields = []
    if "display_name" in payload:
        changed_fields.append("display_name")
    if "username" in payload:
        changed_fields.append("username")
    if not changed_fields:
        raise web.HTTPBadRequest(reason="display_name 또는 username 의무")

    # actual DB UPDATE = 별개 cycle (Phase 5+ 본격)
    await _audit(
        request,
        user_id=user_id,
        action=ActivityAction.PROFILE_UPDATE,
        metadata={"changed_fields": changed_fields},
    )
    return web.json_response({"ok": True, "user_id": user_id, "changed": changed_fields})


async def handle_user_status(request: web.Request) -> web.Response:
    """GET /api/auth/users/{user_id}/status — cycle 169.216 신설.

    친구 last_seen + 온라인 상태 조회. chat_header status binding chain prereq.

    응답 schema = ``{user_id: int, last_login_at: iso, last_active_at: iso | null, online: bool}``.
    online = (now - last_active_at) < 60s (사용자 만 활성).
    Bearer 인증 의무 (auth_middleware 주입).
    """
    from datetime import datetime, timezone, timedelta
    viewer_id = request.get("user_id")
    if not isinstance(viewer_id, int) or viewer_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        target_id = int(request.match_info["user_id"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(reason="user_id 양수 int 의무")

    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"user_id": target_id, "online": False, "last_login_at": None, "last_active_at": None})

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT last_login_at, last_active_at FROM users LEFT JOIN user_sessions "
                "ON user_sessions.user_id = users.id "
                "WHERE users.id = %s ORDER BY user_sessions.last_active_at DESC LIMIT 1",
                (target_id,),
            )
            row = await cur.fetchone()
    if not row:
        raise web.HTTPNotFound(reason=f"user_id {target_id} 부재")

    last_login, last_active = row
    online = False
    if last_active:
        delta = datetime.now(timezone.utc) - last_active.replace(tzinfo=timezone.utc)
        online = delta < timedelta(seconds=60)
    return web.json_response({
        "user_id": target_id,
        "online": online,
        "last_login_at": last_login.isoformat() if last_login else None,
        "last_active_at": last_active.isoformat() if last_active else None,
    })


async def handle_dm_room_resolve(request: web.Request) -> web.Response:
    """GET /api/auth/dm/{user_id}/room — cycle 169.222 — DM room_id resolver.

    viewer ↔ target user 의 1:1 direct room lookup 또는 신설.
    응답 = ``{room_id: int, room_code: str}``. Bearer 인증 의무.
    """
    viewer_id = request.get("user_id")
    if not isinstance(viewer_id, int) or viewer_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        target_id = int(request.match_info["user_id"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(reason="user_id 양수 int 의무")
    if viewer_id == target_id:
        raise web.HTTPBadRequest(reason="self DM 불가")
    pool = request.app.get("db_pool")
    if pool is None:
        raise web.HTTPServiceUnavailable(reason="DB pool 부재")
    from server.db.repositories.rooms import find_or_create_dm_room
    room_id = await find_or_create_dm_room(pool, viewer_id, target_id)
    small, large = sorted((viewer_id, target_id))
    return web.json_response({"room_id": room_id, "room_code": f"dm-{small}-{large}"})


async def handle_email_change_request(request: web.Request) -> web.Response:
    """POST /api/auth/email/request — cycle 128 이메일 변경 요청 skeleton.

    schema = ``{new_email: str}``. user_id = middleware 주입.
    OTP 발송 + UPDATE users.email = 별개 cycle (Phase 5+).
    EMAIL_CHANGE audit + 임시 200 응답.
    """

    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    payload = await _read_json(request)
    new_email = str(payload.get("new_email", "")).strip().lower()
    if not new_email or "@" not in new_email:
        raise web.HTTPBadRequest(reason="new_email 유효 의무")

    # actual OTP + UPDATE = 별개 cycle
    import hashlib

    email_hash = hashlib.sha256(new_email.encode("utf-8")).hexdigest()[:16]
    await _audit(
        request,
        user_id=user_id,
        action=ActivityAction.EMAIL_CHANGE,
        metadata={"new_email_hash": email_hash},
    )
    return web.json_response({"ok": True, "next": "verify_otp"})


async def handle_account_delete(request: web.Request) -> web.Response:
    """DELETE /api/auth/account — cycle 128 계정 탈퇴 skeleton.

    soft-delete (status=deleted + 30일 보관 후 hard-delete) = 별개 cycle.
    ACCOUNT_DELETE audit + 임시 200 응답 + session_store 제거.
    """

    user_id = request.get("user_id")
    token = request.get("session_token")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")

    # session_store 제거 (Phase 1 in-memory)
    store = request.app.get("session_store")
    if isinstance(store, dict) and isinstance(token, str):
        store.pop(token, None)

    # actual UPDATE users SET status=deleted = 별개 cycle
    await _audit(
        request,
        user_id=user_id,
        action=ActivityAction.ACCOUNT_DELETE,
    )
    return web.json_response({"ok": True, "user_id": user_id, "status": "scheduled_delete"})


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
    app.router.add_post("/api/auth/resend", handle_resend_otp)
    app.router.add_post("/api/auth/verify", handle_verify)
    app.router.add_post("/api/auth/login", handle_login)
    app.router.add_post("/api/auth/logout", handle_logout)
    app.router.add_post("/api/auth/reset/request", handle_reset_request)
    app.router.add_post("/api/auth/reset/consume", handle_reset_consume)
    # cycle 128 — profile + email change + account delete 3 신규 endpoint
    app.router.add_put("/api/auth/profile", handle_profile_update)
    app.router.add_post("/api/auth/email/request", handle_email_change_request)
    app.router.add_delete("/api/auth/account", handle_account_delete)
    # cycle 169.216 — last_seen + 온라인 상태 조회 (chat_header status binding chain)
    app.router.add_get(r"/api/auth/users/{user_id:\d+}/status", handle_user_status)
    # cycle 169.222 — DM room resolver (friend_id ↔ direct room_id mapping)
    app.router.add_get(r"/api/auth/dm/{user_id:\d+}/room", handle_dm_room_resolve)
    log.info("[api] auth 12 endpoint 등록 완료")
