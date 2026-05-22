# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — bot framework BotFather 등가 (cycle 169.420 신설).

엔드포인트:
- GET  /api/bots                         — 공개 디렉토리 list (public)
- POST /api/bots                         — 신규 봇 등록 (owner Bearer)
- GET  /api/bots/me                      — owner self 봇 list (Bearer)
- GET  /api/bots/{username}              — 단일 봇 정보 (public)
- POST /api/bots/{username}/tokens       — 봇 token 발급 (owner Bearer)
- DELETE /api/bots/tokens/{token_id}     — token revoke (owner Bearer)

정합 memory = [[project_bot_framework]] — Phase 3+ 차별화.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict

from aiohttp import web

from server.db.repositories import bots as _bots_repo

log = logging.getLogger(__name__)

# 한글 주석 — username regex (lowercase + 숫자 + _, 4~32 chars, 끝 _bot suffix 권장 텔레그램 정합)
_USERNAME_RE = re.compile(r"^[a-z][a-z0-9_]{3,31}$")
# 한글 주석 — webhook URL HTTPS strict (보안 의무)
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

    요청 schema = ``{name, username, description, webhook_url, inline_enabled, is_public}``.
    응답 schema = ``{bot_id, username, token: <plaintext 1회 노출>}``.
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
    # 한글 주석 — plaintext token = 응답 1회 노출 (DB 저장 부재, 재 발급 불가)
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
    """POST /api/bots/{username}/tokens — 봇 token 추가 발급."""
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
    """DELETE /api/bots/tokens/{token_id} — token revoke."""
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
    # 한글 주석 — owner 검증 — bot_tokens JOIN bots WHERE owner_user_id = user_id
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
