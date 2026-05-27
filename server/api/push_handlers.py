# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — FCM device token register/unregister (cycle 169.446 신설).

역할 — FCM push 발송 대상이 되는 디바이스 token 의 등록/비활성을 처리한다.
호출자(인증된 사용자)의 self token 만 다루며, token 의 소유권은 user_id 로 묶인다.

계층 위치 — server API handler 계층(정본 §E). auth_middleware 통과(Bearer 의무)
후 진입하며, 영속화는 `device_tokens` repository 에 위임한다.

의존성 — aiohttp `web` + `request.app["db_pool"]`(asyncmy) + `device_tokens`
repository(`upsert_token`/`deactivate_token`). push 발송 자체는 본 모듈 범위 외.

범위 한계 — token CRUD 만. 실 FCM 메시지 전송/페이로드 구성/재시도는 별도
push 발송 경로가 담당한다. unregister 는 물리 삭제가 아니라 비활성(soft).

엔드포인트 카탈로그(실 함수 2 + register 1):
- `handle_register_token`    POST   /api/push/register           — token UPSERT.
- `handle_unregister_token`  DELETE /api/push/tokens/{token_id}  — owner 검증 후 비활성.
- `register_push_routes` — server.main 등록 entry.
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from server.db.repositories import device_tokens as _dt_repo

log = logging.getLogger(__name__)


async def handle_register_token(request: web.Request) -> web.Response:
    """POST /api/push/register — 디바이스 FCM token UPSERT.

    의도 — 로그인 디바이스가 push 수신 대상으로 자신을 등록(또는 token 갱신)한다.

    인증 — Bearer 의무. `request["user_id"]`(auth_middleware 주입)가 양의 정수
    아니면 401.

    검증 순서 — (1) user_id 유효 → (2) JSON body 파싱 → (3) body=dict →
    (4) fcm_token 비어있지 않음 → (5) platform ENUM 6종 → (6) db_pool 가용.
    각 단계 실패 시 즉시 4xx/503 반환(이후 단계 미진입).

    Parameters — body ``{fcm_token: str, platform: str, device_label: str?}``.
        platform ∈ {macos, windows, linux, ios, android, web}.
    Returns — 201 + ``{token_id: int}``.
    Raises — HTTPUnauthorized(인증 부재) / HTTPBadRequest(body·필드 위반) /
        repository ValueError → HTTPBadRequest. db_pool 부재 시 503 JSON.
    부작용 — `device_tokens` UPSERT(DB write) + INFO 로그.
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
    """DELETE /api/push/tokens/{token_id} — token 비활성 chain.

    의도 — 디바이스 로그아웃/해지 시 self token 을 push 대상에서 제외한다.

    인증 — Bearer 의무(401). 추가로 token owner 검증 — `device_tokens` 의
    user_id 가 호출자와 다르면 403(타 사용자 token 비활성 차단).

    검증 순서 — (1) user_id 유효 → (2) token_id 정수 → (3) db_pool 가용 →
    (4) token 존재(부재 시 404) → (5) owner 일치(불일치 403) → 비활성 실행.

    Parameters — match_info ``token_id``(경로 정수).
    Returns — 200 + ``{deactivated: bool, token_id: int}``.
    Raises — HTTPUnauthorized / HTTPBadRequest(token_id 비정수) /
        HTTPNotFound(token 부재) / HTTPForbidden(owner 불일치). db_pool 부재 시 503.
    부작용 — owner 조회 SELECT + `deactivate_token` UPDATE(soft, DB write).
    """
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
