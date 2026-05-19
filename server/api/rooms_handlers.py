# SPDX-License-Identifier: GPL-3.0-or-later
"""aiohttp REST endpoint — 그룹 채팅 룸 (cycle 135).

엔드포인트 6종 (auth_middleware 의 Bearer 검증 의무):

- POST   /api/rooms                  — 룸 생성 (owner = auth user_id)
- GET    /api/rooms                  — owner + member 룸 list
- GET    /api/rooms/{room_id}        — 룸 detail + member list
- POST   /api/rooms/{room_id}/join   — 룸 가입 (peers row INSERT)
- POST   /api/rooms/{room_id}/leave  — 룸 탈퇴 (peers row UPDATE left_at)
- POST   /api/rooms/{room_id}/invite — owner 의 초대 (peers row INSERT)
- POST   /api/rooms/{room_id}/kick   — owner 의 추방 (peers row UPDATE)

audit hook
----------
- ROOM_CREATE / ROOM_JOIN / ROOM_LEAVE — cycle 128 ENUM 정합.
- invite/kick = ROOM_JOIN / ROOM_LEAVE 의 재사용 + metadata.invited_user_id /
  metadata.kicked_user_id 추가.
- pool 부재 = graceful skip + 예외 swallow + log.warning.

설계 결정
---------
- room_code = 8자 hex (secrets.token_hex(4)) — 0001_init.sql CHAR(16) 와 정합
  (선두 8자 사용, 충돌 시 재시도 = Phase 5+ 별개).
- owner 자동 peers row 등록 (role=owner) — rooms.owner_id 와 peers role 정합.
- kick = owner 만 + 자기 자신 추방 차단 + target role check.
- 모든 endpoint = parameterized SQL + 예외 swallow.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any, Optional

from aiohttp import web

from server.db.repositories import rooms as rooms_repo
from server.db.repositories.user_activity import ActivityAction, log_activity
from server.middleware.activity import extract_client_ip

log = logging.getLogger(__name__)


# ─── audit helper ───────────────────────────────────────────────────────────


async def _audit_room(
    request: web.Request,
    *,
    user_id: int,
    action: ActivityAction,
    target_id: Optional[int],
    metadata: Optional[dict] = None,
) -> None:
    """ROOM_* audit hook — pool 부재 graceful + 예외 swallow.

    user_activity_log INSERT 실패 시 endpoint 응답 무영향 (log.warning 만).
    """

    pool = request.app.get("db_pool")
    if pool is None:
        return
    try:
        ua = (request.headers.get("User-Agent", "") or "")[:255]
        await log_activity(
            pool,
            user_id=user_id,
            action=action,
            target_id=target_id,
            ip_address=extract_client_ip(request),
            user_agent=ua,
            metadata=metadata,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "room audit 실패 user_id=%d action=%s: %s",
            user_id,
            action.value,
            exc,
        )


async def _read_json(request: web.Request) -> dict:
    """body JSON 파싱 — 무효 = 400."""

    try:
        return await request.json()
    except Exception as exc:  # noqa: BLE001
        raise web.HTTPBadRequest(reason="JSON 파싱 실패") from exc


def _parse_room_id(request: web.Request) -> int:
    """path variable room_id 정수 파싱 — 무효 = 400."""

    raw = request.match_info.get("room_id", "").strip()
    if not raw:
        raise web.HTTPBadRequest(reason="room_id 경로 변수 부재")
    try:
        rid = int(raw)
    except (TypeError, ValueError) as exc:
        raise web.HTTPBadRequest(reason="room_id 정수 의무") from exc
    if rid <= 0:
        raise web.HTTPBadRequest(reason="room_id 양수 의무")
    return rid


def _room_row_to_wire(row: Any) -> dict:
    """RoomRow → JSON-safe dict."""

    return {
        "id": row.id,
        "room_code": row.room_code,
        "owner_id": row.owner_id,
        "kind": row.kind,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "closed_at": row.closed_at.isoformat() if row.closed_at else None,
    }


def _peer_row_to_wire(row: Any) -> dict:
    """PeerRow → JSON-safe dict."""

    return {
        "id": row.id,
        "room_id": row.room_id,
        "user_id": row.user_id,
        "role": row.role,
        "joined_at": row.joined_at.isoformat() if row.joined_at else None,
        "left_at": row.left_at.isoformat() if row.left_at else None,
    }


# ─── handlers ───────────────────────────────────────────────────────────────


async def handle_create_room(request: web.Request) -> web.Response:
    """POST /api/rooms — 룸 생성 (owner = auth user_id).

    body = ``{kind?: "direct"|"group"}``. default kind=group (cycle 135 의 그룹
    채팅 신규 directive 정합). owner 자동 peers row 등록.
    """

    user_id = request["user_id"]
    body = await _read_json(request) if request.content_length else {}
    kind = (body.get("kind") or "group").strip()
    if kind not in ("direct", "group"):
        raise web.HTTPBadRequest(reason="kind = direct 또는 group 의무")

    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    # 한글 주석: 8자 hex room_code — CHAR(16) column 의 선두 8자 사용.
    room_code = secrets.token_hex(4)

    try:
        room_id = await rooms_repo.insert_room(
            pool, room_code=room_code, owner_id=user_id, kind=kind
        )
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "room 생성 실패 — user_id=%s kind=%s", user_id, kind
        )
        raise web.HTTPInternalServerError(reason="room 생성 실패") from exc

    # 한글 주석: owner 자동 peers row 등록 — role=owner.
    try:
        await rooms_repo.insert_peer(
            pool, room_id=room_id, user_id=user_id, role="owner"
        )
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "owner peer 등록 실패 — room_id=%d user_id=%d: %s",
            room_id,
            user_id,
            exc,
        )

    await _audit_room(
        request,
        user_id=user_id,
        action=ActivityAction.ROOM_CREATE,
        target_id=room_id,
        metadata={"room_code": room_code, "kind": kind},
    )

    return web.json_response(
        {
            "ok": True,
            "id": room_id,
            "room_code": room_code,
            "kind": kind,
            "owner_id": user_id,
        },
        status=201,
    )


async def handle_list_rooms(request: web.Request) -> web.Response:
    """GET /api/rooms — owner + member 룸 list (중복 제거).

    query parameter `scope` = owner / member / all (default all).
    """

    user_id = request["user_id"]
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    scope = request.query.get("scope", "all").lower().strip()
    if scope not in ("owner", "member", "all"):
        raise web.HTTPBadRequest(reason="scope = owner / member / all 중 1")

    rows = []
    if scope in ("owner", "all"):
        rows.extend(await rooms_repo.list_rooms_by_owner(pool, user_id))
    if scope in ("member", "all"):
        member_rows = await rooms_repo.list_rooms_by_member(pool, user_id)
        # 한글 주석: owner + member 중복 제거 (set 의 id 기반).
        seen = {r.id for r in rows}
        rows.extend(r for r in member_rows if r.id not in seen)

    payload = {
        "ok": True,
        "user_id": user_id,
        "rooms": [_room_row_to_wire(r) for r in rows],
        "count": len(rows),
    }
    return web.json_response(payload)


async def handle_get_room(request: web.Request) -> web.Response:
    """GET /api/rooms/{room_id} — 룸 detail + member list.

    참여자 또는 owner 만 접근 가능. 그 외 = 403.
    """

    user_id = request["user_id"]
    room_id = _parse_room_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )

    # 한글 주석: owner 또는 활성 peer 만 접근 허용.
    peer = await rooms_repo.get_peer(pool, room_id=room_id, user_id=user_id)
    if room.owner_id != user_id and peer is None:
        return web.json_response(
            {"error": "forbidden", "room_id": room_id}, status=403
        )

    members = await rooms_repo.list_active_peers(pool, room_id)
    return web.json_response(
        {
            "ok": True,
            "room": _room_row_to_wire(room),
            "members": [_peer_row_to_wire(p) for p in members],
            "member_count": len(members),
        }
    )


async def handle_join_room(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/join — 룸 가입.

    이미 활성 참여 중 = 409. 룸 closed = 409.
    """

    user_id = request["user_id"]
    room_id = _parse_room_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )
    if room.status != "active":
        return web.json_response(
            {"error": "room_closed", "room_id": room_id}, status=409
        )

    existing = await rooms_repo.get_peer(pool, room_id=room_id, user_id=user_id)
    if existing is not None:
        return web.json_response(
            {"error": "already_member", "room_id": room_id}, status=409
        )

    try:
        peer_id = await rooms_repo.insert_peer(
            pool, room_id=room_id, user_id=user_id, role="member"
        )
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "room join 실패 — room_id=%d user_id=%d", room_id, user_id
        )
        raise web.HTTPInternalServerError(reason="join 실패") from exc

    await _audit_room(
        request,
        user_id=user_id,
        action=ActivityAction.ROOM_JOIN,
        target_id=room_id,
        metadata={"peer_id": peer_id},
    )

    return web.json_response(
        {"ok": True, "room_id": room_id, "peer_id": peer_id}, status=200
    )


