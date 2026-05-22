# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — 읽음 상태 추적 (cycle 169.447 신설).

엔드포인트:
- POST /api/rooms/{room_id}/read — chat 포커스 시점 last_read_msg_id 갱신
- GET  /api/rooms/unread — multiple room unread count batch 조회 (?room_ids=1,2,3)
"""

from __future__ import annotations

import logging
from typing import Any

from aiohttp import web

from server.db.repositories import read_states as _rs_repo

log = logging.getLogger(__name__)


async def handle_mark_read(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/read — last_read_msg_id UPSERT.

    body = ``{last_read_msg_id: int}``.
    """
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    try:
        room_id = int(request.match_info["room_id"])
    except (KeyError, ValueError):
        raise web.HTTPBadRequest(reason="room_id 정수 의무")
    try:
        body = await request.json()
    except ValueError:
        body = {}
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(reason="body object 의무")
    last_read = body.get("last_read_msg_id")
    if not isinstance(last_read, int) or last_read < 0:
        raise web.HTTPBadRequest(reason="last_read_msg_id 0 이상 정수 의무")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response(
            {"error": "DB_DISABLED"}, status=503,
        )
    await _rs_repo.upsert_last_read(
        pool, user_id=user_id, room_id=room_id, last_read_msg_id=last_read,
    )
    log.info("[read] user=%d room=%d last_read=%d", user_id, room_id, last_read)
    return web.json_response({"ok": True, "room_id": room_id, "last_read_msg_id": last_read})


async def handle_unread_counts(request: web.Request) -> web.Response:
    """GET /api/rooms/unread?room_ids=1,2,3 — multiple room unread count batch."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    raw = request.query.get("room_ids", "").strip()
    if not raw:
        return web.json_response({"counts": {}})
    try:
        room_ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise web.HTTPBadRequest(reason="room_ids = comma-separated 정수 의무")
    if not room_ids:
        return web.json_response({"counts": {}})
    if len(room_ids) > 100:
        raise web.HTTPBadRequest(reason="room_ids 100개 cap")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"counts": {}})
    counts = await _rs_repo.get_unread_counts(
        pool, user_id=user_id, room_ids=room_ids,
    )
    return web.json_response({"counts": {str(k): v for k, v in counts.items()}})


async def handle_last_read_batch(request: web.Request) -> web.Response:
    """GET /api/rooms/last-read?room_ids=1,2,3 — batch last_read_msg_id (cycle 169.470)."""
    user_id = request.get("user_id")
    if not isinstance(user_id, int) or user_id <= 0:
        raise web.HTTPUnauthorized(reason="Bearer 인증 의무")
    raw = request.query.get("room_ids", "").strip()
    if not raw:
        return web.json_response({"last_read": {}})
    try:
        room_ids = [int(x) for x in raw.split(",") if x.strip()]
    except ValueError:
        raise web.HTTPBadRequest(reason="room_ids = comma-separated 정수 의무")
    if not room_ids or len(room_ids) > 100:
        raise web.HTTPBadRequest(reason="room_ids 1~100 cap")
    pool = request.app.get("db_pool")
    if pool is None:
        return web.json_response({"last_read": {}})
    out = await _rs_repo.get_last_read_batch(
        pool, user_id=user_id, room_ids=room_ids,
    )
    return web.json_response({"last_read": {str(k): v for k, v in out.items()}})


def register_read_routes(app: web.Application) -> None:
    """server.main register entry — 3 endpoint 등록."""
    app.router.add_post("/api/rooms/{room_id}/read", handle_mark_read)
    app.router.add_get("/api/rooms/unread", handle_unread_counts)
    app.router.add_get("/api/rooms/last-read", handle_last_read_batch)  # cycle 169.470
    log.info("[api] read 3 endpoint 등록 완료 (cycle 169.447~470)")
