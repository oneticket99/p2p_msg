# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 제어 endpoint skeleton — Phase 5 Item 5 진입 prerequisite.

본 module = audit hook + skeleton response 의무 단. 실 Quartz / BitBlt / X11
binding = Phase 5 본격 cycle 166~180 의 별개 작업. 본 사이클 132 의 목표는
DB audit endpoint coverage 15 → 18 ActivityAction 의 wiring + test 의무.

엔드포인트:
- POST /api/remote/request — 원격 제어 요청 (patternA 도움 / patternB 제어)
- POST /api/remote/grant — target 사용자 의 명시 grant
- POST /api/remote/revoke — granter 또는 target 의 명시 revoke

설계 결정
---------
- 모든 endpoint = audit hook 의무 (REMOTE_REQUEST / REMOTE_GRANT / REMOTE_REVOKE).
- pool 부재 = graceful skip (DB_ENABLED=0 dev 정합).
- 실 세션 생성 / WebRTC 의 signaling = Phase 5 본격 별개.
- user_id 의 middleware 주입 의무 (auth_middleware 통과 가정).
"""
from __future__ import annotations

import logging
from typing import Optional

from aiohttp import web

from server.db.repositories.user_activity import ActivityAction, log_activity
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)


async def _audit_remote(
    req: web.Request,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int],
    metadata: dict,
) -> None:
    """한글 주석 — pool 부재 graceful + 예외 swallow.

    log_activity 의 wrapper — endpoint 응답 무영향 의무. 실패 시 warning log
    만 남기고 endpoint 의 200 응답 유지.
    """

    pool = req.app.get("db_pool")
    if pool is None:
        return
    try:
        ua = (req.headers.get("User-Agent", "") or "")[:255]
        await log_activity(
            pool,
            user_id=user_id,
            action=action,
            target_id=target_id,
            ip_address=extract_client_ip(req),
            user_agent=ua,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[remote] audit fail user_id=%d action=%s err=%r",
            user_id,
            action.value,
            exc,
        )


async def handle_remote_request(req: web.Request) -> web.Response:
    """원격 제어 요청 — patternA (도움 요청) 또는 patternB (제어 요청).

    Phase 5 skeleton — 실 세션 생성 + WebRTC signaling = 별개 cycle 166+.
    body schema = ``{target_user_id: int, pattern: "help"|"control"}``.
    """

    user_id = req.get("user_id", 0) or 0
    body = await req.json() if req.content_length else {}
    target_user_id = body.get("target_user_id")
    pattern = body.get("pattern", "help")
    await _audit_remote(
        req,
        user_id,
        ActivityAction.REMOTE_REQUEST,
        target_user_id,
        {"pattern": pattern},
    )
    return web.json_response(
        {"ok": True, "status": "pending", "pattern": pattern}, status=200
    )


async def handle_remote_grant(req: web.Request) -> web.Response:
    """원격 제어 승인 — target 사용자 의 명시 grant.

    Phase 5 skeleton — 실 세션 token + WebRTC offer/answer = 별개 cycle.
    body schema = ``{request_id: int, requester_user_id: int}``.
    """

    user_id = req.get("user_id", 0) or 0
    body = await req.json() if req.content_length else {}
    request_id = body.get("request_id")
    requester_user_id = body.get("requester_user_id")
    await _audit_remote(
        req,
        user_id,
        ActivityAction.REMOTE_GRANT,
        requester_user_id,
        {"request_id": request_id},
    )
    return web.json_response(
        {"ok": True, "status": "granted", "request_id": request_id}, status=200
    )


async def handle_remote_revoke(req: web.Request) -> web.Response:
    """원격 제어 해제 — granter 또는 target 의 명시 revoke.

    Phase 5 skeleton — 실 세션 close + WebRTC peer close = 별개 cycle.
    body schema = ``{session_id: int, target_user_id: int}``.
    """

    user_id = req.get("user_id", 0) or 0
    body = await req.json() if req.content_length else {}
    session_id = body.get("session_id")
    target_user_id = body.get("target_user_id")
    await _audit_remote(
        req,
        user_id,
        ActivityAction.REMOTE_REVOKE,
        target_user_id,
        {"session_id": session_id},
    )
    return web.json_response(
        {"ok": True, "status": "revoked", "session_id": session_id}, status=200
    )


def register_remote_routes(app: web.Application) -> None:
    """한글 주석 — server.main 의 entry 등록.

    3 route 의 일괄 등록 — request / grant / revoke. Phase 5 본격 cycle 의
    Phase 5 본격 cycle 166+ 의 actual binding 직전 의 skeleton wiring.
    """

    app.router.add_post("/api/remote/request", handle_remote_request)
    app.router.add_post("/api/remote/grant", handle_remote_grant)
    app.router.add_post("/api/remote/revoke", handle_remote_revoke)
    log.info("[api] remote 3 endpoint 등록 완료 (skeleton)")
