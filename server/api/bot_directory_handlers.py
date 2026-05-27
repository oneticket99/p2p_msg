# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — bot framework BotFather 등가 (cycle 169.420 신설).

역할 — 봇 등록/공개 디렉토리 조회/토큰 발급·해지를 처리한다(텔레그램 BotFather
등가). 봇 토큰은 발급 시 1회만 평문 노출되고 DB 에는 해시만 저장한다.

계층 위치 — server API handler 계층(정본 §E). GET 디렉토리/단일 봇은 public,
나머지는 Bearer + owner 검증. 영속화는 `bots` repository 에 위임한다.

의존성 — aiohttp `web` + `request.app["db_pool"]` + `bots` repository
(`list_public_bots`/`get_bot_by_username`/`insert_bot`/`insert_bot_token`/
`list_owner_bots`/`revoke_bot_token` + `BotRow`). username/webhook 정규식은 모듈 상수.

범위 한계 — 봇 메타 + 토큰 수명 관리만. 실 봇 메시지 처리(webhook dispatch)·
inline query·payment 는 별도 bot runtime 경로(본 module 범위 외).

엔드포인트 카탈로그(실 함수 6 + dict helper + register):
- `handle_list_public_bots`  GET    /api/bots                    — 공개+active(public).
- `handle_create_bot`        POST   /api/bots                    — 등록+초기 토큰(Bearer).
- `handle_list_my_bots`      GET    /api/bots/me                 — owner self(Bearer).
- `handle_get_bot`           GET    /api/bots/{username}         — 단일(public).
- `handle_create_token`      POST   /api/bots/{username}/tokens  — 토큰 발급(owner).
- `handle_revoke_token`      DELETE /api/bots/tokens/{token_id}  — 토큰 해지(owner).
- `_bot_to_dict` / `register_bot_directory_routes`.

정합 memory = [[project_bot_framework]] — Phase 3+ 차별화.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from aiohttp import web

from server.db.repositories import bots as _bots_repo

log = logging.getLogger(__name__)

# username 규칙 — 소문자 시작 + 소문자/숫자/언더스코어 4~32자(끝 _bot suffix 권장, 텔레그램 정합)
_USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{3,31}$")
# webhook URL 은 HTTPS strict — 평문 http 콜백 차단(토큰 노출/MITM 방어)
_WEBHOOK_URL_RE = re.compile(r"^https://[a-zA-Z0-9.\-_~:/?#@!$&'()*+,;=%]+$")


def _bot_to_dict(b: _bots_repo.BotRow) -> Dict[str, Any]:
    """BotRow → JSON dict."""
    return {
        "id": b.id,
        "owner_user_id": b.owner_user_id,
        "name": b.name,
        "username": b.username,
        "description": b.description,
        "webhook_url": b.webhook_url,
        "inline_enabled": b.inline_enabled,
        "is_public": b.is_public,
        "status": b.status,
    }


async def handle_list_public_bots(request: web.Request) -> web.Response:
    """GET /api/bots — 공개 + active 봇 list."""
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"bots": [], "limit": 0, "offset": 0, "count": 0})
    try:
        limit = max(1, min(200, int(request.query.get("limit", "50"))))
        offset = max(0, int(request.query.get("offset", "0")))
    except ValueError:
        raise web.HTTPBadRequest(reason="limit/offset 정수 의무")
    rows = await _bots_repo.list_public_bots(pool, limit=limit, offset=offset)
    payload = [_bot_to_dict(r) for r in rows]
    return web.json_response({
        "bots": payload, "limit": limit, "offset": offset, "count": len(payload),
    })


async def handle_get_bot(request: web.Request) -> web.Response:
    """GET /api/bots/{username} — 단일 봇 정보 (public)."""
    username = request.match_info.get("username", "").lower()
    if not username:
        raise web.HTTPBadRequest(reason="username 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        raise web.HTTPServiceUnavailable(reason="DB pool 부재")
    bot = await _bots_repo.get_bot_by_username(pool, username)
    if bot is None or not bot.is_public:
        raise web.HTTPNotFound(reason=f"bot username={username} 부재 또는 비공개")
    return web.json_response({"bot": _bot_to_dict(bot)})


async def handle_create_bot(request: web.Request) -> web.Response:
    """POST /api/bots — 신규 봇 등록 + 초기 token 발급.

    인증 — Bearer 의무(401). 등록자가 owner 가 된다.
    검증 순서 — (1) user_id → (2) JSON body=dict → (3) name 1~64 →
    (4) username 정규식 → (5) description ≤255 → (6) webhook_url HTTPS strict →
    (7) db_pool → (8) username 중복(409).

    Parameters — body ``{name, username, description?, webhook_url?, inline_enabled?,
        is_public?}``.
    Returns — 201 + ``{bot_id, username, token, token_id}``(token 평문 1회 노출).
    Raises — HTTPUnauthorized / HTTPBadRequest(필드 위반) / 409(username 중복) /
        503(db_pool 부재).
    부작용 — `insert_bot` + `insert_bot_token`(bots + bot_tokens INSERT, 토큰 해시
        저장) + INFO 로그. 평문 토큰은 응답에만 — DB 미저장이라 재발급 불가.
    """
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        body = await request.json()
    except ValueError as exc:
        raise web.HTTPBadRequest(reason="JSON body 의무") from exc
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")

    name = str(body.get("name", "")).strip()
    username = str(body.get("username", "")).strip().lower()
    description = body.get("description")
    webhook_url = body.get("webhook_url")
    inline_enabled = bool(body.get("inline_enabled", False))
    is_public = bool(body.get("is_public", False))

    if not name or len(name) > 64:
        raise web.HTTPBadRequest(reason="name 1~64자 의무")
    if not _USERNAME_RE.match(username):
        raise web.HTTPBadRequest(
            reason="username 형식 부재 (소문자 시작 + 4~32자 + 소문자/숫자/언더스코어)"
        )
    if description is not None and (not isinstance(description, str) or len(description) > 255):
        raise web.HTTPBadRequest(reason="description string + 255자 cap")
    if webhook_url is not None:
        if not isinstance(webhook_url, str) or not _WEBHOOK_URL_RE.match(webhook_url):
            raise web.HTTPBadRequest(reason="webhook_url HTTPS strict 의무")

    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    existing = await _bots_repo.get_bot_by_username(pool, username)
    if existing is not None:
        return web.json_response(
            {"error": "USERNAME_CONFLICT", "message": f"username={username} 이미 사용 중"},
            status=409,
        )
    try:
        bot_id = await _bots_repo.insert_bot(
            pool, owner_user_id=user_id, name=name, username=username,
            description=description, webhook_url=webhook_url,
            inline_enabled=inline_enabled, is_public=is_public,
        )
        token_plaintext, token_id = await _bots_repo.insert_bot_token(
            pool, bot_id=bot_id, label="initial",
        )
    except ValueError as exc:
        raise web.HTTPBadRequest(reason=str(exc))
    log.info(
        "[bot_directory] create user_id=%d username=%s bot_id=%d token_id=%d",
        user_id, username, bot_id, token_id,
    )
    # 평문 token 은 이 응답에만 노출 — DB 는 해시만 보관하므로 분실 시 재발급만 가능
    return web.json_response(
        {"bot_id": bot_id, "username": username, "token": token_plaintext, "token_id": token_id},
        status=201,
    )


async def handle_list_my_bots(request: web.Request) -> web.Response:
    """GET /api/bots/me — owner self 봇 list (status 무관)."""
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"bots": []})
    rows = await _bots_repo.list_owner_bots(pool, owner_user_id=user_id)
    return web.json_response({"bots": [_bot_to_dict(r) for r in rows]})


