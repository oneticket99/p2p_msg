# SPDX-License-Identifier: GPL-3.0-or-later
"""원격 제어 endpoint skeleton — Phase 5 Item 5 진입 prerequisite.

역할 — 친구간 원격 데스크탑 제어(패턴 A 도움 / 패턴 B 제어)의 요청·승인·해제
의도를 audit 로 남기는 skeleton. 실 Quartz / BitBlt / X11 capture binding 은
Phase 5 본격 cycle 166~180 의 별개 작업이고, 본 module 은 audit hook + skeleton
응답까지만 책임진다(사이클 132 목표 = DB audit ActivityAction wiring + test).

계층 위치 — server API handler 계층(정본 §E). auth_middleware 통과(user_id 주입
가정) 후 진입하며, audit 영속화는 `user_activity` repository 에 위임한다.

의존성 — aiohttp `web` + `user_activity`(`log_activity`/`ActivityAction`) +
`activity` 미들웨어(`extract_client_ip`) + `request.app["db_pool"]`. 실 세션
생성/WebRTC signaling 은 본 module 범위 외.

범위 한계 — 상태머신/세션 토큰/WebRTC offer-answer 부재. 모든 endpoint 는
audit 만 남기고 고정 status(pending/granted/revoked) 응답을 돌려준다. db_pool
부재 시 audit graceful skip(DB_ENABLED=0 dev 정합) — 응답은 200 유지.

엔드포인트 카탈로그(실 함수 3 + audit helper + register):
- `handle_remote_request`  POST /api/remote/request — REMOTE_REQUEST audit.
- `handle_remote_grant`    POST /api/remote/grant   — REMOTE_GRANT audit.
- `handle_remote_revoke`   POST /api/remote/revoke  — REMOTE_REVOKE audit.
- `_audit_remote` — log_activity wrapper(응답 무영향 보장).
- `register_remote_routes` — server.main 등록 entry.

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
    """audit 기록 wrapper — pool 부재 graceful + 예외 swallow.

    의도 — endpoint 응답 경로가 audit 실패에 영향받지 않게 격리한다(audit 는
    부가 효과이지 응답 조건이 아니다).

    Parameters — req(요청), user_id(행위자), action(ActivityAction ENUM),
        target_id(대상 사용자, 부재 가능), metadata(부가 dict).
    부작용 — `user_activity` INSERT(DB write). pool 부재 시 즉시 반환(skip),
        예외 발생 시 warning 로그만 남기고 삼켜 endpoint 200 을 보존한다.
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

    인증 — auth_middleware 주입 user_id 가정(부재 시 0 fallback).
    Parameters — body ``{target_user_id: int, pattern: "help"|"control"}``.
    Returns — 200 + ``{ok, status:"pending", pattern}``(고정 응답).
    부작용 — REMOTE_REQUEST audit(DB write, graceful). 실 세션 생성 부재.
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

    인증 — auth_middleware 주입 user_id 가정(부재 시 0 fallback).
    Parameters — body ``{request_id: int, requester_user_id: int}``.
    Returns — 200 + ``{ok, status:"granted", request_id}``(고정 응답).
    부작용 — REMOTE_GRANT audit(DB write, graceful). 실 세션 token 발급 부재.
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

    인증 — auth_middleware 주입 user_id 가정(부재 시 0 fallback).
    Parameters — body ``{session_id: int, target_user_id: int}``.
    Returns — 200 + ``{ok, status:"revoked", session_id}``(고정 응답).
    부작용 — REMOTE_REVOKE audit(DB write, graceful). 실 세션 close 부재.
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
    """server.main entry — 3 route(request/grant/revoke) 일괄 등록.

    Phase 5 본격 cycle 166+ 의 actual capture binding 직전 단계의 skeleton
    wiring 이다(현 시점 = audit + 고정 응답).
    """

    app.router.add_post("/api/remote/request", handle_remote_request)
    app.router.add_post("/api/remote/grant", handle_remote_grant)
    app.router.add_post("/api/remote/revoke", handle_remote_revoke)
    log.info("[api] remote 3 endpoint 등록 완료 (skeleton)")
