# SPDX-License-Identifier: GPL-3.0-or-later
"""emoji pack moderation admin endpoint — Phase 5 Item 3 cycle 144 + 147.

역할 — emoji 팩 moderation 큐 조회 + 승인/거부/DMCA takedown 결정을 처리한다.
`emoji_handlers.py` 의 후속 admin 전용 경로다.

계층 위치 — server API handler 계층(정본 §E). 전 endpoint admin 전용 —
auth_middleware 와 무관하게 자체 admin Bearer(env token strict 일치)로 보호한다.
영속화는 `emoji_packs` repository(`list_pending`/`update_moderation_status`)에 위임.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `emoji_packs` repository
(`ModerationStatus` ENUM 포함). admin 토큰은 env ``EMOJI_MODERATION_ADMIN_TOKEN``
주입(version_handlers VERSION_ADMIN_TOKEN 패턴 정합).

범위 한계 — moderation 결정 + 큐 조회만. audit DB 영속·bulk batch·cursor
pagination·DMCA notice 발신은 별개 cycle(148+).

엔드포인트 카탈로그(실 함수 4 + helper 4 + register):
- `handle_queue`    GET  /api/emoji/moderation/queue    — pending 목록(admin).
- `handle_approve`  POST /api/emoji/moderation/approve  — 승인(admin).
- `handle_reject`   POST /api/emoji/moderation/reject   — 거부(admin).
- `handle_dmca`     POST /api/emoji/moderation/dmca     — DMCA takedown(admin).
- `_check_admin_bearer`/`_parse_pack_id`/`_parse_pagination`/`_handle_decision`.

cycle 132 의 `emoji_handlers.py` 5 endpoint 의 후속 — admin moderation
4 endpoint 신설 (cycle 144) + cycle 147 의 list_pending actual binding.
owner role(admin Bearer token)만 access 가능.

엔드포인트 4종 (cycle 147 — queue 의 실 list_pending 연결 완료):
- GET  /api/emoji/moderation/queue    — pending 팩 list (admin only, pagination)
- POST /api/emoji/moderation/approve  — pack 승인 (admin only)
- POST /api/emoji/moderation/reject   — pack 거부 (admin only)
- POST /api/emoji/moderation/dmca     — pack DMCA takedown (admin only)

설계 결정
---------
- admin Bearer = EMOJI_MODERATION_ADMIN_TOKEN env 의 strict 일치 의무.
  (version_handlers.py 의 VERSION_ADMIN_TOKEN 패턴 정합.)
- repository binding = emoji_packs.update_moderation_status + list_pending.
- pool 부재 graceful 503 (DB_ENABLED=0 dev 정합).
- audit log = log.info 의 line (별개 cycle 의 DB 영속 audit table).
- queue 의 pagination = limit + offset query string (1~200 cap, 음수 차단).

본 cycle 의 범위 외 (별개 cycle 148+):
- audit log DB 영속 (admin_actions 테이블)
- bulk approve/reject batch endpoint
- pagination cursor-based (cycle 132 skeleton 정합)
- DMCA notice 본문 templating + 외부 발신
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from aiohttp import web

from server.db.repositories.emoji_packs import (
    ModerationStatus,
    list_pending,
    update_moderation_status,
)

log = logging.getLogger(__name__)

# admin Bearer 토큰 env 키 — version_handlers VERSION_ADMIN_TOKEN 정합
_ENV_ADMIN_TOKEN = "EMOJI_MODERATION_ADMIN_TOKEN"


def _check_admin_bearer(req: web.Request) -> Optional[web.Response]:
    """admin Bearer 검증 — env token 정합 시 None, 실패 시 401 응답 반환.

    Parameters
    ----------
    req : web.Request
        aiohttp 요청 객체.

    Returns
    -------
    Optional[web.Response]
        None = 통과, web.Response = 401 즉시 반환.
    """

    # env token 부재 시 401 fallback — skeleton 안전 default
    admin_token = os.environ.get(_ENV_ADMIN_TOKEN, "").strip()
    if not admin_token:
        return web.json_response(
            {
                "error": "admin only",
                "reason": "EMOJI_MODERATION_ADMIN_TOKEN unset",
            },
            status=401,
        )

    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return web.json_response(
            {"error": "admin only", "reason": "Bearer header missing"},
            status=401,
        )
    token = auth_header[len("Bearer ") :].strip()
    if token != admin_token:
        return web.json_response(
            {"error": "admin only", "reason": "token mismatch"}, status=401
        )
    return None


async def _parse_pack_id(req: web.Request) -> tuple[Optional[int], Optional[web.Response]]:
    """request body 의 pack_id 추출 + 검증 — (pack_id, error_response) 반환.

    Returns
    -------
    tuple
        (pack_id, None) = 통과, (None, web.Response) = 400 즉시 반환.
    """

    try:
        body = await req.json() if req.content_length else {}
    except Exception:
        return None, web.json_response({"error": "json invalid"}, status=400)
    if not isinstance(body, dict):
        return None, web.json_response({"error": "body object 의무"}, status=400)

    pack_id = body.get("pack_id")
    # pack_id 정수 + 양수 의무 — type 검증 strict
    if not isinstance(pack_id, int) or pack_id <= 0:
        return None, web.json_response(
            {"error": "pack_id 양수 정수 의무"}, status=400
        )
    return pack_id, None


def _parse_pagination(req: web.Request) -> tuple[int, int, Optional[web.Response]]:
    """query string limit/offset 추출 + 검증 — (limit, offset, error) 반환.

    Returns
    -------
    tuple
        (limit, offset, None) = 통과, (-, -, web.Response) = 400 즉시 반환.

    Notes
    -----
    - limit default 50 / 1~200 cap.
    - offset default 0 / 음수 차단.
    """

    # query string default — limit 50 + offset 0 + cap 200
    try:
        limit = int(req.query.get("limit", "50"))
        offset = int(req.query.get("offset", "0"))
    except (TypeError, ValueError):
        return 0, 0, web.json_response(
            {"error": "limit/offset 정수 의무"}, status=400
        )
    if limit <= 0 or limit > 200:
        return 0, 0, web.json_response(
            {"error": "limit 1~200 의무"}, status=400
        )
    if offset < 0:
        return 0, 0, web.json_response(
            {"error": "offset 음수 차단"}, status=400
        )
    return limit, offset, None


async def handle_queue(req: web.Request) -> web.Response:
    """GET /api/emoji/moderation/queue — pending 팩 list (admin only).

    cycle 147 — list_pending repository 호출 + pagination + JSON serialize.

    Query parameters
    ----------------
    limit : int = 50
        page size (1~200 cap).
    offset : int = 0
        page offset (음수 차단).

    응답:
        200: {"queue": [{"pack_id", "name", "slug", "owner_user_id", "created_at"}, ...],
              "limit", "offset", "count"}
        400: {"error": "limit/offset 무효"} — pagination 범위 위반
        401: {"error": "admin only"} — Bearer 부재 또는 불일치
        503: {"error": "db unavailable"} — pool 부재 graceful
        500: {"error": "internal"} — repository 예외
    """

    # admin Bearer 검증 — 실패 시 즉시 401
    auth_err = _check_admin_bearer(req)
    if auth_err is not None:
        return auth_err

    # pagination query 추출 + 검증
    limit, offset, pag_err = _parse_pagination(req)
    if pag_err is not None:
        return pag_err

    pool = req.app.get("db_pool")
    if pool is None:
        # dev 환경 의 DB_ENABLED=0 graceful 503
        return web.json_response({"error": "db unavailable"}, status=503)

    try:
        # cycle 147 — list_pending repository 의 직접 binding
        rows = await list_pending(pool, limit=limit, offset=offset)
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001
        log.warning("[emoji-moderation] GET /queue 실패 — %r", exc)
        return web.json_response({"error": "internal"}, status=500)

    # PendingPackRow → JSON dict 변환 (admin UI populate 용 5 field)
    queue_payload = [
        {
            "pack_id": r.id,
            "name": r.name,
            "slug": r.slug,
            "owner_user_id": r.owner_user_id,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    log.info(
        "[emoji-moderation] GET /queue limit=%d offset=%d count=%d",
        limit,
        offset,
        len(queue_payload),
    )
    return web.json_response(
        {
            "queue": queue_payload,
            "limit": limit,
            "offset": offset,
            "count": len(queue_payload),
        },
        status=200,
    )


async def _handle_decision(
    req: web.Request, new_status: ModerationStatus, log_label: str
) -> web.Response:
    """approve / reject / dmca 3 endpoint 의 공통 chain.

    Parameters
    ----------
    req : web.Request
        aiohttp 요청.
    new_status : ModerationStatus
        UPDATE 의 target ENUM.
    log_label : str
        audit log line label.

    Returns
    -------
    web.Response
        200 / 400 / 401 / 503 / 500.
    """

    # admin Bearer 검증 — 실패 시 즉시 401
    auth_err = _check_admin_bearer(req)
    if auth_err is not None:
        return auth_err

    pack_id, parse_err = await _parse_pack_id(req)
    if parse_err is not None:
        return parse_err

    pool = req.app.get("db_pool")
    if pool is None:
        return web.json_response({"error": "db unavailable"}, status=503)

    try:
        # repository 의 update_moderation_status 의 직접 binding
        rowcount = await update_moderation_status(
            pool, pack_id=pack_id, moderation_status=new_status
        )
    except ValueError as exc:
        return web.json_response({"error": str(exc)}, status=400)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "[emoji-moderation] %s pack_id=%d 실패 — %r",
            log_label,
            pack_id,
            exc,
        )
        return web.json_response({"error": "internal"}, status=500)

    # audit log — admin 결정 의 단일 line (별개 cycle 의 DB audit)
    log.info(
        "[emoji-moderation] %s pack_id=%d new=%s rowcount=%d",
        log_label,
        pack_id,
        new_status.value,
        rowcount,
    )
    return web.json_response(
        {
            "ok": True,
            "pack_id": pack_id,
            "moderation_status": new_status.value,
            "rowcount": rowcount,
        },
        status=200,
    )


async def handle_approve(req: web.Request) -> web.Response:
    """POST /api/emoji/moderation/approve — pack 승인 (admin only).

    body schema = {"pack_id": int}.
    응답:
        200: {"ok": true, "pack_id", "moderation_status": "approved", "rowcount"}
        400: {"error": "..."} — body 무효
        401: {"error": "admin only"} — Bearer 부재 또는 불일치
        503: {"error": "db unavailable"} — pool 부재 graceful
    """

    return await _handle_decision(req, ModerationStatus.APPROVED, "approve")


async def handle_reject(req: web.Request) -> web.Response:
    """POST /api/emoji/moderation/reject — pack 거부 (admin only).

    body schema = {"pack_id": int}.
    """

    return await _handle_decision(req, ModerationStatus.REJECTED, "reject")


async def handle_dmca(req: web.Request) -> web.Response:
    """POST /api/emoji/moderation/dmca — pack DMCA takedown (admin only).

    body schema = {"pack_id": int}.
    """

    return await _handle_decision(req, ModerationStatus.DMCA_TAKEDOWN, "dmca")


def register_emoji_moderation_routes(app: web.Application) -> None:
    """server.main entry — emoji moderation 4 endpoint 등록.

    GET    /api/emoji/moderation/queue   — pending list (skeleton)
    POST   /api/emoji/moderation/approve — 승인
    POST   /api/emoji/moderation/reject  — 거부
    POST   /api/emoji/moderation/dmca    — DMCA takedown
    """

    app.router.add_get("/api/emoji/moderation/queue", handle_queue)
    app.router.add_post("/api/emoji/moderation/approve", handle_approve)
    app.router.add_post("/api/emoji/moderation/reject", handle_reject)
    app.router.add_post("/api/emoji/moderation/dmca", handle_dmca)
    log.info("[api] emoji moderation 4 endpoint 등록 완료 (cycle 144 skeleton)")
