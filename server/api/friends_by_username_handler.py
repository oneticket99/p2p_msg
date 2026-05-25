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

    target = await get_user_by_username(pool, username)
    if target is None:
        raise web.HTTPNotFound(reason=f"username '{username}' 부재")
    if target.id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 친구 추가 불가")

    # cycle 169.832 — 요청/승인 모델 정합 (instant-accept leak 봉합).
    # username 검색 친구 추가 = 단방향 pending 요청 생성 → 수신자 "받은 친구 요청" +
    # badge 노출. 양방향 accepted + DM room + system message 는 수락 시점
    # (handle_accept_friend) 으로 이동한다. (기존 instant-accept 가 pending 을 우회해
    # 수신자에게 요청이 전혀 보이지 않던 버그 회수 — 사용자 dogfooding 발견.)
    existing = await _fr_repo.get_friend(
        pool, user_id=user_id, friend_user_id=target.id,
    )
    if existing is not None and existing.status in ("accepted", "pending"):
        # 한글 주석 — 이미 친구이거나 요청 진행 중이면 중복 생성 금지 (멱등 응답)
        return web.json_response({
            "friend_user_id": target.id,
            "username": username,
            "status": existing.status,
        }, status=200)
    try:
        await _fr_repo.insert_friend(
            pool, user_id=user_id, friend_user_id=target.id, status="pending",
        )
    except Exception as exc:
        log.debug("[friends_by_username] pending INSERT graceful — %r", exc)
    log.info(
        "[friends_by_username] 친구 요청 발신 user=%d target=%d (%s) status=pending",
        user_id, target.id, username,
    )
    return web.json_response({
        "friend_user_id": target.id,
        "username": username,
        "status": "pending",
    }, status=201)


def register_friends_by_username_routes(app: web.Application) -> None:
    """server.main register entry."""
    app.router.add_post("/api/friends/by-username", handle_add_friend_by_username)
    log.info("[api] friends_by_username endpoint 등록 완료 (cycle 169.457)")