async def handle_create_token(request: web.Request) -> web.Response:
    """POST /api/bots/{username}/tokens — 봇 token 추가 발급.

    인증 — Bearer 의무(401) + owner 검증(bot.owner ≠ user 시 403).
    Parameters — match_info ``username``, body ``{label?: str}``(≤64자).
    Returns — 201 + ``{token, token_id, label}``(평문 1회 노출).
    Raises — HTTPUnauthorized / HTTPBadRequest(username·label) / 404(봇 부재) /
        403(owner 불일치) / 503.
    부작용 — `insert_bot_token`(bot_tokens INSERT, 해시 저장) + INFO 로그.
    """
    user_id = request.get("user_id")
    if user_id is None or not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    username = request.match_info.get("username", "").lower()
    if not username:
        raise web.HTTPBadRequest(reason="username 의무")
    label = None
    try:
        body = await request.json()
        if isinstance(body, dict):
            label = body.get("label")
            if label is not None and (not isinstance(label, str) or len(label) > 64):
                raise web.HTTPBadRequest(reason="label string + 64자 cap")
    except ValueError:
        pass
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED", "message": "DB pool 비활성"}, status=503
        )
    bot = await _bots_repo.get_bot_by_username(pool, username)
    if bot is None:
        raise web.HTTPNotFound(reason=f"bot username={username} 부재")
    if bot.owner_user_id != user_id:
        raise web.HTTPForbidden(reason="bot owner 만 token 발급 가능")
    plaintext, token_id = await _bots_repo.insert_bot_token(
        pool, bot_id=bot.id, label=label,
    )
    log.info(
        "[bot_directory] create_token user_id=%d username=%s token_id=%d",
        user_id, username, token_id,
    )
    return web.json_response(
        {"token": plaintext, "token_id": token_id, "label": label},
        status=201,
    )


async def handle_revoke_token(request: web.Request) -> web.Response:
    """DELETE /api/bots/tokens/{token_id} — token revoke.

    인증 — Bearer 의무(401) + owner 검증(bot_tokens JOIN bots, owner ≠ user 시 403).
    Parameters — match_info ``token_id``(정수).
    Returns — 200 + ``{revoked: bool, token_id}``. 미존재 404.
    부작용 — owner 검증 JOIN SELECT + `revoke_bot_token`(bot_tokens soft revoke).
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
    # owner 검증 — 토큰의 봇 owner 가 호출자인지 JOIN 으로 확인(타 owner 토큰 해지 차단)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT b.owner_user_id FROM bot_tokens t JOIN bots b ON t.bot_id = b.id "
                "WHERE t.id = %s LIMIT 1",
                (token_id,),
            )
            row = await cur.fetchone()
    if row is None:
        raise web.HTTPNotFound(reason=f"token_id={token_id} 부재")
    if int(row[0]) != user_id:
        raise web.HTTPForbidden(reason="token owner 만 revoke 가능")
    ok = await _bots_repo.revoke_bot_token(pool, token_id=token_id)
    return web.json_response({"revoked": ok, "token_id": token_id})


def register_bot_directory_routes(app: web.Application) -> None:
    """server.main register entry — 6 endpoint 등록."""
    app.router.add_get("/api/bots", handle_list_public_bots)
    app.router.add_get("/api/bots/me", handle_list_my_bots)
    app.router.add_post("/api/bots", handle_create_bot)
    app.router.add_get("/api/bots/{username}", handle_get_bot)
    app.router.add_post("/api/bots/{username}/tokens", handle_create_token)
    app.router.add_delete("/api/bots/tokens/{token_id}", handle_revoke_token)
    log.info("[api] bot_directory 6 endpoint 등록 완료 (cycle 169.420)")
