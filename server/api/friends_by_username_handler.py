# SPDX-License-Identifier: GPL-3.0-or-later
"""telegram align 사용자명 검색 친구 추가 endpoint (cycle 169.457 신설)."""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

log = logging.getLogger(__name__)


async def handle_add_friend_by_username(request: web.Request) -> web.Response:
    """POST /api/friends/by-username — username resolve + friends INSERT.

    body = ``{username: str}``.
    응답 = ``{friend_user_id: int, room_id: int}``.
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest(reason="JSON body 의무")
    username = str(body.get("username", "")).strip().lstrip("@")
    if not username or len(username) < 3:
        raise web.HTTPBadRequest(reason="username 3자 이상 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"error": "DB_DISABLED"}, status=503)

    from server.db.repositories.users import get_user_by_username
    from server.db.repositories import friends as _fr_repo
    from server.db.repositories.rooms import find_or_create_dm_room
    from server.db.repositories.messages import insert_text_message

    target = await get_user_by_username(pool, username)
    if target is None:
        raise web.HTTPNotFound(reason=f"username '{username}' 부재")
    if target.id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 친구 추가 불가")

    # 한글 주석 — telegram 등가 — 사용자명 검색 = 단방향 friends INSERT (양측 자동 friends 부재 retain)
    # 신청자 side만 friend retain. target side notify chain = 별 cycle (friend request inbox).
    try:
        await _fr_repo.insert_friend(
            pool, user_id=user_id, friend_user_id=target.id, status="accepted",
        )
    except Exception as exc:
        log.debug("[friends_by_username] INSERT graceful — %r", exc)

    # DM room 생성 + welcome system message
    room_id = 0
    try:
        room_id = await find_or_create_dm_room(pool, user_id, target.id)
        # 한글 주석 — system message 의 의 retain (target side notify chain — 별 cycle)
        log.info(
            "[friends_by_username] PASS user=%d target=%d (%s) room=%d",
            user_id, target.id, username, room_id,
        )
    except Exception as exc:
        log.warning("[friends_by_username] DM room 실패 — %r", exc)

    return web.json_response({
        "friend_user_id": target.id,
        "username": username,
        "room_id": room_id,
    }, status=201)


def register_friends_by_username_routes(app: web.Application) -> None:
    """server.main register entry."""
    app.router.add_post("/api/friends/by-username", handle_add_friend_by_username)
    log.info("[api] friends_by_username endpoint 등록 완료 (cycle 169.457)")