async def handle_leave_room(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/leave — 룸 탈퇴 (peers UPDATE left_at).

    활성 참여 부재 = 404.
    """

    user_id = request["user_id"]
    room_id = _parse_room_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    rowcount = await rooms_repo.update_peer_left(
        pool, room_id=room_id, user_id=user_id
    )
    if rowcount == 0:
        return web.json_response(
            {"error": "not_member", "room_id": room_id}, status=404
        )

    await _audit_room(
        request,
        user_id=user_id,
        action=ActivityAction.ROOM_LEAVE,
        target_id=room_id,
        metadata=None,
    )

    return web.json_response({"ok": True, "room_id": room_id}, status=200)


async def handle_invite_room(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/invite — owner 의 초대.

    body = ``{user_id: int}``. owner 만 허용. 이미 활성 참여 중 = 409.
    """

    user_id = request["user_id"]
    room_id = _parse_room_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    body = await _read_json(request)
    invited_user_id = body.get("user_id")
    if not isinstance(invited_user_id, int) or invited_user_id <= 0:
        raise web.HTTPBadRequest(reason="user_id 양수 정수 의무")
    if invited_user_id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 초대 차단")

    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )
    if room.owner_id != user_id:
        return web.json_response(
            {"error": "forbidden_owner_only", "room_id": room_id}, status=403
        )
    if room.status != "active":
        return web.json_response(
            {"error": "room_closed", "room_id": room_id}, status=409
        )

    existing = await rooms_repo.get_peer(
        pool, room_id=room_id, user_id=invited_user_id
    )
    if existing is not None:
        return web.json_response(
            {"error": "already_member", "user_id": invited_user_id}, status=409
        )

    try:
        peer_id = await rooms_repo.insert_peer(
            pool, room_id=room_id, user_id=invited_user_id, role="member"
        )
    except Exception as exc:  # noqa: BLE001
        log.exception(
            "room invite 실패 — room_id=%d invited=%d", room_id, invited_user_id
        )
        raise web.HTTPInternalServerError(reason="invite 실패") from exc

    await _audit_room(
        request,
        user_id=user_id,
        action=ActivityAction.ROOM_JOIN,
        target_id=room_id,
        metadata={"invited_user_id": invited_user_id, "peer_id": peer_id},
    )

    return web.json_response(
        {
            "ok": True,
            "room_id": room_id,
            "invited_user_id": invited_user_id,
            "peer_id": peer_id,
        },
        status=200,
    )


async def handle_kick_room(request: web.Request) -> web.Response:
    """POST /api/rooms/{room_id}/kick — owner 의 추방.

    body = ``{user_id: int}``. owner 만 허용 + 자기 자신 추방 차단 +
    target 의 활성 참여 의무.
    """

    user_id = request["user_id"]
    room_id = _parse_room_id(request)
    pool = request.app["db_pool"]
    if pool is None:
        raise web.HTTPInternalServerError(reason="db_pool 미활성")

    body = await _read_json(request)
    kicked_user_id = body.get("user_id")
    if not isinstance(kicked_user_id, int) or kicked_user_id <= 0:
        raise web.HTTPBadRequest(reason="user_id 양수 정수 의무")
    if kicked_user_id == user_id:
        raise web.HTTPBadRequest(reason="자기 자신 추방 차단")

    room = await rooms_repo.get_room_by_id(pool, room_id)
    if room is None:
        return web.json_response(
            {"error": "room_not_found", "room_id": room_id}, status=404
        )
    if room.owner_id != user_id:
        return web.json_response(
            {"error": "forbidden_owner_only", "room_id": room_id}, status=403
        )

    rowcount = await rooms_repo.update_peer_left(
        pool, room_id=room_id, user_id=kicked_user_id
    )
    if rowcount == 0:
        return web.json_response(
            {"error": "target_not_member", "user_id": kicked_user_id},
            status=404,
        )

    await _audit_room(
        request,
        user_id=user_id,
        action=ActivityAction.ROOM_LEAVE,
        target_id=room_id,
        metadata={"kicked_user_id": kicked_user_id},
    )

    return web.json_response(
        {"ok": True, "room_id": room_id, "kicked_user_id": kicked_user_id},
        status=200,
    )


def register_rooms_routes(app: web.Application) -> None:
    """aiohttp Application 에 rooms 6 endpoint 등록 (cycle 135)."""

    app.router.add_post("/api/rooms", handle_create_room)
    app.router.add_get("/api/rooms", handle_list_rooms)
    app.router.add_get("/api/rooms/{room_id}", handle_get_room)
    app.router.add_post("/api/rooms/{room_id}/join", handle_join_room)
    app.router.add_post("/api/rooms/{room_id}/leave", handle_leave_room)
    app.router.add_post("/api/rooms/{room_id}/invite", handle_invite_room)
    app.router.add_post("/api/rooms/{room_id}/kick", handle_kick_room)
    log.info("[api] rooms 7 endpoint 등록 완료 (cycle 135)")
